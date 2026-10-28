"""QR 로 1차 위치 보정 → 저장된 각도로 집기/놓기

생각:
  카메라와 집게는 서로 고정, 상자 QR 과 물체의 위치도 고정이다.
  그래서 '보는 자세(view)' 에서 QR 이 기준과 같은 곳에 보이게 팔을 맞추면,
  카메라-물체 관계가 기준 때와 같아진다. 그 뒤에는 저장된 '집는 자세' 로 가되
  보는 자세에서 맞춘 만큼(각도 차이)만 더해서 간다.

준비 (로봇을 이상적인 정지 위치에 두고, 웹 페이지에서):
  1. left_pick_view 처럼 QR 이 잘 보이는 자세를 만들고 [QR 기준 저장]
     → 자세 저장 + 그때 QR 위치(기준) 저장 + 축별 게인(1도에 몇 픽셀) 측정
  2. 같은 위치에서 left_pick (실제로 집는 자세) 저장
실행:
  view 자세 → QR 이 기준 위치로 오도록 팔을 조금씩 움직임 → 움직인 각도(offset) 를
  집는 자세에 더해서 이동. QR 을 못 찾으면 offset 없이 (하드코딩 그대로) 진행한다.
"""
import json
import time
from pathlib import Path

import arm
import hw
import status

REF_FILE = Path(__file__).with_name('qr_refs.json')

QR_TEXT = {'pick': 'PICK', 'place': 'PLACE'}   # TODO: 실제 상자 QR 글자 확인 (웹 화면에 표시됨)

# 보정에 쓰는 축: (서보 채널, QR 값)  팔 좌우 회전 ↔ 화면 가로 위치
AXES = [(hw.SERVO_ARM_ROT, 'cx')]
# TODO: 앞뒤/높이 오차도 크면 팔 상하 ↔ 화면 세로 위치 추가 후 시험
# AXES.append((hw.SERVO_ARM_UP, 'cy'))

GAIN_TEST_DEG = 4      # 게인 측정할 때 움직여 볼 각도
TOL_PX = 8             # 기준과 이만큼(픽셀) 안이면 맞춘 것으로 본다     TODO: 시험 후 조정
MAX_ITERS = 6          # 최대 반복 횟수
MAX_STEP_DEG = 6       # 한 번에 최대로 움직일 각도
MAX_TOTAL_DEG = 15     # 기준 자세에서 이보다 많이 벗어나야 하면 이상한 것 → 보정 안 함
SETTLE_SEC = 0.3       # 서보가 멈추고 화면이 흔들리지 않을 때까지 기다리는 시간
LOOK_TRIES = 5         # QR 못 찾을 때 다시 볼 횟수


def view_name(side, action):
    return f'{side}_{action}_view'


def load_refs():
    if not REF_FILE.exists():
        return {}
    return json.loads(REF_FILE.read_text())


def _save_ref(name, ref):
    refs = load_refs()
    refs[name] = ref
    REF_FILE.write_text(json.dumps(refs, indent=2))


def delete_ref(name):
    refs = load_refs()
    if refs.pop(name, None) is not None:
        REF_FILE.write_text(json.dumps(refs, indent=2))


def find(look, want):
    """want 글자의 QR 하나를 찾는다. 여러 번 봐도 없으면 None"""
    for _ in range(LOOK_TRIES):
        for d in look():
            if d['text'].upper() == want:
                return d
        time.sleep(0.1)
    return None


def _settle_and_find(look, want):
    time.sleep(SETTLE_SEC)
    return find(look, want)


def teach(name, look):
    """지금 팔 자세를 name 으로 저장하고, 그때 보이는 QR 을 기준으로 저장, 축별 게인 측정.
    name 은 left_pick_view 처럼 _pick_view / _place_view 로 끝나야 한다.
    """
    action = 'pick' if name.endswith('_pick_view') else 'place' if name.endswith('_place_view') else None
    if action is None:
        raise ValueError("이름은 '..._pick_view' 또는 '..._place_view' 여야 합니다")
    want = QR_TEXT[action]
    angles = {ch: hw.get_servo(ch) for ch in hw.ARM_SERVOS}
    if None in angles.values():
        raise RuntimeError('각도를 모르는 서보가 있습니다. 먼저 움직여 주세요')

    base = _settle_and_find(look, want)
    if base is None:
        raise RuntimeError(f'{want} QR 이 안 보입니다')
    ref = {'text': want, 'cx': base['cx'], 'cy': base['cy'], 'size': base['size'], 'gain': {}}

    # 축마다 GAIN_TEST_DEG 만큼 움직여 보고 QR 이 몇 픽셀 움직이는지 잰다 (부호 포함)
    for ch, key in AXES:
        arm.move_to({ch: angles[ch] + GAIN_TEST_DEG})
        moved = _settle_and_find(look, want)
        arm.move_to({ch: angles[ch]})
        if moved is None:
            raise RuntimeError(f'채널 {ch} 를 {GAIN_TEST_DEG}° 움직이니 QR 이 안 보입니다. QR 이 화면 가운데 오게 하세요')
        px_per_deg = (moved[key] - base[key]) / GAIN_TEST_DEG
        if abs(px_per_deg) < 1:
            raise RuntimeError(f'채널 {ch} 를 움직여도 QR 이 거의 안 움직입니다 ({px_per_deg:.2f} px/°)')
        ref['gain'][str(ch)] = px_per_deg

    arm.save_pose(name, angles)
    _save_ref(name, ref)
    return ref


def correct(name, look):
    """name(view 자세)으로 가서 QR 이 기준 위치에 오도록 맞춘다.
    돌려주는 값: {채널: 더할 각도}  (못 맞추면 {} → 하드코딩 그대로)
    """
    ref = load_refs().get(name)
    poses = arm.load_poses()
    if ref is None or name not in poses:
        status.detail(f'{name} no ref')
        return {}

    view = poses[name]
    arm.move_to(view)
    for i in range(MAX_ITERS):
        d = _settle_and_find(look, ref['text'])
        if d is None:
            status.detail('QR lost, no fix')
            return {}
        errs = {ch: d[key] - ref[key] for ch, key in AXES}
        status.detail('err ' + ' '.join(f'{e:+.0f}px' for e in errs.values()))
        if all(abs(e) <= TOL_PX for e in errs.values()):
            break
        goal = {}
        for ch, key in AXES:
            step = -errs[ch] / ref['gain'][str(ch)]
            step = max(-MAX_STEP_DEG, min(MAX_STEP_DEG, step))
            goal[ch] = round(hw.get_servo(ch) + step)
            if abs(goal[ch] - view[ch]) > MAX_TOTAL_DEG:
                status.detail('fix too big, no fix')
                arm.move_to(view)
                return {}
        arm.move_to(goal)

    return {ch: hw.get_servo(ch) - view[ch] for ch, _ in AXES}
