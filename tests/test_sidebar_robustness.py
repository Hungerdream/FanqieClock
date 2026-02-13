
import sys
import os
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QEvent, QTimer

# Ensure path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from ui.main_window import MainWindow
from logic.timer import PomodoroTimer

class TestSidebarRobustness(unittest.TestCase):
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
        # Enable auto-hide and ensure timer is running for event filter logic
        self.window.auto_hide_sidebar_toggle.setChecked(True)
        self.timer.start() 
        self.window.sidebar.setFixedWidth(0) # Start collapsed
        QApplication.processEvents()

    def tearDown(self):
        self.window.close()

    def test_enter_event_expands_immediately(self):
        """Test Enter event triggers expansion immediately"""
        # Simulate Enter
        event = QEvent(QEvent.Type.Enter)
        self.window.eventFilter(self.window.sidebar, event)
        
        # Should be animating to 85
        self.assertTrue(hasattr(self.window, 'anim_group'))
        self.assertEqual(self.window.anim_min.endValue(), 85)
        print("\n[Robustness] Enter event triggered expansion to 85")

    def test_leave_event_delays_hide(self):
        """Test Leave event starts timer instead of hiding immediately"""
        # Expand first
        self.window.sidebar.setFixedWidth(85)
        
        # Simulate Leave
        event = QEvent(QEvent.Type.Leave)
        self.window.eventFilter(self.window.sidebar, event)
        
        # Verify timer started
        self.assertTrue(self.window.sidebar_hide_timer.isActive())
        # Verify NO animation started yet (width should still be 85 target or not animating to 4)
        # Note: If animation was running, it might still be running, but we didn't start a new one to 4.
        # Let's check if anim_min end value is 4. If we haven't called animate_sidebar(4), it shouldn't be.
        # Or simply check that we are not animating to 4 immediately.
        
        # If we manually check the timer callback logic:
        # We can't easily wait 300ms in unit test.
        # But we can verify the timer is active.
        print("[Robustness] Leave event started hide timer")
        
        # Simulate Timer Timeout
        # We need to mock cursor position to be outside sidebar
        # Since we can't move physical mouse, we can mock mapFromGlobal or rect().contains?
        # Or we can just invoke the method and see what happens given current mouse pos (likely (0,0)).
        # Sidebar is at some position.
        
        # Let's verify logic by calling check_and_hide_sidebar manually
        # But first ensure mouse is "outside"
        # We can move window to 100,100 and assume mouse at 0,0 is outside.
        self.window.move(100, 100)
        self.window.check_and_hide_sidebar()
        
        # Now it should be animating to 4
        self.assertEqual(self.window.anim_min.endValue(), 0)
        print("[Robustness] Timer timeout triggered collapse (cursor outside)")

    def test_fast_reentry_cancels_hide(self):
        """Test Leave then fast Enter cancels the hide timer"""
        self.window.sidebar.setFixedWidth(80) # Set to non-target width
        # Force initialization of anim_min by calling animate once
        self.window.animate_sidebar(85)
        
        # Now anim_min exists. Ensure sidebar is at target for the test logic.
        self.window.sidebar.setFixedWidth(85)
        
        # Leave
        event = QEvent(QEvent.Type.Leave)
        self.window.eventFilter(self.window.sidebar, event)
        self.assertTrue(self.window.sidebar_hide_timer.isActive())
        
        # Enter (Fast re-entry)
        event = QEvent(QEvent.Type.Enter)
        self.window.eventFilter(self.window.sidebar, event)
        
        # Timer should be stopped
        self.assertFalse(self.window.sidebar_hide_timer.isActive())
        # Should ensure expanded
        self.assertEqual(self.window.anim_min.endValue(), 85)
        print("[Robustness] Fast re-entry cancelled hide timer")

if __name__ == '__main__':
    unittest.main()
