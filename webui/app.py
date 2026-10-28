"""팔 위치 저장 + 미션 디버깅 웹 페이지
카메라 화면, 인식 중인 QR, 서보 버튼, 공통 자세(drive, qr) 저장,
mode 선택 + mode 별 위치 4곳·lift·집게 각도 저장 (sequence.py),
미션 실행 (main 처음부터 / LEFT·RIGHT 강제 후 팔만), 진행 단계 표시, 정지 버튼

mission 폴더에서 실행:  python3 webui/app.py
PC 브라우저에서:        http://192.168.50.2:5002
"""
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # mission 폴더의 hw, arm, qr 사용

import cv2
from flask import Flask, Response, jsonify, request, send_file
from werkzeug.exceptions import HTTPException

import arm
import display
import hw
import main as mission
import qr
import sequence
import status

PORT = 5002
QR_EVERY = 2          # 몇 프레임마다 QR 인식할지 (Pi 부하 줄이기)
QR_HOLD_SEC = 1.0     # 이 시간 안에 본 QR 을 "지금 인식 중" 으로 표시

CHANNELS = [
    (hw.SERVO_ARM_ROT, '팔 좌우'),
    (hw.SERVO_ARM_UP, '팔 상하'),
    (hw.SERVO_WRIST, '손목'),
    (hw.SERVO_GRIP, '집게'),
    (hw.SERVO_STEER, '조향'),
]

app = Flask(__name__)
servo_lock = threading.Lock()


class CameraWorker:
    """카메라를 계속 읽어 최신 JPEG 와 QR 결과를 보관한다."""

    def __init__(self):
        self.jpg = None
        self.detections = []   # 마지막으로 QR 인식을 돌린 프레임의 결과 (qr.detect_all)
        self.det_time = 0.0    # 그 프레임을 읽은 시각
        self.qr_text = ''      # 마지막으로 본 QR 글자 (여러 개면 'PICK, PLACE')
        self.qr_time = 0.0
        self.error = ''
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        try:
            cap = hw.open_camera()
        except RuntimeError as e:
            self.error = str(e)
            return
        n = 0
        shown = []
        while True:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.05)
                continue
            now = time.time()
            n += 1
            if n % QR_EVERY == 0:
                self.detections, self.det_time = qr.detect_all(frame), now
                if self.detections:
                    shown = self.detections
                    self.qr_text = ', '.join(d['text'] for d in shown)
                    self.qr_time = now
            if now - self.qr_time < QR_HOLD_SEC:
                for d in shown:
                    cv2.polylines(frame, [d['points'].astype(int)], True, (0, 255, 0), 3)
                    x, y = int(d['cx']), int(d['cy'])
                    cv2.drawMarker(frame, (x, y), (0, 255, 0), cv2.MARKER_CROSS, 16, 2)
                    cv2.putText(frame, d['text'], (x - 30, y - int(d['size'] / 2) - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            _, jpg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            self.jpg = jpg.tobytes()

    def look(self, timeout=2.0):
        """부른 뒤에 읽은 프레임의 QR 결과 (QR 을 기다릴 때 쓴다)"""
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.det_time > t0:
                return list(self.detections)
            time.sleep(0.02)
        return []


class DistanceWorker:
    """초음파를 0.2초마다 재서 최신 값을 보관한다 (요청이 측정 시간만큼 멈추지 않게)."""

    def __init__(self):
        self.cm = None
        self.error = ''
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            try:
                self.cm = hw.distance_cm()
                self.error = ''
            except Exception as e:   # 에코 미수신, 시간 초과, 핀 사용 중 등
                self.cm = None
                self.error = str(e)
            time.sleep(0.2)


camera = None
distance = None
mission_thread = None


def wait_qr_from_camera(wanted=('LEFT', 'RIGHT')):
    """미션 시작 뒤에 새로 인식된 LEFT/RIGHT 를 기다린다 (카메라는 CameraWorker 가 계속 읽음)."""
    started = time.time()
    while True:
        status.check_abort()
        for d in camera.look():
            if d['text'].upper() in wanted and camera.det_time > started:
                return d['text'].upper()


def mission_running():
    return mission_thread is not None and mission_thread.is_alive()


def start_mission(target, *args):
    global mission_thread

    def run():
        try:
            target(*args)
        except Exception as e:   # 오류 내용은 status 에 기록됨
            print('[미션 오류]', e)

    mission_thread = threading.Thread(target=run, daemon=True)
    mission_thread.start()


@app.route('/')
def index():
    return send_file(Path(__file__).with_name('index.html'))


@app.route('/video')
def video():
    def frames():
        while True:
            if camera.jpg:
                yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + camera.jpg + b'\r\n'
            time.sleep(1 / 15)
    return Response(frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/state')
def state():
    age = time.time() - camera.qr_time if camera.qr_time else None
    return jsonify(
        angles={ch: hw.get_servo(ch) for ch, _ in CHANNELS},
        channels=[{'ch': ch, 'name': name} for ch, name in CHANNELS],
        arm_channels=hw.ARM_SERVOS,
        qr={'text': camera.qr_text, 'age': age, 'live': age is not None and age < QR_HOLD_SEC},
        camera_error=camera.error,
        distance=distance.cm,
        distance_error=distance.error,
        poses=arm.load_poses(),
        pose_names=arm.POSE_NAMES,
        modes=sequence.load(),
        mode_names=sequence.MODES,
        positions=sequence.POSITIONS,
        lift=sequence.LIFT,
        grips=sequence.GRIPS,
        order=sequence.ORDER,
        mission=status.snapshot(),
    )


@app.route('/api/mission/<kind>', methods=['POST'])
def mission_control(kind):
    if kind == 'stop':
        status.request_abort()
        hw.estop(True)
        return jsonify(ok=True)
    if mission_running():
        return jsonify(ok=False, error='미션이 이미 실행 중입니다'), 409
    mode = sequence.active_mode()   # 웹에서 고른 mode
    if kind == 'full':
        start_mission(mission.run_full, wait_qr_from_camera, mode)
    elif kind == 'arm':
        side = (request.get_json(silent=True) or {}).get('side')
        if side not in ('left', 'right'):
            return jsonify(ok=False, error='side 는 left / right'), 400
        start_mission(mission.run_arm_only, side, mode)
    else:
        return jsonify(ok=False, error='알 수 없는 모드'), 404
    return jsonify(ok=True)


@app.route('/api/mode/<action>', methods=['POST'])
def mode_control(action):
    """active: 사용할 mode 고르기 / save: 지금 각도를 mode 의 위치로 저장 / go: 그 위치로 이동"""
    data = request.get_json()
    mode = data['mode']
    with servo_lock:
        if action == 'active':
            sequence.set_active(mode)
        elif action == 'save':
            sequence.save(mode, data['name'])
        elif action == 'go':
            sequence.go(mode, data['name'])
        else:
            return jsonify(ok=False, error='알 수 없는 동작'), 404
    return jsonify(ok=True)


@app.errorhandler(Exception)
def api_error(e):
    """저장 안 된 위치로 이동 등 → 화면에 오류 문구로 보여준다."""
    if isinstance(e, HTTPException):   # 404 같은 건 그대로
        return e
    return jsonify(ok=False, error=str(e)), 400


@app.before_request
def block_manual_while_running():
    """미션 중에는 서보 버튼·위치 저장을 막는다 (서로 같은 서보를 움직이지 않게)."""
    if (request.method == 'POST' and mission_running()
            and request.path.startswith(('/api/servo', '/api/pose', '/api/mode'))):
        return jsonify(ok=False, error='미션 실행 중에는 수동 조작을 할 수 없습니다'), 409


@app.route('/api/servo', methods=['POST'])
def servo():
    data = request.get_json()
    ch = int(data['ch'])
    with servo_lock:
        if 'angle' in data:
            goal = int(data['angle'])
        else:
            goal = (hw.get_servo(ch) or 90) + int(data['delta'])
        arm.move_to({ch: max(0, min(180, goal))})
    return jsonify(ok=True, angle=hw.get_servo(ch))


@app.route('/api/pose/<action>', methods=['POST'])
def pose(action):
    name = request.get_json()['name'].strip()
    if not name:
        return jsonify(ok=False, error='이름을 입력하세요'), 400
    with servo_lock:
        if action == 'save':
            angles = {ch: hw.get_servo(ch) for ch in hw.ARM_SERVOS}
            if None in angles.values():
                return jsonify(ok=False, error='각도를 모르는 서보가 있습니다. 먼저 움직여 주세요'), 400
            arm.save_pose(name, angles)
        elif action == 'go':
            arm.go_pose(name)
        elif action == 'delete':
            arm.delete_pose(name)
        else:
            return jsonify(ok=False, error='알 수 없는 동작'), 404
    return jsonify(ok=True)


if __name__ == '__main__':
    print('시작: 팔과 집게를 90도, 조향을 가운데로 보냅니다')
    arm.move_to({ch: 90 for ch in hw.ARM_SERVOS + [hw.SERVO_GRIP]})
    hw.steer(0)
    display.start()
    camera = CameraWorker()
    distance = DistanceWorker()
    print(f'브라우저에서 http://192.168.50.2:{PORT} 접속 (종료: Ctrl+C)')
    try:
        app.run(host='0.0.0.0', port=PORT, threaded=True)
    finally:
        hw.cleanup()
