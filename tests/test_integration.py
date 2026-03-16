
import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Ensure path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from ui.main_window import MainWindow
from logic.timer import PomodoroTimer
from logic.data_manager import DataManager


def _cleanup_window(window, timer=None):
    """Stop all timers and close window cleanly."""
    # Stop pomodoro timer first to prevent auto-restart
    if timer is not None:
        timer.timer.stop()
        timer.is_running = False
    # Stop Qt timers owned by the window
    for attr in ('sidebar_hide_timer', 'sidebar_poll_timer'):
        t = getattr(window, attr, None)
        if t is not None:
            t.stop()
    window.close()
    QApplication.processEvents()


class TestIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self._cleanup_pairs = []  # list of (window, timer)

    def tearDown(self):
        for window, timer in self._cleanup_pairs:
            _cleanup_window(window, timer)
        self._cleanup_pairs.clear()
        QApplication.processEvents()

    # ------------------------------------------------------------------
    # Helper: create window with disk IO mocked out
    # ------------------------------------------------------------------
    def _make_window(self, timer=None):
        if timer is None:
            timer = PomodoroTimer()
        # Patch DataManager.save_data and save_data_sync so nothing touches disk
        with patch.object(DataManager, 'save_data', return_value=None), \
             patch.object(DataManager, 'save_data_sync', return_value=None):
            window = MainWindow(timer)
        self._cleanup_pairs.append((window, timer))
        return window, timer

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------
    def test_timer_finish_updates_stats(self):
        """Finishing a work session increments stats correctly."""
        timer = PomodoroTimer()
        timer.work_seconds = 1

        with patch.object(DataManager, 'save_data', return_value=None), \
             patch.object(DataManager, 'save_data_sync', return_value=None):
            window = MainWindow(timer)
        self._cleanup_pairs.append((window, timer))

        window.data_manager.data = window.data_manager.get_default_data()

        # Start then immediately pause to avoid real tick
        with patch.object(DataManager, 'save_data', return_value=None):
            window.toggle_timer()
        self.assertTrue(timer.is_running)

        # Pause the underlying QTimer so it won't auto-finish during the test
        timer.timer.stop()

        # Simulate work mode finished
        timer.current_mode = 'work'
        window.work_mins_spin.setValue(25)

        with patch.object(DataManager, 'save_data', return_value=None), \
             patch.object(DataManager, 'save_data_sync', return_value=None):
            window.handle_timer_finished()

        stats = window.data_manager.data["stats"]
        self.assertEqual(stats["total_pomodoros"], 1)
        self.assertEqual(stats["total_minutes"], 25)

    def test_kanban_task_focus(self):
        """start_focus_on_task switches to timer page and starts timer."""
        window, timer = self._make_window()

        with patch.object(DataManager, 'save_data', return_value=None):
            from PyQt6.QtWidgets import QLineEdit
            input_field = QLineEdit()
            input_field.setText("Focus Task")
            window.add_kanban_task("q1", input_field)

        q1_list = window.kanban_cols["q1"]
        self.assertEqual(q1_list.count(), 1)
        item = q1_list.item(0)
        task_data = item.data(Qt.ItemDataRole.UserRole)
        self.assertEqual(task_data["content"], "Focus Task")

        with patch.object(DataManager, 'save_data', return_value=None):
            window.start_focus_on_task(task_data)

        # Stop the QTimer immediately so it won't fire and loop
        timer.timer.stop()

        self.assertEqual(window.content_stack.currentIndex(), 0)
        self.assertEqual(window.mode_label.text(), "正在专注：Focus Task")
        self.assertTrue(timer.is_running)
        self.assertEqual(window.current_task['id'], task_data['id'])

    def test_settings_update_timer(self):
        """Saving settings propagates new durations to the timer."""
        window, timer = self._make_window()

        window.work_mins_spin.setValue(50)
        window.break_mins_spin.setValue(10)

        with patch.object(DataManager, 'save_data', return_value=None), \
             patch.object(DataManager, 'save_data_sync', return_value=None):
            window.save_settings()

        self.assertEqual(timer.work_seconds, 50 * 60)
        self.assertEqual(timer.break_seconds, 10 * 60)


if __name__ == '__main__':
    unittest.main()
