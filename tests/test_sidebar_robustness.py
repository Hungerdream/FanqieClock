
import sys
import os
import unittest
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QEvent, QTimer

# Ensure path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from ui.main_window import MainWindow
from logic.timer import PomodoroTimer
from logic.data_manager import DataManager


class TestSidebarRobustness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.timer = PomodoroTimer()
        with patch.object(DataManager, 'save_data', return_value=None), \
             patch.object(DataManager, 'save_data_sync', return_value=None):
            self.window = MainWindow(self.timer)
        self.window.show()
        self.window.auto_hide_sidebar_toggle.setChecked(True)
        # Mark timer as running without real tick
        self.timer.start()
        self.timer.timer.stop()
        self.window.sidebar.setFixedWidth(0)
        QApplication.processEvents()

    def tearDown(self):
        self.timer.timer.stop()
        self.timer.is_running = False
        for attr in ('sidebar_hide_timer', 'sidebar_poll_timer'):
            t = getattr(self.window, attr, None)
            if t is not None:
                t.stop()
        self.window.close()
        QApplication.processEvents()

    def test_enter_event_expands_immediately(self):
        """Test Enter event triggers expansion immediately"""
        event = QEvent(QEvent.Type.Enter)
        self.window.eventFilter(self.window.sidebar, event)

        self.assertTrue(hasattr(self.window, 'anim_group'))
        self.assertEqual(self.window.anim_min.endValue(), 85)

    def test_leave_event_delays_hide(self):
        """Test Leave event starts timer instead of hiding immediately"""
        self.window.sidebar.setFixedWidth(85)

        event = QEvent(QEvent.Type.Leave)
        self.window.eventFilter(self.window.sidebar, event)

        self.assertTrue(self.window.sidebar_hide_timer.isActive())

        self.window.move(100, 100)
        self.window.check_and_hide_sidebar()
        self.assertEqual(self.window.anim_min.endValue(), 0)

    def test_fast_reentry_cancels_hide(self):
        """Test Leave then fast Enter cancels the hide timer"""
        self.window.sidebar.setFixedWidth(80)
        self.window.animate_sidebar(85)
        self.window.sidebar.setFixedWidth(85)

        event = QEvent(QEvent.Type.Leave)
        self.window.eventFilter(self.window.sidebar, event)
        self.assertTrue(self.window.sidebar_hide_timer.isActive())

        event = QEvent(QEvent.Type.Enter)
        self.window.eventFilter(self.window.sidebar, event)

        self.assertFalse(self.window.sidebar_hide_timer.isActive())
        self.assertEqual(self.window.anim_min.endValue(), 85)


if __name__ == '__main__':
    unittest.main()
