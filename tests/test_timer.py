import unittest
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from logic.timer import PomodoroTimer
from PyQt6.QtWidgets import QApplication

# App needed for QTimer signals
app = QApplication(sys.argv)

class TestPomodoroTimer(unittest.TestCase):
    def setUp(self):
        # Use very short durations for testing
        self.timer = PomodoroTimer(work_minutes=0.1, break_minutes=0.1, long_break_minutes=0.1)

    def test_initial_state(self):
        self.assertEqual(self.timer.current_mode, 'work')
        self.assertFalse(self.timer.is_running)
        self.assertEqual(self.timer.pomodoros_completed, 0)

    def test_start_pause(self):
        self.timer.start()
        self.assertTrue(self.timer.is_running)
        self.assertIsNotNone(self.timer.end_time)
        
        self.timer.pause()
        self.assertFalse(self.timer.is_running)

    def test_reset(self):
        self.timer.start()
        self.timer.reset()
        self.assertFalse(self.timer.is_running)
        self.assertEqual(self.timer.remaining_seconds, self.timer.work_seconds)

    def test_mode_switching_cycle(self):
        # Initial: Work
        self.assertEqual(self.timer.current_mode, 'work')
        
        # Finish Work -> Break
        self.timer.switch_mode()
        self.assertEqual(self.timer.current_mode, 'break')
        # Work count increments only when finishing work? 
        # Logic says: if current_mode == 'work': pomodoros_completed += 1
        # So yes, switching FROM work increments it.
        self.assertEqual(self.timer.pomodoros_completed, 1)
        
        # Finish Break -> Work
        self.timer.switch_mode()
        self.assertEqual(self.timer.current_mode, 'work')
        
    def test_long_break_trigger(self):
        # We need to complete 4 pomodoros to trigger long break
        # Currently at 0
        
        # 1. Work -> Break
        self.timer.switch_mode()
        self.assertEqual(self.timer.pomodoros_completed, 1)
        self.assertEqual(self.timer.current_mode, 'break')
        
        # Break -> Work
        self.timer.switch_mode()
        
        # 2. Work -> Break
        self.timer.switch_mode()
        self.assertEqual(self.timer.pomodoros_completed, 2)
        
        # Break -> Work
        self.timer.switch_mode()
        
        # 3. Work -> Break
        self.timer.switch_mode()
        self.assertEqual(self.timer.pomodoros_completed, 3)
        
        # Break -> Work
        self.timer.switch_mode()
        
        # 4. Work -> Long Break
        self.timer.switch_mode()
        self.assertEqual(self.timer.pomodoros_completed, 4)
        self.assertEqual(self.timer.current_mode, 'long_break')
        
        # Long Break -> Work
        self.timer.switch_mode()
        self.assertEqual(self.timer.current_mode, 'work')

if __name__ == '__main__':
    unittest.main()