
import sys
import os
import unittest
from unittest.mock import patch, MagicMock, call
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QCloseEvent

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


class TestInterruptionRecord(unittest.TestCase):
    """打断记录功能测试"""

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
        self.window.data_manager.data['interruptions'] = []
        QApplication.processEvents()

    def tearDown(self):
        _cleanup(self.window, self.timer)

    def test_internal_interruption_saved_to_data(self):
        """内部打断应追加到 data['interruptions'] 并持久化"""
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.record_interruption('internal')
        QApplication.processEvents()

        interrupts = self.window.data_manager.data.get('interruptions', [])
        self.assertEqual(len(interrupts), 1)
        self.assertEqual(interrupts[0]['type'], 'internal')
        self.assertIn('timestamp', interrupts[0])

    def test_external_interruption_saved_to_data(self):
        """外部打断应追加到 data['interruptions']"""
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.record_interruption('external')
        QApplication.processEvents()

        interrupts = self.window.data_manager.data.get('interruptions', [])
        self.assertEqual(len(interrupts), 1)
        self.assertEqual(interrupts[0]['type'], 'external')

    def test_multiple_interruptions_accumulate(self):
        """多次打断记录应累计，不覆盖"""
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.record_interruption('internal')
            self.window.record_interruption('external')
            self.window.record_interruption('internal')

        interrupts = self.window.data_manager.data.get('interruptions', [])
        self.assertEqual(len(interrupts), 3)

    def test_internal_interruption_updates_mode_label(self):
        """内部打断后 mode_label 应提示已记录"""
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.record_interruption('internal')
        QApplication.processEvents()

        self.assertIn('内部', self.window.mode_label.text())

    def test_external_interruption_updates_mode_label(self):
        """外部打断后 mode_label 应提示已记录"""
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.record_interruption('external')
        QApplication.processEvents()

        self.assertIn('外部', self.window.mode_label.text())

    def test_data_manager_record_interruption_timestamp_format(self):
        """record_interruption 写入的 timestamp 应是有效的 ISO 格式字符串"""
        import datetime
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.data_manager.record_interruption('internal')

        interrupts = self.window.data_manager.data.get('interruptions', [])
        ts = interrupts[-1]['timestamp']
        # 验证可以被 fromisoformat 解析
        try:
            datetime.datetime.fromisoformat(ts)
        except ValueError:
            self.fail(f"Timestamp '{ts}' is not a valid ISO format")


class TestCloseEvent(unittest.TestCase):
    """关闭窗口数据保存测试"""

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
        self.timer.timer.stop()
        self.timer.is_running = False
        for attr in ('sidebar_hide_timer', 'sidebar_hover_timer'):
            t = getattr(self.window, attr, None)
            if t:
                t.stop()
        if hasattr(self.window, 'quote_worker') and self.window.quote_worker.isRunning():
            self.window.quote_worker.quit()
            self.window.quote_worker.wait(1000)
        # 不调用 window.close() 以免重复触发 closeEvent
        QApplication.processEvents()

    def test_programmatic_close_calls_save_sync(self):
        """程序触发关闭（非 spontaneous）时应调用 save_data_sync"""
        with patch.object(DataManager, 'save_data_sync', return_value=None) as mock_sync:
            # 模拟非 spontaneous 的 close event（程序主动关闭）
            event = QCloseEvent()
            # spontaneous() 默认返回 False，符合程序触发场景
            self.window.closeEvent(event)

        mock_sync.assert_called_once()

    def test_programmatic_close_accepts_event(self):
        """程序触发关闭时应 accept 事件（不拦截）"""
        event = QCloseEvent()
        with patch.object(DataManager, 'save_data_sync', return_value=None):
            self.window.closeEvent(event)

        self.assertTrue(event.isAccepted())

    def test_spontaneous_close_ignored(self):
        """用户点 X 触发的 spontaneous 关闭应被忽略（最小化到托盘）"""
        event = QCloseEvent()
        # 用 MagicMock 替换 spontaneous 使其返回 True
        event.spontaneous = MagicMock(return_value=True)

        with patch.object(DataManager, 'save_data_sync', return_value=None) as mock_sync:
            self.window.closeEvent(event)

        # spontaneous 关闭时不应调用 save_data_sync
        mock_sync.assert_not_called()
        # event 应被 ignore
        self.assertFalse(event.isAccepted())


class TestThemeToggle(unittest.TestCase):
    """主题切换测试"""

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

    def test_toggle_to_dark_saves_setting(self):
        """切换到暗色主题后，settings 中 theme 应为 'dark'"""
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.on_theme_toggled(True)  # True = dark

        theme = self.window.data_manager.data.get('settings', {}).get('theme')
        self.assertEqual(theme, 'dark')

    def test_toggle_to_light_saves_setting(self):
        """切换到亮色主题后，settings 中 theme 应为 'light'"""
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.on_theme_toggled(False)  # False = light

        theme = self.window.data_manager.data.get('settings', {}).get('theme')
        self.assertEqual(theme, 'light')

    def test_apply_dark_theme_sets_timer_label_style(self):
        """apply_theme('dark') 后 timer_label 应使用浅色字体"""
        self.window.apply_theme('dark')
        QApplication.processEvents()

        if hasattr(self.window, 'timer_label'):
            style = self.window.timer_label.styleSheet()
            # 暗色主题使用浅色文字
            self.assertIn('E6E6E6', style,
                          f"Dark theme timer_label should use #E6E6E6, got: {style}")

    def test_apply_light_theme_sets_timer_label_style(self):
        """apply_theme('light') 后 timer_label 应使用深色字体"""
        self.window.apply_theme('light')
        QApplication.processEvents()

        if hasattr(self.window, 'timer_label'):
            style = self.window.timer_label.styleSheet()
            # 亮色主题使用深色文字
            self.assertIn('1A1A1A', style,
                          f"Light theme timer_label should use #1A1A1A, got: {style}")

    def test_apply_theme_dark_loads_qss_file(self):
        """apply_theme('dark') 应加载 style_dark.qss（文件存在则调用 setStyleSheet）"""
        app = QApplication.instance()
        with patch.object(app, 'setStyleSheet') as mock_set:
            self.window.apply_theme('dark')
        QApplication.processEvents()

        # 只在 QSS 文件存在时断言
        from ui.main_window import get_resource_path
        dark_qss = get_resource_path(os.path.join('styles', 'style_dark.qss'))
        if os.path.exists(dark_qss):
            mock_set.assert_called()

    def test_theme_toggle_round_trip(self):
        """dark → light → dark 切换后 settings 中值应跟随"""
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.on_theme_toggled(True)
        self.assertEqual(
            self.window.data_manager.data.get('settings', {}).get('theme'), 'dark')

        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.on_theme_toggled(False)
        self.assertEqual(
            self.window.data_manager.data.get('settings', {}).get('theme'), 'light')

        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.on_theme_toggled(True)
        self.assertEqual(
            self.window.data_manager.data.get('settings', {}).get('theme'), 'dark')


if __name__ == '__main__':
    unittest.main()
