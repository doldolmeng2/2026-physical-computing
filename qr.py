"""웹캠 QR 인식 (출발: LEFT/RIGHT, 상자: PICK/PLACE)"""
import time

import cv2

_detector = cv2.QRCodeDetector()


def detect_qr(frame):
    """(글자, 꼭짓점 4개) 를 돌려준다. 못 읽으면 ('', None)"""
    text, points, _ = _detector.detectAndDecode(frame)
    text = text.strip()
    return (text, points) if text else ('', None)


def read_qr(frame):
    """프레임에서 QR 글자를 읽는다. 없으면 ''"""
    return detect_qr(frame)[0]


def detect_all(frame):
    """프레임 안의 QR 을 모두 찾는다 (한 상자에 PICK, PLACE 가 같이 보일 수 있음).
    [{'text', 'cx', 'cy', 'size', 'points'}, ...]  cx/cy = 중심 픽셀, size = 한 변 평균 픽셀
    """
    ok, texts, points, _ = _detector.detectAndDecodeMulti(frame)
    if not ok or points is None:
        return []
    found = []
    for text, pts in zip(texts, points):
        text = text.strip()
        if not text:
            continue
        pts = pts.reshape(-1, 2)
        sides = [float(((pts[i] - pts[(i + 1) % 4]) ** 2).sum() ** 0.5) for i in range(4)]
        found.append({'text': text, 'cx': float(pts[:, 0].mean()), 'cy': float(pts[:, 1].mean()),
                      'size': sum(sides) / 4, 'points': pts})
    return found


def make_look(cap, flush=5):
    """cap 으로 '지금' 프레임을 찍어 detect_all 결과를 돌려주는 함수를 만든다.
    카메라 버퍼에 쌓인 옛 프레임(팔이 움직이기 전)은 flush 개 버린다.
    """
    def look():
        for _ in range(flush):
            cap.grab()
        ok, frame = cap.read()
        return detect_all(frame) if ok else []
    return look


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
