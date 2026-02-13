
import sys
import os
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QEvent

# Ensure path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from ui.main_window import MainWindow
from logic.timer import PomodoroTimer

class TestSidebarFix(unittest.TestCase):
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
        self.window.auto_hide_sidebar_toggle.setChecked(True)
        self.window.sidebar.setFixedWidth(85)
        QApplication.processEvents()

    def tearDown(self):
        self.window.close()

    def test_switch_page_does_not_interfere(self):
        """Test that switching pages does not forcefully toggle sidebar"""
        # 1. Timer NOT running. Sidebar 85.
        self.window.switch_page(0)
        # Should stay 85 (no auto-hide triggered by switch)
        print(f"[Timer Stopped] Width after switch to 0: {self.window.sidebar.width()}")
        self.assertEqual(self.window.sidebar.width(), 85)
        
        # 2. Start Timer. Sidebar hides to 4.
        self.window.toggle_timer()
        self.window.sidebar.setFixedWidth(0) # Simulate animation end
        
        # 3. Hover (Expand to 85)
        event = QEvent(QEvent.Type.Enter)
        self.window.eventFilter(self.window.sidebar, event)
        self.window.sidebar.setFixedWidth(85) # Simulate animation end
        
        # 4. Switch to Page 1 (Tasks) while hovering
        self.window.switch_page(1)
        # Should stay 85 (because we are hovering)
        print(f"[Timer Running, Hovering] Width after switch to 1: {self.window.sidebar.width()}")
        self.assertEqual(self.window.sidebar.width(), 85)
        
        # 5. Leave Hover
        event = QEvent(QEvent.Type.Leave)
        self.window.eventFilter(self.window.sidebar, event)
        
        # Manually trigger the hide check (simulating timer timeout)
        # Move window to ensure cursor (wherever it is) is likely outside the sidebar rect
        self.window.move(10000, 10000)
        self.window.check_and_hide_sidebar()
        
        # Should animate to 0
        print(f"[Leave Hover] Target: {self.window.anim_min.endValue()}")
        self.assertEqual(self.window.anim_min.endValue(), 0)

if __name__ == '__main__':
    unittest.main()
