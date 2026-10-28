"""PC에서 모터 없이 실행: python3 -m unittest discover -s tests -p test_drive_logic.py"""
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class DriveTests(unittest.TestCase):
    def setUp(self):
        self.hw = SimpleNamespace(stop=Mock(), steer=Mock(), drive=Mock(),
                                  distance_cm=Mock())
        path = Path(__file__).resolve().parents[1] / 'drive.py'
        spec = importlib.util.spec_from_file_location('drive_under_test', path)
        self.drive = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'hw': self.hw}):
            spec.loader.exec_module(self.drive)
        self.clock = 0.0
        self.drive.time = SimpleNamespace(monotonic=lambda: self.clock, sleep=lambda _: None)
        self.addCleanup(patch.stopall)
        patch('sys.stdout', new=io.StringIO()).start()

    def readings(self, values):
        values = iter(values)

        def read():
            self.clock += 0.06
            value = next(values)
            if isinstance(value, BaseException):
                raise value
            return value

        self.hw.distance_cm.side_effect = read

    def test_approach_decelerates_and_stays_stopped(self):
        self.readings([80, 49, 37, 40, 30, 30.2, 29.9, 30, 30.1, 30])
        self.assertEqual(self.drive.drive_to_stop_line(), 30)
        self.assertEqual([c.args[0] for c in self.hw.drive.call_args_list], [30, 22, 18])
        self.hw.stop.assert_called()

    def test_already_at_line_does_not_move(self):
        self.readings([30] * 6)
        self.drive.drive_to_stop_line()
        self.hw.drive.assert_not_called()

    def test_sensor_failure_and_interrupt_stop_motor(self):
        for error in (RuntimeError('no echo'), TimeoutError(), KeyboardInterrupt()):
            with self.subTest(error=type(error)):
                self.hw.stop.reset_mock()
                self.readings([70, error])
                with self.assertRaises(type(error)):
                    self.drive.drive_to_stop_line()
                self.hw.stop.assert_called()

    def test_invalid_distances_stop_motor(self):
        for value in (float('nan'), float('inf'), 0, -1, 200):
            with self.subTest(value=value):
                self.hw.drive.reset_mock()
                self.readings([value])
                with self.assertRaises(RuntimeError):
                    self.drive.drive_to_stop_line()
                self.hw.drive.assert_not_called()
                self.hw.stop.assert_called()

    def test_false_close_echo_or_overshoot_does_not_restart(self):
        for final in (60, 28):
            with self.subTest(final=final):
                self.hw.drive.reset_mock()
                self.readings([70, 30] + [final] * 5)
                with self.assertRaises(RuntimeError):
                    self.drive.drive_to_stop_line()
                self.assertEqual(self.hw.drive.call_count, 1)
                self.hw.stop.assert_called()

    def test_timeout_stops_motor(self):
        self.drive.MAX_DRIVE_SECONDS = 0.15
        self.readings([70] * 10)
        with self.assertRaises(TimeoutError):
            self.drive.drive_to_stop_line()
        self.hw.stop.assert_called()

    def test_braking_and_sensor_offset(self):
        self.drive.BRAKE_ADVANCE_CM = 0.5
        self.drive.DISTANCE_OFFSET_CM = 1.0
        self.readings([60, 29.5] + [29] * 5)
        self.assertEqual(self.drive.drive_to_stop_line(), 30)

    def test_bad_configuration_does_not_move(self):
        self.drive.CREEP_SPEED = -1
        with self.assertRaises(ValueError):
            self.drive.drive_to_stop_line()
        self.hw.drive.assert_not_called()
        self.hw.stop.assert_called()


if __name__ == '__main__':
    unittest.main()
