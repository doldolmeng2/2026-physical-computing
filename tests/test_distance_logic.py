"""GPIO 라이브러리만 대체해 hw.py의 새 에코/미수신 처리를 검사한다."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class SensorBase:
    def __init__(self, **kwargs):
        self.max_distance = kwargs['max_distance']

    def _read(self):
        return self.result


class DistanceTests(unittest.TestCase):
    def setUp(self):
        modules = {name: Mock() for name in
                   ('busio', 'cv2', 'adafruit_motor', 'adafruit_pca9685', 'board')}
        modules['gpiozero'] = SimpleNamespace(DistanceSensor=SensorBase)
        path = Path(__file__).resolve().parents[1] / 'hw.py'
        spec = importlib.util.spec_from_file_location('hw_under_test', path)
        self.hw = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, modules):
            spec.loader.exec_module(self.hw)
        self.now = 1.0
        self.on_sleep = lambda: None

        def sleep(seconds):
            self.now += seconds
            self.on_sleep()

        self.hw.time = SimpleNamespace(monotonic=lambda: self.now, sleep=sleep)
        self.sensor = self.hw._FreshDistanceSensor(max_distance=2)
        self.hw._ultra = self.sensor

    def publish(self, result):
        self.sensor.result = result
        self.sensor._read()

    def test_waits_for_new_echo_instead_of_old_distance(self):
        self.publish(0.8)
        self.on_sleep = lambda: self.publish(0.15)
        self.assertAlmostEqual(self.hw.distance_cm(), 30)

    def test_no_echo_is_error_even_with_previous_good_distance(self):
        self.publish(0.8)
        self.on_sleep = lambda: self.publish(None)
        with self.assertRaises(RuntimeError):
            self.hw.distance_cm()

    def test_old_sample_times_out(self):
        self.publish(0.8)
        with self.assertRaises(TimeoutError):
            self.hw.distance_cm(timeout=0.01)

    def test_startup_without_echo_times_out(self):
        with self.assertRaises(TimeoutError):
            self.hw.distance_cm(timeout=0.01)


if __name__ == '__main__':
    unittest.main()
