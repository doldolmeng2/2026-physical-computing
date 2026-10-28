"""로봇팔 공통 자세(drive, qr) 저장/이동, 천천히 움직이기

물체를 옮기는 위치(mode 별 4곳 + lift + 집게 각도)는 sequence.py 에서 다룬다.
"""
import json
import time
from pathlib import Path

import hw

POSE_FILE = Path(__file__).with_name('poses.json')

# mode 와 상관없이 쓰는 자세. 웹 페이지나 test_arm.py 의 save 명령으로 저장한다.
POSE_NAMES = ['drive', 'qr']


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


def go_pose(name):
    poses = load_poses()
    if name not in poses:
        raise KeyError(f"'{name}' 자세가 없습니다. 웹 페이지나 test_arm.py 로 먼저 저장하세요")
    move_to(poses[name])
