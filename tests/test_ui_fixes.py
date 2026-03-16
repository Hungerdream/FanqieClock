
import sys
import os
import unittest
from unittest.mock import patch
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QLocale
from ui.main_window import MainWindow
from logic.timer import PomodoroTimer
from logic.data_manager import DataManager


class MockTimer(PomodoroTimer):
    def __init__(self):
        super().__init__()
        self.is_running = False

    def start(self):
        self.is_running = True
        self.tick.emit(1500)

    def pause(self):
        self.is_running = False

    def reset(self):
        self.is_running = False


class TestUIBugs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.timer = MockTimer()
        with patch.object(DataManager, 'save_data', return_value=None), \
             patch.object(DataManager, 'save_data_sync', return_value=None):
            self.window = MainWindow(self.timer)
        self.window.show()

    def tearDown(self):
        self.timer.timer.stop()
        self.timer.is_running = False
        for attr in ('sidebar_hide_timer', 'sidebar_poll_timer'):
            t = getattr(self.window, attr, None)
            if t is not None:
                t.stop()
        self.window.close()
        QApplication.processEvents()

    def test_start_button_connections(self):
        """
        Test 1: Start Button Unresponsive
        Verify timer starts (not double-connected start+pause=stopped).
        """
        self.window.timer.is_running = False

        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.start_btn.click()
        self.window.timer.timer.stop()

        self.assertTrue(
            self.window.timer.is_running,
            "Timer should be running after a single start button click. "
            "If it's not, the button may have duplicate signal connections."
        )

    def test_header_layout_alignment(self):
        """
        Test 2: Top Header Visibility
        Check container layout doesn't force AlignHCenter that shrinks the header.
        """
        timer_page = self.window.content_stack.widget(0)
        container = timer_page.findChild(QWidget, "TimerContainer")
        self.assertIsNotNone(container, "TimerContainer not found")

        layout = container.layout()
        alignment = layout.alignment()

        self.assertFalse(
            bool(alignment & Qt.AlignmentFlag.AlignHCenter),
            "TimerContainer has AlignHCenter which prevents the header from stretching full width."
        )

    def test_settings_numerals(self):
        """
        Test 3: Settings Numerals
        Verify spinbox locale produces standard Arabic digits.
        """
        spinbox = self.window.work_mins_spin
        locale = spinbox.locale()
        locale_name = locale.name()

        acceptable = {"en_US", "en_GB", "C", "en"}
        self.assertTrue(
            any(locale_name.startswith(a) for a in acceptable),
            f"Spinbox locale is '{locale_name}', which may produce non-Arabic digits. "
            "Consider explicitly setting spinbox.setLocale(QLocale(QLocale.Language.English))."
        )


if __name__ == '__main__':
    unittest.main()
