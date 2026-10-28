"""로봇팔 자세 저장/이동, 집게"""
import json
import time
from pathlib import Path

import hw

POSE_FILE = Path(__file__).with_name('poses.json')

# 미션에서 쓰는 자세 이름. test_arm.py 의 save 명령으로 각도를 저장한다.
# TODO: 실제 로봇으로 각 자세 각도 저장 (필요하면 자세 추가)
POSE_NAMES = ['drive', 'qr', 'left_pick', 'left_place', 'right_pick', 'right_place',
              # QR 보정용 '보는 자세' (웹의 [QR 기준 저장] 으로 저장, align.py 참고)
              'left_pick_view', 'left_place_view', 'right_pick_view', 'right_place_view']

GRIP_OPEN = None    # TODO: test_arm.py 로 집게가 열리는 각도 확인
GRIP_CLOSE = None   # TODO: 물체를 놓치지 않고 잡는 각도 확인 (너무 세게 닫지 않기)


def load_poses():
    if not POSE_FILE.exists():
        return {}
    data = json.loads(POSE_FILE.read_text())
    return {name: {int(ch): a for ch, a in angles.items()} for name, angles in data.items()}


def save_pose(name, angles):
    poses = load_poses()
    poses[name] = angles
    POSE_FILE.write_text(json.dumps(poses, indent=2))


def delete_pose(name):
    poses = load_poses()
    poses.pop(name, None)
    POSE_FILE.write_text(json.dumps(poses, indent=2))


def move_to(angles, step=2, delay=0.02):
    """{채널: 각도} 로 조금씩 이동. 처음(현재 각도 모름)이면 바로 이동"""
    while True:
        done = True
        for ch, goal in angles.items():
            now = hw.get_servo(ch)
            if now is None or abs(goal - now) <= step:
                hw.set_servo(ch, goal)
            else:
                hw.set_servo(ch, now + step if goal > now else now - step)
                done = False
        if done:
            return
        time.sleep(delay)


def go_pose(name, offset=None):
    """offset: {채널: 더할 각도} (QR 보정 결과, align.correct)"""
    poses = load_poses()
    if name not in poses:
        raise KeyError(f"'{name}' 자세가 없습니다. test_arm.py 로 먼저 저장하세요")
    angles = dict(poses[name])
    for ch, d in (offset or {}).items():
        angles[ch] = max(0, min(180, angles[ch] + d))
    move_to(angles)


def grip():
    if GRIP_CLOSE is None:
        raise RuntimeError('arm.py 의 GRIP_CLOSE 를 먼저 채우세요')
    move_to({hw.SERVO_GRIP: GRIP_CLOSE})


def release():
    if GRIP_OPEN is None:
        raise RuntimeError('arm.py 의 GRIP_OPEN 을 먼저 채우세요')
    move_to({hw.SERVO_GRIP: GRIP_OPEN})


def pick(side, offset=None):
    """side: 'left' / 'right', offset: QR 보정 결과 (없으면 저장된 각도 그대로)
    TODO: 집는 순서 확인 (들어 올리는 중간 자세가 필요한지, 넘어뜨리지 않는지)
    """
    release()
    go_pose(f'{side}_pick', offset)
    grip()


def place(side, offset=None):
    """TODO: 놓는 순서 확인 (빈 칸 위치, 놓은 뒤 팔을 빼는 방향)"""
    go_pose(f'{side}_place', offset)
    release()
