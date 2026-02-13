
import sys
import os
import unittest
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer

# Ensure path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from ui.main_window import MainWindow
from logic.timer import PomodoroTimer

class TestSidebarAutoHide(unittest.TestCase):
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
        # Ensure setting is enabled
        self.window.auto_hide_sidebar_toggle.setChecked(True)
        # Ensure sidebar starts expanded
        self.window.sidebar.setFixedWidth(85)

    def tearDown(self):
        self.window.close()

    def test_sidebar_collapse_on_start(self):
        # Initial state
        self.assertEqual(self.window.sidebar.width(), 85)
        
        # Start Timer
        self.window.toggle_timer()
        
        # Check if animation started
        # We can check if animation group is running
        self.assertTrue(hasattr(self.window, 'anim_group'))
        from PyQt6.QtCore import QAbstractAnimation
        self.assertEqual(self.window.anim_group.state(), QAbstractAnimation.State.Running)
        
        # Check target values
        self.assertEqual(self.window.anim_min.endValue(), 0)
        self.assertEqual(self.window.anim_max.endValue(), 0)
        
        # Simulate wait (or just trust the animation started)
        # We can't easily wait 300ms in unit test without blocking loop, 
        # but verifying the target is enough.

    def test_sidebar_expand_on_stop(self):
        # Start first to collapse
        self.window.toggle_timer()
        
        # Stop Timer
        self.window.stop_timer()
        
        # Check target values
        from PyQt6.QtCore import QAbstractAnimation
        if self.window.anim_group.state() == QAbstractAnimation.State.Running:
            self.assertEqual(self.window.anim_min.endValue(), 85)
        else:
            # If not running, we should be at 85
            self.assertEqual(self.window.sidebar.width(), 85)

    def test_sidebar_hover_behavior(self):
        # Start timer -> Collapsed
        self.window.toggle_timer()
        # Force width to 0 for testing logic (skip animation wait)
        self.window.sidebar.setFixedWidth(0)
        
        # Simulate Enter Event
        from PyQt6.QtCore import QEvent, QPointF
        enter_event = QEvent(QEvent.Type.Enter)
        self.window.eventFilter(self.window.sidebar, enter_event)
        
        # Should trigger expansion
        self.assertEqual(self.window.anim_min.endValue(), 85)
        
        # Force width to 85
        self.window.sidebar.setFixedWidth(85)
        
        # Simulate Leave Event
        leave_event = QEvent(QEvent.Type.Leave)
        self.window.eventFilter(self.window.sidebar, leave_event)
        
        # Should trigger timer, not immediate collapse
        self.assertTrue(self.window.sidebar_hide_timer.isActive())
        
        # Force timeout check (Simulate mouse outside)
        self.window.move(100, 100) # Move window so (0,0) cursor is outside
        self.window.check_and_hide_sidebar()
        
        # Should trigger collapse
        self.assertEqual(self.window.anim_min.endValue(), 0)

if __name__ == '__main__':
    unittest.main()
