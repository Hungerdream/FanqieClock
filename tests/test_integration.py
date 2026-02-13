
import sys
import os
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Ensure path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from ui.main_window import MainWindow
from logic.timer import PomodoroTimer
from logic.data_manager import DataManager

class TestIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        # Use a test file for data to avoid messing with real data
        self.test_db = "test_integration_data.json"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
            
        # Patch DataManager in MainWindow to use test file?
        # MainWindow instantiates DataManager internally. 
        # We can mock it or modify the instance after creation if possible, 
        # but MainWindow.__init__ calls load_saved_data() immediately.
        # So better to patch the class or argument if it took one.
        # It doesn't take one. So we have to rely on DataManager using a default or monkeypatching.
        
        # Monkeypatch DataManager.__init__ default filename? 
        # Or just swap the instance after init and reload?
        pass

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_timer_finish_updates_stats(self):
        # Create Timer
        timer = PomodoroTimer()
        timer.work_duration = 1 # 1 second for test
        
        # Create Window
        # We need to force DataManager to use our test file.
        # Since we can't easily inject, we will modify the instance attribute.
        window = MainWindow(timer)
        window.data_manager.filename = self.test_db
        window.data_manager.data = window.data_manager.get_default_data() # Reset data
        
        # Start Timer
        window.toggle_timer()
        self.assertTrue(timer.is_running)
        
        # Fast forward timer to finish
        # We can manually emit finished signal or call the handler logic
        # But let's simulate the flow properly if possible.
        # timer.start() starts a QTimer. We can't wait for it easily in unit test without event loop.
        # So we will invoke the finish handler directly to test the integration logic.
        
        # Simulate work mode
        timer.current_mode = 'work'
        window.work_mins_spin.setValue(25)
        
        # Simulate finish
        window.handle_timer_finished()
        
        # Check if stats updated
        stats = window.data_manager.data["stats"]
        self.assertEqual(stats["total_pomodoros"], 1)
        self.assertEqual(stats["total_minutes"], 25)
        
        # Check if saved (file creation might happen async, so we check the in-memory data first,
        # then check file existence with a delay if we were running the event loop)
        # Since handle_timer_finished calls save_data() which starts a thread...
        # We can't guarantee file is on disk instantly.
        
    def test_kanban_task_focus(self):
        timer = PomodoroTimer()
        window = MainWindow(timer)
        window.data_manager.filename = self.test_db
        
        # Add a task to q1
        from PyQt6.QtWidgets import QLineEdit
        input_field = QLineEdit()
        input_field.setText("Focus Task")
        window.add_kanban_task("q1", input_field)
        
        # Verify task added
        q1_list = window.kanban_cols["q1"]
        self.assertEqual(q1_list.count(), 1)
        item = q1_list.item(0)
        task_data = item.data(Qt.ItemDataRole.UserRole)
        self.assertEqual(task_data["content"], "Focus Task")
        
        # Start focus (simulate clicking the focus button on the widget)
        # The widget signals focus_task -> window.start_focus_on_task
        window.start_focus_on_task(task_data)
        
        # Check window state
        self.assertEqual(window.content_stack.currentIndex(), 0) # Timer page
        self.assertEqual(window.mode_label.text(), "正在专注：Focus Task")
        self.assertTrue(timer.is_running)
        self.assertEqual(window.current_task['id'], task_data['id'])

    def test_settings_update_timer(self):
        timer = PomodoroTimer()
        window = MainWindow(timer)
        window.data_manager.filename = self.test_db
        
        # Change settings
        window.work_mins_spin.setValue(50)
        window.break_mins_spin.setValue(10)
        
        # Save
        window.save_settings()
        
        # Check timer
        self.assertEqual(timer.work_seconds, 50 * 60)
        self.assertEqual(timer.break_seconds, 10 * 60)

if __name__ == '__main__':
    unittest.main()
