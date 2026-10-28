"""미션 1~5 순서대로 실행

단계별로 나눠 두어서 웹 페이지(webui)에서도 같은 함수를 부른다.
  run_full(wait_qr, mode)     처음부터 (QR → 주행 → 물체 옮기기)
  run_arm_only(first, mode)   QR 결과를 강제로 정하고 물체 옮기기만
mode 는 'mode1' / 'mode2' (저장한 위치 세트). 없으면 웹에서 고른 mode (modes.json 의 active).
진행 상태는 status 에 기록되고 OLED(display.py)와 웹 페이지에 표시된다.
status.step() 에 쓰는 글자는 OLED 에 나오므로 영문으로 쓴다.
"""
import arm
import display
import drive
import hw
import qr
import sequence
import status


def mission_qr(wait_qr):
    """미션 1: QR 인식. 'left' / 'right' 를 돌려준다."""
    status.step('1/3 QR', 'pose qr')
    arm.go_pose('qr')   # TODO: 출발선에서 모니터 QR이 잘 보이는 자세인지 확인
    status.step('1/3 QR', 'waiting QR')
    first = wait_qr().lower()
    status.set_qr(first.upper())
    return first


def mission_drive():
    """미션 2: 직진, 정지선에서 정지. 이 뒤로 바퀴를 움직이면 실격"""
    status.step('2/3 DRIVE', 'pose drive')
    arm.go_pose('drive')   # TODO: 주행 중 팔 자세 확인 (모니터에 닿지 않게)
    status.step('2/3 DRIVE', 'driving')
    final = drive.drive_to_stop_line()
    status.step('2/3 STOP', f'stop {final:.1f}cm')


def mission_arm(first, mode):
    """미션 3~4: 저장한 위치 4곳을 QR 방향에 맞는 순서로 (sequence.py)"""
    sequence.run(first, mode)
    status.step('END', 'pose drive')
    arm.go_pose('drive')


def run_task(label, qr_text, body):
    """body 를 실행하면서 status 에 시작/끝/오류를 기록한다 (OLED·웹에 표시)."""
    hw.estop(False)
    status.begin(label, qr_text)
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


def _label(kind, mode):
    return f'{kind} m{mode[-1]}'   # 'FULL m1' (OLED 에 짧게)


def run_full(wait_qr, mode=None):
    """wait_qr: QR 이 보일 때까지 기다렸다가 'LEFT'/'RIGHT' 를 돌려주는 함수"""
    mode = mode or sequence.active_mode()

    def body():
        first = mission_qr(wait_qr)
        mission_drive()
        mission_arm(first, mode)
    run_task(_label('FULL', mode), '', body)


def run_arm_only(first, mode=None):
    """first: 'left' / 'right' 를 강제로 정하고 물체 옮기기만 (로봇은 정지선에 미리 둔다)"""
    mode = mode or sequence.active_mode()
    run_task(_label('ARM', mode), first.upper() + '*', lambda: mission_arm(first, mode))


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
