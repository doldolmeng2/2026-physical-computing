"""미션 1~5 순서대로 실행

단계별로 나눠 두어서 웹 페이지(webui)에서도 같은 함수를 부른다.
  run_full(wait_qr)     미션 1~4 처음부터 (QR → 주행 → 팔)
  run_arm_only(first)   QR 결과를 강제로 정하고 미션 3~4 (팔만)
진행 상태는 status 에 기록되고 OLED(display.py)와 웹 페이지에 표시된다.
status.step() 에 쓰는 글자는 OLED 에 나오므로 영문으로 쓴다.
"""
import arm
import display
import drive
import hw
import qr
import status


def other(side):
    return 'right' if side == 'left' else 'left'


def mission_qr(wait_qr):
    """미션 1: QR 인식. 'left' / 'right' 를 돌려준다."""
    status.step('1/4 QR', 'pose qr')
    arm.go_pose('qr')   # TODO: 출발선에서 모니터 QR이 잘 보이는 자세인지 확인
    status.step('1/4 QR', 'waiting QR')
    first = wait_qr().lower()
    status.set_qr(first.upper())
    return first


def mission_drive():
    """미션 2: 직진, 정지선에서 정지. 이 뒤로 바퀴를 움직이면 실격"""
    status.step('2/4 DRIVE', 'pose drive')
    arm.go_pose('drive')   # TODO: 주행 중 팔 자세 확인 (모니터에 닿지 않게)
    status.step('2/4 DRIVE', 'driving')
    final = drive.drive_to_stop_line()
    status.step('2/4 STOP', f'stop {final:.1f}cm')


def mission_arm(first):
    """미션 3~4: 처음 방향 물체 → 반대편 빈 칸, 반대편 물체 → 처음 방향 빈 칸"""
    second = other(first)
    status.step('3/4 PICK', f'{first} pick')
    arm.pick(first)
    status.step('3/4 PLACE', f'{second} place')
    arm.place(second)
    status.step('4/4 PICK', f'{second} pick')
    arm.pick(second)
    status.step('4/4 PLACE', f'{first} place')
    arm.place(first)
    status.step('END', 'pose drive')
    arm.go_pose('drive')


def _run(mode, qr_text, body):
    hw.estop(False)
    status.begin(mode, qr_text)
    try:
        body()
        status.finish()
    except status.Aborted:
        status.finish('STOPPED')
    except Exception as e:
        status.finish(f'{type(e).__name__}: {e}')
        raise
    finally:
        hw.stop()


def run_full(wait_qr):
    """wait_qr: QR 이 보일 때까지 기다렸다가 'LEFT'/'RIGHT' 를 돌려주는 함수"""
    def body():
        first = mission_qr(wait_qr)
        mission_drive()
        mission_arm(first)
    _run('FULL', '', body)


def run_arm_only(first):
    """first: 'left' / 'right' 를 강제로 정하고 팔 미션만 (로봇은 정지선에 미리 둔다)"""
    _run('ARM', first.upper() + '*', lambda: mission_arm(first))


def main():
    display.start()
    cap = hw.open_camera()
    try:
        run_full(lambda: qr.wait_for_qr(cap))
        print('완료')
    finally:
        hw.cleanup()
        cap.release()


if __name__ == '__main__':
    main()
