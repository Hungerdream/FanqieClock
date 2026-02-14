
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
        
        # container = self.window.notes_table.cellWidget(0, 2)
        # layout = container.layout()
        # btn = layout.itemAt(0).widget()
        # icon = btn.icon()

        # Check specific icon file used in the app
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'resources', 'icon_delete_new.svg')
        icon = QIcon(icon_path)
        
        if not os.path.exists(icon_path):
            print(f"ERROR: Icon file not found at {icon_path}")
        else:
            print(f"Icon file exists at {icon_path}")
        print(f"Icon isNull: {icon.isNull()}")
        
        # Check if SVG plugin is available
        from PyQt6.QtGui import QImageReader
        formats = [fmt.data().decode() for fmt in QImageReader.supportedImageFormats()]
        print(f"Supported formats: {formats}")
        
        if 'svg' not in formats:
            print("WARNING: SVG format not supported! This is why the icon is missing.")

if __name__ == '__main__':
    unittest.main()
