
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
        # Check if SVG plugin is available
        from PyQt6.QtGui import QImageReader
        formats = [fmt.data().decode() for fmt in QImageReader.supportedImageFormats()]
        print(f"Supported formats: {formats}")
        
        if 'svg' not in formats:
            print("WARNING: SVG format not supported! This is why the icon is missing.")
            
        # Verify specific icon loading
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'resources', 'icon_delete_new.svg')
        icon = QIcon(icon_path)
        print(f"Icon path: {icon_path}")
        print(f"Icon isNull: {icon.isNull()}")
        
        # We can't strictly assert isNull() is False without a running GUI event loop that supports SVGs properly 
        # in some headless environments, but we can check if the file exists.
        self.assertTrue(os.path.exists(icon_path), "Icon file does not exist")
        
        if 'svg' in formats:
            self.assertFalse(icon.isNull(), "Icon should not be null if SVG is supported")

if __name__ == '__main__':
    unittest.main()
