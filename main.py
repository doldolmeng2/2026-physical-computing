"""미션 1~5 순서대로 실행

단계별로 나눠 두어서 웹 페이지(webui)에서도 같은 함수를 부른다.
  run_full(wait_qr, look)     미션 1~4 처음부터 (QR → 주행 → 팔)
  run_arm_only(first, look)   QR 결과를 강제로 정하고 미션 3~4 (팔만)
look 을 주면 집기/놓기 전에 상자 QR 로 1차 보정한다 (align.py).
진행 상태는 status 에 기록되고 OLED(display.py)와 웹 페이지에 표시된다.
status.step() 에 쓰는 글자는 OLED 에 나오므로 영문으로 쓴다.
"""
import align
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


def fix(side, action, look):
    """QR 로 1차 보정한 각도 차이. look 이 없으면 보정 없이 {}"""
    if look is None:
        return {}
    offset = align.correct(align.view_name(side, action), look)
    status.detail(f'{side} {action} fix {offset or "none"}')
    return offset


def mission_arm(first, look=None):
    """미션 3~4: 처음 방향 물체 → 반대편 빈 칸, 반대편 물체 → 처음 방향 빈 칸
    look: 카메라로 QR 을 보는 함수 (qr.make_look). 있으면 집기/놓기 전에 QR 로 보정
    """
    second = other(first)
    for n, (side_pick, side_place) in enumerate([(first, second), (second, first)], start=3):
        status.step(f'{n}/4 PICK', f'{side_pick} pick')
        arm.pick(side_pick, fix(side_pick, 'pick', look))
        status.step(f'{n}/4 PLACE', f'{side_place} place')
        arm.place(side_place, fix(side_place, 'place', look))
    status.step('END', 'pose drive')
    arm.go_pose('drive')


def run_task(mode, qr_text, body):
    """body 를 실행하면서 status 에 시작/끝/오류를 기록한다 (OLED·웹에 표시)."""
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


def run_full(wait_qr, look=None):
    """wait_qr: QR 이 보일 때까지 기다렸다가 'LEFT'/'RIGHT' 를 돌려주는 함수
    look: 상자 QR 보정용 (없으면 저장된 각도 그대로)
    """
    def body():
        first = mission_qr(wait_qr)
        mission_drive()
        mission_arm(first, look)
    run_task('FULL', '', body)


def run_arm_only(first, look=None):
    """first: 'left' / 'right' 를 강제로 정하고 팔 미션만 (로봇은 정지선에 미리 둔다)"""
    run_task('ARM', first.upper() + '*', lambda: mission_arm(first, look))


def main():
    display.start()
    cap = hw.open_camera()
    try:
        run_full(lambda: qr.wait_for_qr(cap), qr.make_look(cap))
        print('완료')
    finally:
        hw.cleanup()
        cap.release()


if __name__ == '__main__':
    main()
