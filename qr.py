"""웹캠 QR 인식 (출발: LEFT/RIGHT, 상자: PICK/PLACE)"""
import time

import cv2

_detector = cv2.QRCodeDetector()


def read_qr(frame):
    """프레임에서 QR 글자를 읽는다. 없으면 ''"""
    text, _, _ = _detector.detectAndDecode(frame)
    return text.strip()


def wait_for_qr(cap, wanted=('LEFT', 'RIGHT'), timeout=None):
    """wanted 중 하나가 보일 때까지 기다린다. 시간 초과면 None
    TODO: 실제 QR 글자가 'LEFT'/'RIGHT' 그대로인지 test_camera.py 로 확인
    """
    start = time.time()
    while timeout is None or time.time() - start < timeout:
        ok, frame = cap.read()
        if not ok:
            continue
        text = read_qr(frame).upper()
        if text in wanted:
            return text
    return None
