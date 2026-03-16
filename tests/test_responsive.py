
import sys
import os
import unittest
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSize

# Ensure path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from ui.main_window import MainWindow
from logic.timer import PomodoroTimer
from logic.data_manager import DataManager


class TestResponsiveSidebar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.timer = PomodoroTimer()
        # Mock disk IO so no background threads write data.json
        with patch.object(DataManager, 'save_data', return_value=None), \
             patch.object(DataManager, 'save_data_sync', return_value=None):
            self.window = MainWindow(self.timer)
        self.window.show()
        # Reset manual state in-memory only (no disk write)
        self.window.data_manager.data.setdefault("settings", {})["sidebar_manual_state"] = None
        # Reset animation state
        if hasattr(self.window, '_last_compact_mode'):
            del self.window._last_compact_mode

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

    def test_responsive_collapse(self):
        """Test that sidebar collapses when window width < 1200px"""
        from unittest.mock import patch as mpatch
        from PyQt6.QtGui import QResizeEvent

        # 先展开侧边栏，确保初始宽度不为 0
        self.window.sidebar.setMinimumWidth(85)
        self.window.sidebar.setMaximumWidth(85)
        QApplication.processEvents()

        # 用 mock 捕获 animate_sidebar 的调用参数，避免依赖异步动画状态
        with mpatch.object(self.window, 'animate_sidebar', wraps=self.window.animate_sidebar) as mock_anim:
            event = QResizeEvent(QSize(1000, 800), QSize(1300, 800))
            self.window.resizeEvent(event)
            QApplication.processEvents()

        mock_anim.assert_called()
        called_width = mock_anim.call_args[0][0]
        self.assertEqual(called_width, 0, f"Expected animate_sidebar(0) for collapse, got animate_sidebar({called_width})")

    def test_responsive_expand(self):
        """Test that sidebar expands when window width >= 1200px"""
        from unittest.mock import patch as mpatch
        from PyQt6.QtGui import QResizeEvent

        # 先折叠侧边栏，确保初始宽度为 0
        self.window._last_compact_mode = True
        self.window.sidebar.setMinimumWidth(0)
        self.window.sidebar.setMaximumWidth(0)
        QApplication.processEvents()

        with mpatch.object(self.window, 'animate_sidebar', wraps=self.window.animate_sidebar) as mock_anim:
            event = QResizeEvent(QSize(1250, 800), QSize(1000, 800))
            self.window.resizeEvent(event)
            QApplication.processEvents()

        mock_anim.assert_called()
        called_width = mock_anim.call_args[0][0]
        self.assertEqual(called_width, 85, f"Expected animate_sidebar(85) for expand, got animate_sidebar({called_width})")

    def test_manual_toggle_persistence(self):
        """Test that manual toggle saves state"""
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.toggle_sidebar()

        settings = self.window.data_manager.data.get("settings", {})
        self.assertIn("sidebar_manual_state", settings)
        self.assertIsNotNone(settings["sidebar_manual_state"])


if __name__ == '__main__':
    unittest.main()
