"""PiCar-Pro 하드웨어 (모터, 서보, 초음파, 카메라)

핀/채널 값은 Adeept_PiCar-Pro/Server 의 Move.py, RPIservo.py, Ultra.py 와 같다.
"""
import subprocess
import time

import busio
import cv2
from adafruit_motor import motor, servo
from adafruit_pca9685 import PCA9685
from board import SCL, SDA
from gpiozero import DistanceSensor

# ---- PCA9685 (Robot HAT) ----
PCA_ADDR = 0x5f
PWM_FREQ = 50

# ---- 뒷바퀴 모터 (M1 = 왼쪽, M2 = 오른쪽) ----
MOTOR_M1 = (15, 14)
MOTOR_M2 = (12, 13)
M1_DIR = 1    # TODO: test_motor.py 로 앞으로 가는지 확인 (반대면 -1)
M2_DIR = 1    # TODO: 위와 같음

# ---- 서보 채널 (Adeept 웹 컨트롤러 버튼 기준) ----
SERVO_STEER = 0     # 앞바퀴 조향
SERVO_ARM_ROT = 1   # 팔 좌우 회전   TODO: test_arm.py 로 실제 부위 확인
SERVO_ARM_UP = 2    # 팔 상하        TODO: 위와 같음
SERVO_WRIST = 3     # 손목 상하      TODO: 위와 같음
SERVO_GRIP = 4      # 집게           TODO: 위와 같음
ARM_SERVOS = [SERVO_ARM_ROT, SERVO_ARM_UP, SERVO_WRIST]   # 자세(pose)로 저장하는 서보

STEER_CENTER = 90   # TODO: test_motor.py 로 똑바로 가는 조향 각도 확인

# ---- 초음파 HC-SR04 ----
ULTRA_TRIG = 23
ULTRA_ECHO = 24

# ---- 카메라 (로봇팔 끝 USB 웹캠) ----
CAMERA_INDEX = 0
CAMERA_SIZE = (640, 480)

_pca = None
_motors = {}
_servos = {}
_angles = {}
_ultra = None


def warn_if_webserver_running():
    r = subprocess.run(['systemctl', 'is-active', 'Adeept_Robot.service'],
                       capture_output=True, text=True)
    if r.stdout.strip() == 'active':
        print('[경고] Adeept 웹 컨트롤러가 실행 중입니다. 먼저 끄세요:')
        print('       sudo systemctl stop Adeept_Robot.service')


def get_pca():
    global _pca
    if _pca is None:
        warn_if_webserver_running()
        _pca = PCA9685(busio.I2C(SCL, SDA), address=PCA_ADDR)
        _pca.frequency = PWM_FREQ   # 주파수는 처음 한 번만 설정
    return _pca


# ---------------- 모터 ----------------
def _motor(channels):
    if channels not in _motors:
        pca = get_pca()
        m = motor.DCMotor(pca.channels[channels[0]], pca.channels[channels[1]])
        m.decay_mode = motor.SLOW_DECAY
        _motors[channels] = m
    return _motors[channels]


def drive(speed):
    """speed: -100 ~ 100 (+ 앞으로, - 뒤로, 0 정지)"""
    speed = max(-100, min(100, speed)) / 100
    _motor(MOTOR_M1).throttle = speed * M1_DIR
    _motor(MOTOR_M2).throttle = speed * M2_DIR


def stop():
    drive(0)


# ---------------- 서보 ----------------
def set_servo(ch, angle):
    angle = max(0, min(180, angle))
    if ch not in _servos:
        _servos[ch] = servo.Servo(get_pca().channels[ch],
                                  min_pulse=500, max_pulse=2400, actuation_range=180)
    _servos[ch].angle = angle
    _angles[ch] = angle


def get_servo(ch):
    """마지막으로 보낸 각도 (아직 안 보냈으면 None)"""
    return _angles.get(ch)


def steer(offset=0):
    """STEER_CENTER 기준으로 조향. Adeept 코드에서는 각도를 줄이면 왼쪽 (TODO: 확인)"""
    set_servo(SERVO_STEER, STEER_CENTER + offset)


# ---------------- 초음파 ----------------
class _FreshDistanceSensor(DistanceSensor):
    """gpiozero의 과거 중앙값 대신 새 측정과 에코 실패를 전달한다.

    gpiozero 2.x의 _read() 확장: 반환값은 정규화 거리 또는 None이다.
    기본 queue는 None을 버려 에코가 끊겨도 과거 거리를 계속 내보낸다.
    """
    def __init__(self, **kwargs):
        self.latest_sample = None
        super().__init__(**kwargs)

    def _read(self):
        value = super()._read()
        self.latest_sample = (time.monotonic(), value)
        return value


def distance_cm(timeout=0.5):
    """호출 후 완료된 새 에코 하나를 cm로 반환. 미수신/갱신 중단은 예외."""
    global _ultra
    started = time.monotonic()
    if _ultra is None:
        _ultra = _FreshDistanceSensor(echo=ULTRA_ECHO, trigger=ULTRA_TRIG,
                                     max_distance=2, queue_len=1, partial=True)
    while time.monotonic() - started < timeout:
        sample = _ultra.latest_sample
        if sample is not None and sample[0] > started:
            if sample[1] is None:
                raise RuntimeError('초음파 에코 미수신: 배선과 모니터 방향을 확인하세요')
            return sample[1] * _ultra.max_distance * 100
        time.sleep(0.002)
    raise TimeoutError('초음파 새 측정 시간 초과')


def distance_median(n=5, gap=0.02):
    """n번 재서 중앙값 (값이 튀는 것을 줄임)"""
    vals = []
    for _ in range(n):
        vals.append(distance_cm())
        time.sleep(gap)
    vals.sort()
    return vals[n // 2]


# ---------------- 카메라 ----------------
def open_camera():
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_SIZE[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_SIZE[1])
    if not cap.isOpened():
        raise RuntimeError('카메라를 열 수 없습니다 (USB 연결, 다른 프로그램 사용 여부 확인)')
    return cap


def cleanup():
    if _motors:
        stop()
    if _ultra is not None:
        _ultra.close()
