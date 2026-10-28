"""팔 자세 저장용 웹 페이지: 카메라 화면 + 인식 중인 QR + 서보 버튼 + 자세 저장/불러오기

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
import hw
import qr

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
    )


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
    camera = CameraWorker()
    distance = DistanceWorker()
    print(f'브라우저에서 http://192.168.50.2:{PORT} 접속 (종료: Ctrl+C)')
    try:
        app.run(host='0.0.0.0', port=PORT, threaded=True)
    finally:
        hw.cleanup()
