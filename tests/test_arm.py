"""로봇팔 테스트: 서보 각도를 하나씩 바꿔 보고, 원하는 자세를 poses.json 에 저장한다.

명령
  <채널> <각도>      절대 각도        예) 2 120
  <채널> +<n> / -<n> 현재에서 더하기  예) 2 +5
  show               현재 각도 보기
  save <이름>        현재 팔 자세(채널 1~3) 저장  예) save left_pick
  go <이름>          저장한 자세로 이동
  list               저장한 자세 목록
  q                  종료
채널: 1 팔 좌우, 2 팔 상하, 3 손목, 4 집게 (TODO: 실제 부위 확인)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # mission 폴더의 hw, arm, qr 사용

import arm
import hw


def show():
    for ch in [hw.SERVO_STEER] + hw.ARM_SERVOS + [hw.SERVO_GRIP]:
        print(f'  채널 {ch}: {hw.get_servo(ch)}')


def main():
    print(__doc__)
    print('시작: 팔과 집게를 90도로 보냅니다')
    arm.move_to({ch: 90 for ch in hw.ARM_SERVOS + [hw.SERVO_GRIP]})
    print('저장할 자세 이름:', ', '.join(arm.POSE_NAMES))

    while True:
        cmd = input('> ').split()
        if not cmd:
            continue
        try:
            if cmd[0] == 'q':
                break
            elif cmd[0] == 'show':
                show()
            elif cmd[0] == 'list':
                for name, angles in arm.load_poses().items():
                    print(f'  {name}: {angles}')
            elif cmd[0] == 'save':
                angles = {ch: hw.get_servo(ch) for ch in hw.ARM_SERVOS}
                arm.save_pose(cmd[1], angles)
                print(f'  저장: {cmd[1]} = {angles}')
            elif cmd[0] == 'go':
                arm.go_pose(cmd[1])
                show()
            else:
                ch = int(cmd[0])
                value = cmd[1]
                if value[0] in '+-':
                    goal = hw.get_servo(ch) + int(value)
                else:
                    goal = int(value)
                arm.move_to({ch: max(0, min(180, goal))})
                print(f'  채널 {ch}: {hw.get_servo(ch)}')
        except (IndexError, ValueError, KeyError, TypeError) as e:
            print('  명령 오류:', e)


if __name__ == '__main__':
    try:
        main()
    finally:
        hw.cleanup()
