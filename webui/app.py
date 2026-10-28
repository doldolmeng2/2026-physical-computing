"""팔 자세 저장 + 미션 디버깅 웹 페이지
카메라 화면, 인식 중인 QR, 서보 버튼, 자세 저장/불러오기,
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

import arm
import display
import hw
import main as mission
import qr
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
        self.qr_text = ''
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
        points = None
        while True:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.05)
                continue
            n += 1
            if n % QR_EVERY == 0:
                text, points = qr.detect_qr(frame)
                if text:
                    self.qr_text, self.qr_time = text, time.time()
            if points is not None and time.time() - self.qr_time < QR_HOLD_SEC:
                cv2.polylines(frame, [points.astype(int).reshape(-1, 2)], True, (0, 255, 0), 3)
                cv2.putText(frame, self.qr_text, (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 0), 3)
            _, jpg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            self.jpg = jpg.tobytes()


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
        if camera.qr_time > started and camera.qr_text.upper() in wanted:
            return camera.qr_text.upper()
        time.sleep(0.05)


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
        grip={'open': arm.GRIP_OPEN, 'close': arm.GRIP_CLOSE},
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
    if kind == 'full':
        start_mission(mission.run_full, wait_qr_from_camera)
    elif kind == 'arm':
        side = request.get_json()['side']
        if side not in ('left', 'right'):
            return jsonify(ok=False, error='side 는 left / right'), 400
        start_mission(mission.run_arm_only, side)
    else:
        return jsonify(ok=False, error='알 수 없는 모드'), 404
    return jsonify(ok=True)


@app.before_request
def block_manual_while_running():
    """미션 중에는 서보 버튼·자세 저장을 막는다 (서로 같은 서보를 움직이지 않게)."""
    if request.method == 'POST' and request.path.startswith(('/api/servo', '/api/pose')) and mission_running():
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
