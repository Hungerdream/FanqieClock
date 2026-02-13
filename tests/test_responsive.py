
import sys
import os
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSize

# Ensure path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from ui.main_window import MainWindow
from logic.timer import PomodoroTimer

class TestResponsiveSidebar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.timer = PomodoroTimer()
        self.window = MainWindow(self.timer)
        self.window.show()
        # Reset manual state
        self.window.data_manager.update_settings({"sidebar_manual_state": None})
        # Reset animation state
        if hasattr(self.window, '_last_compact_mode'):
            del self.window._last_compact_mode

    def tearDown(self):
        self.window.close()

    def test_responsive_collapse(self):
        """Test that sidebar collapses when window width < 1200px"""
        # Resize to large
        self.window.resize(1300, 800)
        QApplication.processEvents()
        
        # Verify expanded
        # Wait for animation or check target if animation started
        # Since we just resized, resizeEvent triggered.
        # Initial state might be default (85).
        
        # Resize to small
        from PyQt6.QtGui import QResizeEvent
        event = QResizeEvent(QSize(1000, 800), QSize(1300, 800))
        self.window.resizeEvent(event)
        
        # Check if animation target is 4
        self.assertEqual(self.window.anim_min.endValue(), 0)
        
    def test_responsive_expand(self):
        """Test that sidebar expands when window width >= 1200px"""
        # Simulate small state first
        self.window._last_compact_mode = True
        self.window.sidebar.setFixedWidth(0)
        
        # Resize to large
        from PyQt6.QtGui import QResizeEvent
        event = QResizeEvent(QSize(1250, 800), QSize(1000, 800))
        self.window.resizeEvent(event)
        
        # Check if animation target is 85
        self.assertEqual(self.window.anim_min.endValue(), 85)

    def test_manual_toggle_persistence(self):
        """Test that manual toggle saves state"""
        # Toggle sidebar manually
        self.window.toggle_sidebar()
        
        # Check settings
        settings = self.window.data_manager.data.get("settings", {})
        self.assertIn("sidebar_manual_state", settings)
        self.assertIsNotNone(settings["sidebar_manual_state"])

if __name__ == '__main__':
    unittest.main()
