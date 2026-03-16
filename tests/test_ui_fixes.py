
import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
import unittest
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QLocale
from ui.main_window import MainWindow
from logic.timer import PomodoroTimer

# Mock Timer to avoid dependency issues
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
        # Create App
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.timer = MockTimer()
        self.window = MainWindow(self.timer)
        self.window.show()

    def tearDown(self):
        if hasattr(self.window, 'sidebar_hide_timer'):
            self.window.sidebar_hide_timer.stop()
        if hasattr(self.window, 'sidebar_poll_timer'):
            self.window.sidebar_poll_timer.stop()
        self.window.close()
        QApplication.processEvents()

    def test_start_button_connections(self):
        """
        Test 1: Start Button Unresponsive
        Check if the button has duplicate connections.
        Note: PyQt doesn't easily expose the number of connections on a signal.
        We simulate a click and verify the timer state is correct.
        """
        # Reset timer state
        self.window.timer.is_running = False

        # Click button once
        self.window.start_btn.click()

        # If connected once: timer should be running.
        # If connected twice: start + pause = stopped (incorrect behavior).
        self.assertTrue(
            self.window.timer.is_running,
            "Timer should be running after a single start button click. "
            "If it's not, the button may have duplicate signal connections."
        )

    def test_header_layout_alignment(self):
        """
        Test 2: Top Header Visibility
        Check if the container layout forces alignment that shrinks the header.
        """
        timer_page = self.window.content_stack.widget(0)
        container = timer_page.findChild(QWidget, "TimerContainer")
        self.assertIsNotNone(container, "TimerContainer not found")
        
        layout = container.layout()
        alignment = layout.alignment()
        
        # Qt.AlignmentFlag.AlignHCenter (0x0004): items are horizontally centered
        # and won't stretch to full width — this would be a layout bug.
        self.assertFalse(
            bool(alignment & Qt.AlignmentFlag.AlignHCenter),
            "TimerContainer has AlignHCenter which prevents the header from stretching full width."
        )

    def test_settings_numerals(self):
        """
        Test 3: Settings Numerals
        Verify that spinbox locale uses English/C locale to ensure Arabic digits (0-9).
        """
        spinbox = self.window.work_mins_spin
        locale = spinbox.locale()
        locale_name = locale.name()

        # Acceptable locales that produce standard Arabic digits
        acceptable = {"en_US", "en_GB", "C", "en"}
        self.assertTrue(
            any(locale_name.startswith(a) for a in acceptable),
            f"Spinbox locale is '{locale_name}', which may produce non-Arabic digits. "
            "Consider explicitly setting spinbox.setLocale(QLocale(QLocale.Language.English))."
        )

if __name__ == '__main__':
    unittest.main()
