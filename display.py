"""OLED(128x64)에 배터리 전압과 미션 상태를 보여준다.

OLED 기본 글꼴은 영문만 나오므로 status 의 step/detail 은 영문으로 쓴다.
전압 계산은 Adeept_PiCar-Pro/Server/Voltage.py 와 같다 (ADS7830, 채널 0).
OLED 나 ADC 가 없으면 조용히 아무것도 하지 않는다.

    import display
    display.start()     # 백그라운드에서 0.5초마다 갱신
"""
import threading
import time

import status

OLED_ADDR = 0x3C
ADC_ADDR = 0x48
ADC_CMD = 0x84
ADC_CHANNEL = 0
ADC_VREF = 4.93
DIVISION_RATIO = 1000 / (3000 + 1000)   # R17 / (R15 + R17)
LOW_VOLTAGE = 6.3                        # 이보다 낮으면 'LOW' 표시 (Adeept 경고 기준)
REFRESH_SEC = 0.5

_started = False


def read_voltage(bus):
    """배터리 전압(V). 10번 읽어 중앙값."""
    ch = ADC_CHANNEL
    cmd = ADC_CMD | (((ch << 2 | ch >> 1) & 0x07) << 4)
    values = sorted(bus.read_byte_data(ADC_ADDR, cmd) for _ in range(10))
    return values[5] / 255.0 * ADC_VREF / DIVISION_RATIO


def _lines(volt):
    s = status.snapshot()
    bat = 'BAT --' if volt is None else f'BAT {volt:.2f}V' + (' LOW' if volt < LOW_VOLTAGE else '')
    return [
        f'{bat}  {time.strftime("%H:%M:%S")}',
        f'MODE {s["mode"]}' + (' RUN' if s['running'] else ''),
        f'QR   {s["qr"] or "-"}',
        f'STEP {s["step"] or "-"}',
        s['detail'][:21],
        ('ERR ' + s['error'])[:21] if s['error'] else '',
    ]


def _loop():
    from luma.core.interface.serial import i2c
    from luma.core.render import canvas
    from luma.oled.device import ssd1306
    device = ssd1306(i2c(port=1, address=OLED_ADDR), rotate=0)
    try:
        import smbus
        bus = smbus.SMBus(1)
    except Exception:
        bus = None
    while True:
        try:
            volt = read_voltage(bus) if bus else None
        except OSError:
            volt = None
        with canvas(device) as draw:
            for i, line in enumerate(_lines(volt)):
                draw.text((0, i * 10), line, fill='white')
        time.sleep(REFRESH_SEC)


def _run():
    try:
        _loop()
    except Exception as e:   # OLED 없음, 라이브러리 없음 등
        print('[OLED] 표시 안 함:', e)


def start():
    global _started
    if not _started:
        _started = True
        threading.Thread(target=_run, daemon=True).start()
