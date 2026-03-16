
import sys
import os
import unittest
from PyQt6.QtWidgets import QApplication, QPushButton, QWidget, QTableWidget
from PyQt6.QtGui import QIcon

# Ensure path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from ui.main_window import MainWindow
from logic.timer import PomodoroTimer

class TestNotesIcon(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.timer = PomodoroTimer()
        self.window = MainWindow(self.timer)
        # Add a dummy note
        self.window.data_manager.update_notes([
            {"title": "Test Note", "content": "Content", "date": "2023-01-01"}
        ])

    def tearDown(self):
        self.window.close()

    def test_icon_validity(self):
        self.window.refresh_notes_table()

        # Check specific icon file used in the app
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'resources', 'icon_delete_new.svg')

        # Assert the icon file exists on disk
        self.assertTrue(
            os.path.exists(icon_path),
            f"Icon file not found at: {icon_path}"
        )

        icon = QIcon(icon_path)

        # Check if SVG plugin is available
        from PyQt6.QtGui import QImageReader
        formats = [fmt.data().decode() for fmt in QImageReader.supportedImageFormats()]
        self.assertIn(
            'svg', formats,
            "SVG image format is not supported by Qt. Icons will be missing. "
            "Ensure PyQt6 or Qt SVG plugin is installed."
        )

        # Assert the icon loaded successfully (not null)
        self.assertFalse(
            icon.isNull(),
            f"QIcon loaded from '{icon_path}' is null — icon failed to render."
        )

if __name__ == '__main__':
    unittest.main()
