
import sys
import unittest
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt6.QtCore import Qt, QTimer, QEvent

class MockMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            if self.windowState() & Qt.WindowState.WindowMinimized:
                self.hide()
        super().changeEvent(event)

class TestWindowRestoreFixed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.window = MockMainWindow()
        self.window.show()
        QApplication.processEvents()

    def tearDown(self):
        self.window.close()

    def test_restore_with_fix(self):
        # 1. Minimize window
        self.window.showMinimized()
        QApplication.processEvents()
        
        # 2. Simulate "Return to Home" with FIX
        self.window.setWindowState(Qt.WindowState.WindowNoState)
        self.window.show()
        self.window.activateWindow()
        QApplication.processEvents()
        
        # 3. Check state
        state = self.window.windowState()
        is_minimized = bool(state & Qt.WindowState.WindowMinimized)
        
        print(f"\n[Fixed] Window State: {state}")
        print(f"[Fixed] Is Minimized: {is_minimized}")
        print(f"[Fixed] Is Visible: {self.window.isVisible()}")
        
        self.assertFalse(is_minimized, "Window should NOT be minimized after fix")
        self.assertTrue(self.window.isVisible(), "Window should be visible")

if __name__ == '__main__':
    unittest.main()
