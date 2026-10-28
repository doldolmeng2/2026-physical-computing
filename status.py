"""미션 진행 상태. main.py 가 바꾸고, OLED(display.py)와 웹 페이지가 읽는다."""
import threading
import time

_lock = threading.Lock()
_abort = threading.Event()

_state = {
    'mode': 'IDLE',     # IDLE / FULL (main 처음부터) / ARM (팔 미션만)
    'qr': '',           # 'LEFT' / 'RIGHT' (강제 지정이면 'LEFT*')
    'step': '',         # 짧은 단계 이름 (OLED 한 줄, 영문)  예) '2/4 DRIVE'
    'detail': '',       # 세부 내용 (영문)                    예) 'stop 30.2cm'
    'error': '',
    'running': False,
    'log': [],          # (시각, 메시지) 최근 30개
}


class Aborted(Exception):
    """웹 정지 버튼으로 미션을 멈췄다."""


def _log(msg):
    _state['log'] = (_state['log'] + [(time.strftime('%H:%M:%S'), msg)])[-30:]


def begin(mode, qr=''):
    _abort.clear()
    with _lock:
        _state.update(mode=mode, qr=qr, step='START', detail='', error='', running=True, log=[])
        _log(f'시작: {mode}')


def set_qr(qr):
    with _lock:
        _state['qr'] = qr
        _log(f'QR: {qr}')


def step(name, detail=''):
    """단계가 바뀔 때 부른다. 정지 버튼이 눌렸으면 여기서 Aborted 를 낸다."""
    check_abort()
    with _lock:
        _state.update(step=name, detail=detail)
        _log(f'{name} {detail}'.strip())


def detail(text):
    """단계는 그대로 두고 세부 내용만 바꾼다."""
    check_abort()
    with _lock:
        _state['detail'] = text
        _log(f'{_state["step"]} {text}')


def finish(error=''):
    with _lock:
        _state.update(running=False, error=error, step='ERROR' if error else 'DONE')
        _log(f'오류: {error}' if error else '완료')


def request_abort():
    _abort.set()


def check_abort():
    if _abort.is_set():
        raise Aborted('정지 버튼')


def snapshot():
    with _lock:
        return dict(_state)
