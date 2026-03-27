
import sys
import os
import unittest
import uuid
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from ui.main_window import MainWindow
from logic.timer import PomodoroTimer
from logic.data_manager import DataManager


def _cleanup(window, timer):
    timer.timer.stop()
    timer.is_running = False
    for attr in ('sidebar_hide_timer', 'sidebar_hover_timer'):
        t = getattr(window, attr, None)
        if t:
            t.stop()
    if hasattr(window, 'quote_worker') and window.quote_worker.isRunning():
        window.quote_worker.quit()
        window.quote_worker.wait(1000)
    window.close()
    QApplication.processEvents()


class TestTaskPomoCount(unittest.TestCase):
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
        QApplication.processEvents()

    def tearDown(self):
        _cleanup(self.window, self.timer)

    def _add_task(self, key='q1', content='测试任务', pomodoros=0):
        """向指定看板列插入一条任务，返回 task_id"""
        task_id = str(uuid.uuid4())
        task_data = {
            'id': task_id,
            'content': content,
            'pomodoros': pomodoros,
            'created_at': '2026-03-16',
        }
        self.window.kanban_cols[key].add_task_item(task_data)
        # Also update task_location for O(1) lookup used by update_task_pomo_count
        row_index = self.window.kanban_cols[key].count() - 1
        self.window.task_location[task_id] = (key, row_index)
        QApplication.processEvents()
        return task_id

    # ------------------------------------------------------------------
    # 1. 基本计数 +1
    # ------------------------------------------------------------------
    def test_pomo_count_increments(self):
        """update_task_pomo_count 应将指定任务的番茄数 +1"""
        task_id = self._add_task(key='q1', content='任务A', pomodoros=0)

        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.update_task_pomo_count(task_id)

        # 从 kanban_cols 取回数据验证
        col = self.window.kanban_cols['q1']
        item = col.item(col.count() - 1)
        data = item.data(Qt.ItemDataRole.UserRole)
        self.assertEqual(data['pomodoros'], 1,
                         f"Expected pomodoros=1, got {data['pomodoros']}")

    def test_pomo_count_increments_multiple_times(self):
        """多次调用后番茄数应累加"""
        task_id = self._add_task(key='q2', content='任务B', pomodoros=2)

        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.update_task_pomo_count(task_id)
            self.window.update_task_pomo_count(task_id)

        col = self.window.kanban_cols['q2']
        item = col.item(col.count() - 1)
        data = item.data(Qt.ItemDataRole.UserRole)
        self.assertEqual(data['pomodoros'], 4)

    def test_pomo_count_nonexistent_task_no_crash(self):
        """对不存在的 task_id 调用应静默忽略，不抛异常"""
        try:
            with patch.object(DataManager, 'save_data', return_value=None):
                self.window.update_task_pomo_count('nonexistent-id-xxx')
        except Exception as e:
            self.fail(f"update_task_pomo_count raised unexpected exception: {e}")

    def test_pomo_count_triggers_save(self):
        """update_task_pomo_count 找到任务后应调用 save_kanban_state"""
        task_id = self._add_task(key='q1', content='任务C')

        with patch.object(self.window, 'save_kanban_state') as mock_save, \
             patch.object(DataManager, 'save_data', return_value=None):
            self.window.update_task_pomo_count(task_id)

        mock_save.assert_called_once()

    def test_pomo_count_widget_label_updated(self):
        """计数后，列表项对应的 widget 标签应同步更新"""
        task_id = self._add_task(key='q3', content='任务D', pomodoros=0)

        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.update_task_pomo_count(task_id)
        QApplication.processEvents()

        col = self.window.kanban_cols['q3']
        item = col.item(col.count() - 1)
        widget = col.itemWidget(item)
        if widget is not None:
            self.assertIn('1', widget.pomo_label.text(),
                          f"pomo_label should show 1, got: {widget.pomo_label.text()}")

    def test_pomo_count_searches_all_columns(self):
        """任务在不同看板列中，都能被正确找到并更新"""
        for key in ('q1', 'q2', 'q3', 'q4'):
            task_id = self._add_task(key=key, content=f'任务_{key}')
            with patch.object(DataManager, 'save_data', return_value=None):
                self.window.update_task_pomo_count(task_id)

            col = self.window.kanban_cols[key]
            item = col.item(col.count() - 1)
            data = item.data(Qt.ItemDataRole.UserRole)
            self.assertEqual(data['pomodoros'], 1,
                             f"Column {key}: expected pomodoros=1, got {data['pomodoros']}")

    # ------------------------------------------------------------------
    # 2. 专注完成后自动触发（通过 handle_timer_finished 集成路径）
    # ------------------------------------------------------------------
    def test_handle_timer_finished_increments_current_task_pomo(self):
        """handle_timer_finished 时若有 current_task，应自动 +1 该任务番茄数"""
        task_id = self._add_task(key='q1', content='当前专注任务', pomodoros=0)
        self.window.current_task = {'id': task_id, 'content': '当前专注任务'}

        with patch.object(DataManager, 'save_data', return_value=None), \
             patch.object(DataManager, 'save_data_sync', return_value=None):
            self.window.handle_timer_finished()
        QApplication.processEvents()

        col = self.window.kanban_cols['q1']
        item = col.item(col.count() - 1)
        data = item.data(Qt.ItemDataRole.UserRole)
        self.assertEqual(data['pomodoros'], 1,
                         "handle_timer_finished should increment current task pomodoros")

    def test_handle_timer_finished_no_current_task_no_crash(self):
        """handle_timer_finished 时无 current_task 应不崩溃"""
        self.window.current_task = None
        try:
            with patch.object(DataManager, 'save_data', return_value=None), \
                 patch.object(DataManager, 'save_data_sync', return_value=None):
                self.window.handle_timer_finished()
        except Exception as e:
            self.fail(f"handle_timer_finished raised: {e}")


if __name__ == '__main__':
    unittest.main()
