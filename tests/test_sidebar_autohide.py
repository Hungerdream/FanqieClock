
import sys
import os
import unittest
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer

# Ensure path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from ui.main_window import MainWindow
from logic.timer import PomodoroTimer
from logic.data_manager import DataManager


class TestSidebarAutoHide(unittest.TestCase):
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
        self.window.sidebar.setFixedWidth(85)

    def tearDown(self):
        self.timer.timer.stop()
        self.timer.is_running = False
        for attr in ('sidebar_hide_timer', 'sidebar_poll_timer'):
            t = getattr(self.window, attr, None)
            if t is not None:
                t.stop()
        self.window.close()
        QApplication.processEvents()

    def test_sidebar_collapse_on_start(self):
        self.assertEqual(self.window.sidebar.width(), 85)

        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.toggle_timer()
        self.timer.timer.stop()  # Stop real tick to prevent auto-finish loop

        self.assertTrue(hasattr(self.window, 'anim_group'))
        from PyQt6.QtCore import QAbstractAnimation
        self.assertEqual(self.window.anim_group.state(), QAbstractAnimation.State.Running)
        self.assertEqual(self.window.anim_min.endValue(), 0)
        self.assertEqual(self.window.anim_max.endValue(), 0)

    def test_sidebar_expand_on_stop(self):
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.toggle_timer()
        self.timer.timer.stop()

        self.window.stop_timer()

        from PyQt6.QtCore import QAbstractAnimation
        if self.window.anim_group.state() == QAbstractAnimation.State.Running:
            self.assertEqual(self.window.anim_min.endValue(), 85)
        else:
            self.assertEqual(self.window.sidebar.width(), 85)

    def test_sidebar_hover_behavior(self):
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.toggle_timer()
        self.timer.timer.stop()
        self.window.sidebar.setFixedWidth(0)

        from PyQt6.QtCore import QEvent
        enter_event = QEvent(QEvent.Type.Enter)
        self.window.eventFilter(self.window.sidebar, enter_event)
        self.assertEqual(self.window.anim_min.endValue(), 85)

        self.window.sidebar.setFixedWidth(85)

        leave_event = QEvent(QEvent.Type.Leave)
        self.window.eventFilter(self.window.sidebar, leave_event)
        self.assertTrue(self.window.sidebar_hide_timer.isActive())

        self.window.move(100, 100)
        self.window.check_and_hide_sidebar()
        self.assertEqual(self.window.anim_min.endValue(), 0)


if __name__ == '__main__':
    unittest.main()
