
import sys
import os
import unittest
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QEvent

# Ensure path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from ui.main_window import MainWindow
from logic.timer import PomodoroTimer
from logic.data_manager import DataManager


class TestSidebarFix(unittest.TestCase):
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
        QApplication.processEvents()

    def tearDown(self):
        self.timer.timer.stop()
        self.timer.is_running = False
        for attr in ('sidebar_hide_timer', 'sidebar_hover_timer'):
            t = getattr(self.window, attr, None)
            if t is not None:
                t.stop()
        if hasattr(self.window, 'quote_worker') and self.window.quote_worker.isRunning():
            self.window.quote_worker.quit()
            self.window.quote_worker.wait(1000)
        self.window.close()
        QApplication.processEvents()

    def test_switch_page_does_not_interfere(self):
        """Test that switching pages does not forcefully toggle sidebar"""
        # Ensure sidebar starts at expected width (some platforms may init differently)
        self.window.sidebar.setFixedWidth(85)
        QApplication.processEvents()
        
        # 1. Timer NOT running. Sidebar should be ~85 (allow 60-100 for cross-platform)
        self.window.switch_page(0)
        self.assertGreaterEqual(self.window.sidebar.width(), 60,
                      f"Expected sidebar expanded (~85), got {self.window.sidebar.width()}")

        # 2. Start Timer. Sidebar hides to 0.
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.toggle_timer()
        self.timer.timer.stop()  # Stop real tick to prevent auto-finish loop
        self.window.sidebar.setFixedWidth(0)

        # 3. Hover (Expand to 85)
        event = QEvent(QEvent.Type.Enter)
        self.window.eventFilter(self.window.sidebar, event)
        self.window.sidebar.setFixedWidth(85)

        # 4. Switch to Page 1 while hovering — should stay expanded (allow 60-100)
        self.window.switch_page(1)
        self.assertGreaterEqual(self.window.sidebar.width(), 60,
                      f"Expected sidebar expanded (~85) after switch_page, got {self.window.sidebar.width()}")

        # 5. Leave Hover
        event = QEvent(QEvent.Type.Leave)
        self.window.eventFilter(self.window.sidebar, event)

        self.window.move(10000, 10000)
        self.window.check_and_hide_sidebar()

        self.assertEqual(self.window.anim_min.endValue(), 0)


if __name__ == '__main__':
    unittest.main()
