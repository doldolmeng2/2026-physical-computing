"""초음파 센서에서 모니터 전면까지 30cm인 정지선으로 직진한다."""
import math
import statistics
import time

import hw

STOP_DISTANCE_CM = 30.0
DISTANCE_OFFSET_CM = 0.0  # 실제 거리 - 센서 표시값 (자로 재서 보정)
BRAKE_ADVANCE_CM = 0.0    # 정지 명령 후 밀린 거리만큼 미리 정지 (실측 후 보정)
DRIVE_SPEED = 30         # PWM %, 실차에서 전진 방향과 속도를 먼저 확인
SLOW_SPEED = 22
CREEP_SPEED = 18
SLOW_DISTANCE_CM = 50.0
CREEP_DISTANCE_CM = 38.0
STOP_TOLERANCE_CM = 1.0  # 폭 2cm 빨간 선의 중심 기준. 측정상 허용 오차
MAX_DRIVE_SECONDS = 20.0
SETTLE_SECONDS = 0.3


def _distance():
    raw = hw.distance_cm()
    if not math.isfinite(raw) or not 2.0 <= raw < 200.0:
        raise RuntimeError(f'초음파 측정 범위 오류: {raw!r} cm')
    distance = raw + DISTANCE_OFFSET_CM
    if not 2.0 <= distance < 200.0:
        raise RuntimeError(f'초음파 보정 범위 오류: {distance!r} cm')
    return distance


def _validate_settings():
    values = (STOP_DISTANCE_CM, DISTANCE_OFFSET_CM, BRAKE_ADVANCE_CM,
              DRIVE_SPEED, SLOW_SPEED, CREEP_SPEED, SLOW_DISTANCE_CM,
              CREEP_DISTANCE_CM, STOP_TOLERANCE_CM, MAX_DRIVE_SECONDS,
              SETTLE_SECONDS)
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
        raise ValueError('drive.py 설정값은 유한한 숫자여야 합니다')
    if not 0 < CREEP_SPEED <= SLOW_SPEED <= DRIVE_SPEED <= 100:
        raise ValueError('속도는 0 < CREEP <= SLOW <= DRIVE <= 100 이어야 합니다')
    if not 2 <= STOP_DISTANCE_CM + BRAKE_ADVANCE_CM < CREEP_DISTANCE_CM < SLOW_DISTANCE_CM < 200:
        raise ValueError('정지 거리 < 근접 감속 거리 < 감속 거리를 확인하세요')
    if BRAKE_ADVANCE_CM < 0 or not 0 < STOP_TOLERANCE_CM <= 1:
        raise ValueError('제동 보정은 0 이상, 정지 허용 오차는 0 초과 1cm 이하입니다')
    if MAX_DRIVE_SECONDS <= 0 or SETTLE_SECONDS < 0:
        raise ValueError('주행 제한 시간과 정지 안정화 시간을 확인하세요')


def drive_to_stop_line():
    """정지 후 확인한 거리(cm)를 반환. 실패 시 예외로 팔 미션 진행을 막는다.

    빨간색 자체를 인식하지 않는다. 센서가 모니터 정면을 향하고 빨간 선의
    중심이 모니터에서 30cm인 배치를 전제로 한다. 정지 후 재전진/후진은 없다.
    """
    try:
        hw.stop()
        _validate_settings()
        hw.steer(0)
        deadline = time.monotonic() + MAX_DRIVE_SECONDS
        stop_at = STOP_DISTANCE_CM + BRAKE_ADVANCE_CM
        speed = None
        while True:
            if time.monotonic() >= deadline:
                raise TimeoutError('정지선에 도달하지 못했습니다. 방향/속도/센서를 확인하세요')
            # hw.distance_cm()은 새 에코를 기다리며, 미수신/시간 초과 시 예외.
            distance = _distance()
            if time.monotonic() >= deadline:
                raise TimeoutError('최대 주행 시간이 초과되었습니다')
            if distance <= stop_at:
                hw.stop()  # 중앙값을 기다리며 선을 넘지 않도록 먼저 멈춘다.
                break
            next_speed = (CREEP_SPEED if distance <= CREEP_DISTANCE_CM else
                          SLOW_SPEED if distance <= SLOW_DISTANCE_CM else DRIVE_SPEED)
            # 접근 중 센서 값이 튀어도 다시 가속하지 않는다.
            if speed is None or next_speed < speed:
                speed = next_speed
                hw.drive(speed)
                print(f'[주행] {distance:.1f} cm / PWM {speed}%')

        time.sleep(SETTLE_SECONDS)
        final = statistics.median(_distance() for _ in range(5))
        error = final - STOP_DISTANCE_CM
        print(f'[정지] {final:.2f} cm / 목표 대비 {error:+.2f} cm')
        if abs(error) > STOP_TOLERANCE_CM:
            raise RuntimeError(
                '정지 위치가 허용 범위 밖입니다. 바퀴를 다시 움직이지 않습니다. '
                '센서 오프셋/속도/BRAKE_ADVANCE_CM을 보정한 뒤 다시 출발하세요')
        return final
    finally:
        hw.stop()


if __name__ == '__main__':
    try:
        drive_to_stop_line()
    except KeyboardInterrupt:
        print('\n사용자 중단: 모터 정지')
    finally:
        hw.cleanup()
