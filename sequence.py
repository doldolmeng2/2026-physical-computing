"""물체 옮기기 시퀀스 (정지선에 선 뒤, 팔만 움직인다)

mode 마다 위치를 한 세트씩 저장한다 (mode1, mode2). 저장은 웹 페이지에서 한다.
  위치 4개   left_pick, right_place, right_pick, left_place  (팔 좌우·상하·손목 각도)
  lift       위치 사이를 옮겨 갈 때 거치는 들어 올린 자세
  grip_open / grip_close   집게 열림/닫힘 각도

출발 QR 이 LEFT 면   left_pick → right_place → right_pick → left_place
          RIGHT 면  right_pick → left_place → left_pick → right_place

집기(pick):  lift → 집게 열기 → 위치 → 집게 닫기 → lift
놓기(place): lift → 위치 → 집게 열기 → lift
"""
import json
from pathlib import Path

import arm
import hw
import status

MODE_FILE = Path(__file__).with_name('modes.json')
MODES = ['mode1', 'mode2']
POSITIONS = ['left_pick', 'right_place', 'right_pick', 'left_place']
LIFT = 'lift'
GRIPS = ['grip_open', 'grip_close']
ORDER = {
    'left': ['left_pick', 'right_place', 'right_pick', 'left_place'],
    'right': ['right_pick', 'left_place', 'left_pick', 'right_place'],
}


def load():
    data = json.loads(MODE_FILE.read_text()) if MODE_FILE.exists() else {}
    data.setdefault('active', MODES[0])
    for m in MODES:
        data.setdefault(m, {})
    return data


def _write(data):
    MODE_FILE.write_text(json.dumps(data, indent=2))


def _check_mode(mode):
    if mode not in MODES:
        raise ValueError(f'mode 는 {MODES} 중 하나')


def active_mode():
    return load()['active']


def set_active(mode):
    _check_mode(mode)
    data = load()
    data['active'] = mode
    _write(data)


def save(mode, name):
    """지금 서보 각도를 mode 의 name 으로 저장. 위치/lift 는 팔 3축, grip_* 은 집게 각도"""
    _check_mode(mode)
    if name in POSITIONS + [LIFT]:
        value = {str(ch): hw.get_servo(ch) for ch in hw.ARM_SERVOS}
        if None in value.values():
            raise RuntimeError('각도를 모르는 서보가 있습니다. 먼저 움직여 주세요')
    elif name in GRIPS:
        value = hw.get_servo(hw.SERVO_GRIP)
        if value is None:
            raise RuntimeError('집게 각도를 모릅니다. 먼저 움직여 주세요')
    else:
        raise ValueError(f'알 수 없는 이름: {name}')
    data = load()
    data[mode][name] = value
    _write(data)


def go(mode, name):
    """mode 의 name 위치(또는 집게 각도)로 이동"""
    _check_mode(mode)
    value = load()[mode].get(name)
    if value is None:
        raise KeyError(f'{mode} 에 {name} 이(가) 저장되지 않았습니다')
    if name in GRIPS:
        arm.move_to({hw.SERVO_GRIP: value})
    else:
        arm.move_to({int(ch): a for ch, a in value.items()})


def missing(mode):
    data = load()[mode]
    return [n for n in POSITIONS + [LIFT] + GRIPS if n not in data]


def run(first, mode):
    """first: 'left' / 'right'. 정지선에 선 뒤 물체 2개를 옮긴다."""
    _check_mode(mode)
    lack = missing(mode)
    if lack:
        raise RuntimeError(f'{mode} 에 저장 안 된 위치: {", ".join(lack)}')
    for i, name in enumerate(ORDER[first], start=1):
        status.step(f'ARM {i}/4', name)
        go(mode, LIFT)
        if name.endswith('_pick'):
            status.detail(f'{name} open')
            go(mode, 'grip_open')
            go(mode, name)
            status.detail(f'{name} close')
            go(mode, 'grip_close')
        else:
            go(mode, name)
            status.detail(f'{name} open')
            go(mode, 'grip_open')
        status.detail(f'{name} lift')
        go(mode, LIFT)
