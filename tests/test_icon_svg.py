
import sys
import os
import unittest
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

# Ensure path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from ui.main_window import MainWindow
from logic.timer import PomodoroTimer
from logic.data_manager import DataManager


class TestNotesIcon(unittest.TestCase):
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
        # Add a dummy note in-memory only
        self.window.data_manager.data["notes"] = [
            {"title": "Test Note", "content": "Content", "date": "2023-01-01"}
        ]

    def tearDown(self):
        self.timer.timer.stop()
        self.timer.is_running = False
        for attr in ('sidebar_hide_timer', 'sidebar_hover_timer'):
            t = getattr(self.window, attr, None)
            if t is not None:
                t.stop()
        if hasattr(self.window, 'quote_worker') and self.window.quote_worker.isRunning():
            self.window.quote_worker.quit()
            self.window.quote_worker.wait(1000)
        self.window.close()
        QApplication.processEvents()

    def test_icon_validity(self):
        with patch.object(DataManager, 'save_data', return_value=None):
            self.window.notes_page.refresh_table()

        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'src', 'resources', 'icon_delete_new.svg'
        )

        self.assertTrue(
            os.path.exists(icon_path),
            f"Icon file not found at: {icon_path}"
        )

        icon = QIcon(icon_path)

        from PyQt6.QtGui import QImageReader
        formats = [fmt.data().decode() for fmt in QImageReader.supportedImageFormats()]
        self.assertIn(
            'svg', formats,
            "SVG image format is not supported by Qt. Icons will be missing."
        )

        self.assertFalse(
            icon.isNull(),
            f"QIcon loaded from '{icon_path}' is null — icon failed to render."
        )


if __name__ == '__main__':
    unittest.main()
