"""초음파 테스트: 0.2초마다 거리(cm)를 출력한다. 종료는 Ctrl+C

raw    = 한 번 잰 값
median = 5번 재서 중앙값 (drive.py 에서 쓰는 방식)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # mission 폴더의 hw, arm, qr 사용

import time

import hw

try:
    while True:
        raw = hw.distance_cm()
        med = hw.distance_median(5)
        print(f'raw {raw:6.1f} cm   median {med:6.1f} cm')
        time.sleep(0.2)
except KeyboardInterrupt:
    pass
finally:
    hw.cleanup()
