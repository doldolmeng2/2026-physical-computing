"""바퀴 테스트: 처음엔 차를 바닥에서 띄우고 실행하세요.

명령
  f <속도> <초>   앞으로     예) f 30 1
  b <속도> <초>   뒤로       예) b 30 1
  st <오프셋>     조향 (STEER_CENTER 기준)  예) st -30, st 0
  sa <각도>       조향 각도 직접 설정 (STEER_CENTER 찾기용)  예) sa 85
  q               종료
속도 0~100
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # mission 폴더의 hw, arm, qr 사용

import time

import hw


def run(speed, sec):
    hw.drive(speed)
    try:
        time.sleep(sec)
    finally:
        hw.stop()


def main():
    print(__doc__)
    hw.steer(0)
    while True:
        cmd = input('> ').split()
        if not cmd:
            continue
        try:
            if cmd[0] == 'q':
                break
            elif cmd[0] == 'f':
                run(int(cmd[1]), float(cmd[2]))
            elif cmd[0] == 'b':
                run(-int(cmd[1]), float(cmd[2]))
            elif cmd[0] == 'st':
                hw.steer(int(cmd[1]))
                print(f'  조향 각도: {hw.get_servo(hw.SERVO_STEER)}')
            elif cmd[0] == 'sa':
                hw.set_servo(hw.SERVO_STEER, int(cmd[1]))
                print(f'  조향 각도: {hw.get_servo(hw.SERVO_STEER)}')
            else:
                print('  알 수 없는 명령')
        except (IndexError, ValueError) as e:
            print('  명령 오류:', e)


if __name__ == '__main__':
    try:
        main()
    finally:
        hw.cleanup()
