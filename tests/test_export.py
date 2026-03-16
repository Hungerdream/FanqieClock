
import sys
import os
import unittest
import tempfile
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


class TestExportStats(unittest.TestCase):
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
        # 注入一些统计数据
        self.window.data_manager.data['stats'] = {
            'total_pomodoros': 42,
            'total_minutes': 1050,
            'total_days': 10,
            'history': {
                '2026-03-16': {'count': 5, 'minutes': 125},
                '2026-03-15': {'count': 3, 'minutes': 75},
            }
        }
        self.window.data_manager.data['interruptions'] = [
            {'type': 'internal', 'timestamp': '2026-03-16T10:00:00'},
            {'type': 'external', 'timestamp': '2026-03-16T11:00:00'},
        ]
        QApplication.processEvents()

    def tearDown(self):
        _cleanup(self.window, self.timer)

    def test_export_pdf_creates_file(self):
        """导出 PDF 时应生成真实文件"""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            tmp_path = f.name

        try:
            # Mock 文件选择对话框，直接返回临时文件路径
            with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName',
                       return_value=(tmp_path, 'PDF Files (*.pdf)')), \
                 patch.object(QMessageBox, 'information', return_value=None):
                self.window.export_stats_pdf()
            QApplication.processEvents()

            self.assertTrue(os.path.exists(tmp_path),
                            f"PDF file was not created at {tmp_path}")
            self.assertGreater(os.path.getsize(tmp_path), 0,
                               "PDF file should not be empty")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_export_pdf_cancelled_no_crash(self):
        """用户取消保存对话框时，应静默忽略，不抛异常也不创建文件"""
        with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName',
                   return_value=('', '')):
            try:
                self.window.export_stats_pdf()
            except Exception as e:
                self.fail(f"export_stats_pdf raised exception on cancel: {e}")

    def test_export_pdf_shows_success_dialog(self):
        """导出成功后应弹出信息对话框"""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            tmp_path = f.name

        try:
            with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName',
                       return_value=(tmp_path, 'PDF Files (*.pdf)')), \
                 patch.object(QMessageBox, 'information') as mock_info:
                self.window.export_stats_pdf()
            QApplication.processEvents()

            mock_info.assert_called_once()
            # 验证对话框标题包含"成功"
            call_args = mock_info.call_args[0]
            self.assertIn('成功', call_args[1])
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_export_pdf_uses_stats_data(self):
        """导出时调用的 HTML 应包含统计数字（通过拦截 doc.print 验证 HTML 内容）"""
        html_captured = []

        original_set_html = None

        from PyQt6.QtGui import QTextDocument

        original_set_html = QTextDocument.setHtml

        def capture_set_html(self_doc, html):
            html_captured.append(html)
            original_set_html(self_doc, html)

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            tmp_path = f.name

        try:
            with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName',
                       return_value=(tmp_path, 'PDF Files (*.pdf)')), \
                 patch.object(QMessageBox, 'information', return_value=None), \
                 patch.object(QTextDocument, 'setHtml', capture_set_html):
                self.window.export_stats_pdf()
            QApplication.processEvents()

            self.assertTrue(html_captured, "setHtml was never called")
            html = html_captured[0]
            # 检查关键统计数字出现在 HTML 中
            self.assertIn('42', html, "Total pomodoros should appear in HTML")
            self.assertIn('1050', html, "Total minutes should appear in HTML")
            self.assertIn('2', html, "Interruption count should appear in HTML")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestRefreshStats(unittest.TestCase):
    """测试统计页面数据刷新展示"""

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

    def test_refresh_stats_shows_total_pomodoros(self):
        """refresh_stats 后统计卡片应显示正确的番茄总数"""
        self.window.data_manager.data['stats'] = {
            'total_pomodoros': 99,
            'total_minutes': 2475,
            'total_days': 5,
            'history': {}
        }
        self.window.data_manager.data['interruptions'] = []
        self.window.refresh_stats()
        QApplication.processEvents()

        self.assertEqual(self.window.stat_pomos.val_label.text(), '99')

    def test_refresh_stats_minutes_display_under_60(self):
        """不足 60 分钟时应显示 'X 分钟' 格式"""
        self.window.data_manager.data['stats'] = {
            'total_pomodoros': 1,
            'total_minutes': 25,
            'total_days': 1,
            'history': {}
        }
        self.window.data_manager.data['interruptions'] = []
        self.window.refresh_stats()
        QApplication.processEvents()

        self.assertIn('分钟', self.window.stat_time.val_label.text())

    def test_refresh_stats_minutes_display_over_60(self):
        """超过 60 分钟时应显示 'X.X 小时' 格式"""
        self.window.data_manager.data['stats'] = {
            'total_pomodoros': 10,
            'total_minutes': 300,
            'total_days': 3,
            'history': {}
        }
        self.window.data_manager.data['interruptions'] = []
        self.window.refresh_stats()
        QApplication.processEvents()

        self.assertIn('小时', self.window.stat_time.val_label.text())

    def test_refresh_stats_history_list_shows_last_7_days(self):
        """历史记录列表最多显示最近 7 天"""
        history = {
            f'2026-03-{i:02d}': {'count': i, 'minutes': i * 25}
            for i in range(1, 12)  # 11天
        }
        self.window.data_manager.data['stats'] = {
            'total_pomodoros': 0, 'total_minutes': 0, 'total_days': 11,
            'history': history
        }
        self.window.data_manager.data['interruptions'] = []
        self.window.refresh_stats()
        QApplication.processEvents()

        self.assertEqual(self.window.history_list.count(), 7)

    def test_refresh_stats_interruption_count(self):
        """打断次数应正确统计"""
        self.window.data_manager.data['stats'] = {
            'total_pomodoros': 0, 'total_minutes': 0, 'total_days': 0,
            'history': {}
        }
        self.window.data_manager.data['interruptions'] = [
            {'type': 'internal', 'timestamp': '2026-03-16T10:00:00'},
            {'type': 'external', 'timestamp': '2026-03-16T11:00:00'},
            {'type': 'internal', 'timestamp': '2026-03-16T12:00:00'},
        ]
        self.window.refresh_stats()
        QApplication.processEvents()

        self.assertEqual(self.window.stat_interrupts.val_label.text(), '3')


if __name__ == '__main__':
    unittest.main()
