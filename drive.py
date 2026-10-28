"""직진 후 정지선(모니터 앞 30cm)에서 정지"""
import hw

STOP_DISTANCE_CM = None   # TODO: 초음파 센서를 빨간 정지선 위에 두고 test_ultrasonic.py 값 확인
DRIVE_SPEED = None        # TODO: test_motor.py 로 정지선을 넘지 않고 멈출 수 있는 속도 확인
# TODO: 멈출 때 밀리는 거리 확인 → 필요하면 STOP_DISTANCE_CM 을 조금 크게 / 감속 구간 추가
# TODO: 똑바로 가지 않으면 조향 보정 필요 여부 확인 (자이로 사용은 나중에)


def drive_to_stop_line():
    if STOP_DISTANCE_CM is None or DRIVE_SPEED is None:
        raise RuntimeError('drive.py 의 TODO 값을 먼저 채우세요')
    hw.steer(0)
    hw.drive(DRIVE_SPEED)
    try:
        while hw.distance_median(3) > STOP_DISTANCE_CM:
            pass
    finally:
        hw.stop()
