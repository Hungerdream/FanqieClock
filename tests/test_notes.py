
import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QApplication, QMessageBox
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


class TestNotes(unittest.TestCase):
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
        # 确保初始笔记为空
        self.window.data_manager.data['notes'] = []
        self.window.refresh_notes_table()
        QApplication.processEvents()

    def tearDown(self):
        _cleanup(self.window, self.timer)

    # ------------------------------------------------------------------
    # 1. 新建笔记
    # ------------------------------------------------------------------
    def test_add_note_updates_data(self):
        """直接调用 update_notes 写入一条笔记，data 中应有记录"""
        note = {'title': '测试标题', 'content': '测试内容', 'date': '2026-03-16'}
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.data_manager.update_notes([note])

        notes = self.window.data_manager.data.get('notes', [])
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]['title'], '测试标题')
        self.assertEqual(notes[0]['content'], '测试内容')

    def test_add_note_refreshes_table(self):
        """新增笔记后 refresh_notes_table 应在表格中显示新行"""
        note = {'title': '标题A', 'content': '内容A', 'date': '2026-03-16'}
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.data_manager.update_notes([note])
        self.window.refresh_notes_table()
        QApplication.processEvents()

        self.assertEqual(self.window.notes_table.rowCount(), 1)
        self.assertEqual(self.window.notes_table.item(0, 0).text(), '标题A')

    def test_add_multiple_notes(self):
        """添加多条笔记后表格行数应匹配"""
        notes = [
            {'title': f'笔记{i}', 'content': f'内容{i}', 'date': '2026-03-16'}
            for i in range(3)
        ]
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.data_manager.update_notes(notes)
        self.window.refresh_notes_table()
        QApplication.processEvents()

        self.assertEqual(self.window.notes_table.rowCount(), 3)

    # ------------------------------------------------------------------
    # 2. 编辑笔记
    # ------------------------------------------------------------------
    def test_edit_note_updates_data(self):
        """修改第 0 条笔记的内容，data 中对应条目应更新"""
        notes = [{'title': '原标题', 'content': '原内容', 'date': '2026-03-16'}]
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.data_manager.update_notes(notes)

        # 直接修改并回写（模拟 show_note_dialog 的 save() 逻辑）
        updated = self.window.data_manager.data['notes']
        updated[0] = {'title': '新标题', 'content': '新内容', 'date': '2026-03-16'}
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.data_manager.update_notes(updated)

        result = self.window.data_manager.data['notes'][0]
        self.assertEqual(result['title'], '新标题')
        self.assertEqual(result['content'], '新内容')

    def test_edit_note_table_row_index_stored(self):
        """refresh_notes_table 时每行的 UserRole 数据应存笔记 UUID"""
        notes = [
            {'id': 'uuid-001', 'title': '笔记0', 'content': '', 'date': '2026-03-16'},
            {'id': 'uuid-002', 'title': '笔记1', 'content': '', 'date': '2026-03-16'},
        ]
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.data_manager.update_notes(notes)
        self.window.refresh_notes_table()
        QApplication.processEvents()

        for row in range(2):
            title_item = self.window.notes_table.item(row, 0)
            # 现在存储的是 UUID 而不是索引
            self.assertEqual(title_item.data(Qt.ItemDataRole.UserRole), notes[row]['id'])

    # ------------------------------------------------------------------
    # 3. 删除笔记
    # ------------------------------------------------------------------
    def test_delete_note_removes_from_data(self):
        """确认删除后，data 中该笔记应消失"""
        notes = [
            {'id': 'keep-uuid', 'title': '保留', 'content': '', 'date': '2026-03-16'},
            {'id': 'delete-uuid', 'title': '删除我', 'content': '', 'date': '2026-03-16'},
        ]
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.data_manager.update_notes(notes)

        with patch.object(DataManager, 'save_data', return_value=None), \
             patch.object(QMessageBox, 'question',
                          return_value=QMessageBox.StandardButton.Yes):
            self.window.delete_note('delete-uuid')

        remaining = self.window.data_manager.data.get('notes', [])
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]['title'], '保留')

    def test_delete_note_cancelled(self):
        """取消删除后，data 中笔记数量不变"""
        notes = [{'id': 'keep-uuid', 'title': '不删', 'content': '', 'date': '2026-03-16'}]
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.data_manager.update_notes(notes)

        with patch.object(DataManager, 'save_data', return_value=None), \
             patch.object(QMessageBox, 'question',
                          return_value=QMessageBox.StandardButton.No):
            self.window.delete_note('keep-uuid')

        remaining = self.window.data_manager.data.get('notes', [])
        self.assertEqual(len(remaining), 1)

    def test_delete_note_out_of_range(self):
        """不存在的 UUID 删除不应崩溃"""
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.data_manager.update_notes([])

        with patch.object(QMessageBox, 'question',
                          return_value=QMessageBox.StandardButton.Yes):
            try:
                self.window.delete_note('non-existent-uuid')
            except Exception as e:
                self.fail(f"delete_note(non-existent) raised {e}")

    # ------------------------------------------------------------------
    # 4. 搜索/过滤
    # ------------------------------------------------------------------
    def test_filter_notes_by_title(self):
        """按标题关键字过滤，只有匹配的行显示"""
        notes = [
            {'title': 'Python 学习', 'content': '内容A', 'date': '2026-03-16'},
            {'title': 'PyQt6 笔记', 'content': '内容B', 'date': '2026-03-16'},
            {'title': '购物清单',   'content': '内容C', 'date': '2026-03-16'},
        ]
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.data_manager.update_notes(notes)
        self.window.refresh_notes_table(filter_text='python')
        QApplication.processEvents()

        self.assertEqual(self.window.notes_table.rowCount(), 1)
        self.assertEqual(self.window.notes_table.item(0, 0).text(), 'Python 学习')

    def test_filter_notes_by_content(self):
        """按正文关键字过滤，命中正文的行也应显示"""
        notes = [
            {'title': '标题A', 'content': '番茄工作法相关', 'date': '2026-03-16'},
            {'title': '标题B', 'content': '购物清单：苹果、香蕉', 'date': '2026-03-16'},
        ]
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.data_manager.update_notes(notes)
        self.window.refresh_notes_table(filter_text='番茄')
        QApplication.processEvents()

        self.assertEqual(self.window.notes_table.rowCount(), 1)

    def test_filter_notes_empty_keyword_shows_all(self):
        """过滤词为空时显示所有笔记"""
        notes = [
            {'title': f'笔记{i}', 'content': '', 'date': '2026-03-16'}
            for i in range(4)
        ]
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.data_manager.update_notes(notes)
        self.window.refresh_notes_table(filter_text='')
        QApplication.processEvents()

        self.assertEqual(self.window.notes_table.rowCount(), 4)

    def test_filter_notes_no_match(self):
        """过滤词无匹配时表格应为空"""
        notes = [{'title': '测试', 'content': '内容', 'date': '2026-03-16'}]
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.data_manager.update_notes(notes)
        self.window.refresh_notes_table(filter_text='zzz_no_match')
        QApplication.processEvents()

        self.assertEqual(self.window.notes_table.rowCount(), 0)


if __name__ == '__main__':
    unittest.main()
