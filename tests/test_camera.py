"""카메라 테스트: 브라우저로 웹캠 화면을 보고, 보이는 QR 글자를 출력한다.

실행 후 PC 브라우저에서 http://192.168.50.2:5001 접속. 종료는 Ctrl+C
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # mission 폴더의 hw, arm, qr 사용

import cv2
from flask import Flask, Response

import hw
import qr

app = Flask(__name__)
cap = hw.open_camera()


def frames():
    last = ''
    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        text = qr.read_qr(frame)
        if text and text != last:
            print('QR:', text)
        last = text
        cv2.putText(frame, f'QR: {text}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        _, jpg = cv2.imencode('.jpg', frame)
        yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpg.tobytes() + b'\r\n'


@app.route('/')
def index():
    return Response(frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5001, threaded=True)
    finally:
        cap.release()
