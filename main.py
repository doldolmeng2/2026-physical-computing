"""미션 1~5 순서대로 실행"""
import arm
import drive
import hw
import qr


def main():
    cap = hw.open_camera()
    try:
        # 미션 1: QR 인식 후 출발
        arm.go_pose('qr')   # TODO: 출발선에서 모니터 QR이 잘 보이는 자세인지 확인
        print('QR 대기 중...')
        first = qr.wait_for_qr(cap).lower()   # 'left' / 'right'
        second = 'right' if first == 'left' else 'left'
        print('QR:', first)

        # 미션 2: 직진, 정지선에서 정지
        arm.go_pose('drive')   # TODO: 주행 중 팔 자세 확인 (모니터에 닿지 않게)
        drive.drive_to_stop_line()
        # 여기부터 바퀴를 움직이면 실격

        # 미션 3: 처음 방향 물체 → 반대편 빈 칸
        arm.pick(first)
        arm.place(second)

        # 미션 4: 반대편에 남은 물체 → 처음 방향 빈 칸
        arm.pick(second)
        arm.place(first)

        arm.go_pose('drive')
        print('완료')
    finally:
        hw.cleanup()
        cap.release()


if __name__ == '__main__':
    main()
