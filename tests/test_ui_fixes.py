
import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
import unittest
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QLocale
from ui.main_window import MainWindow
from logic.timer import PomodoroTimer

# Mock Timer to avoid dependency issues
class MockTimer(PomodoroTimer):
    def __init__(self):
        super().__init__()
        self.is_running = False
    
    def start(self):
        self.is_running = True
        self.tick.emit(1500)
        
    def pause(self):
        self.is_running = False
        
    def reset(self):
        self.is_running = False

class TestUIBugs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create App
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.timer = MockTimer()
        self.window = MainWindow(self.timer)
        self.window.show()

    def tearDown(self):
        self.window.close()

    def test_start_button_connections(self):
        """
        Test 1: Start Button Unresponsive
        Check if the button has duplicate connections.
        Note: PyQt doesn't easily expose the number of connections on a signal.
        We will simulate a click and check how many times toggle_timer is called.
        """
        # We need to mock toggle_timer to count calls
        original_toggle = self.window.toggle_timer
        self.call_count = 0
        
        def mock_toggle():
            self.call_count += 1
            original_toggle()
            
        # Replace the method - BUT the connections are already made to the original method.
        # This approach won't work to count *existing* connections easily.
        # However, we can deduce it from behavior:
        # If connected twice, one click -> 2 calls.
        #   Call 1: is_running False -> Start
        #   Call 2: is_running True -> Pause
        # Result: Timer remains stopped (or starts then stops).
        
        # Let's inspect the behavior directly.
        # Reset timer
        self.window.timer.is_running = False
        
        # Click button
        self.window.start_btn.click()
        
        # If connected once: timer should be running.
        # If connected twice: timer might be paused (start -> pause).
        
        print(f"\n[Test StartBtn] Timer running state after click: {self.window.timer.is_running}")
        
        if not self.window.timer.is_running:
            print("[FAILURE] Timer is NOT running after click. Likely double connection toggled it on then off.")
        else:
            print("[SUCCESS] Timer is running.")
            
        # Verify call count inference
        # If it was double connected, self.timer.start() and self.timer.pause() would both be called.
        # We can't easily track that without mocking the timer *before* window creation, which we did.
        # But let's rely on the state check.

    def test_header_layout_alignment(self):
        """
        Test 2: Top Header Visibility
        Check if the container layout forces alignment that shrinks the header.
        """
        timer_page = self.window.content_stack.widget(0)
        # timer_page -> layout -> container -> layout
        # We need to find 'TimerContainer'
        container = timer_page.findChild(QWidget, "TimerContainer")
        self.assertIsNotNone(container, "TimerContainer not found")
        
        layout = container.layout()
        alignment = layout.alignment()
        
        print(f"\n[Test Header] Container Layout Alignment: {alignment}")
        
        # Qt.AlignmentFlag.AlignCenter is a combination of AlignVCenter | AlignHCenter
        # If AlignHCenter (0x0004) is present, items are horizontally centered and won't stretch.
        
        if alignment & Qt.AlignmentFlag.AlignHCenter:
            print("[FAILURE] Container has Horizontal Center Alignment. Header will not stretch.")
        else:
            print("[SUCCESS] Container does not have Horizontal Center Alignment.")

    def test_settings_numerals(self):
        """
        Test 3: Settings Numerals
        Check locale of the spinboxes.
        """
        settings_page = self.window.content_stack.widget(4) # Index 4 is settings
        # We need to access work_mins_spin. MainWindow saves it as self.work_mins_spin
        # but that attribute is on MainWindow.
        
        spinbox = self.window.work_mins_spin
        locale = spinbox.locale()
        
        print(f"\n[Test Settings] Spinbox Locale: {locale.name()}")
        
        # We want to ensure it's not something that produces non-Arabic digits.
        # Ideally it should be English or C, or we explicitely verify we are not seeing weird behavior.
        # But simply checking if we explicitly set it (which we haven't yet) is a good proxy.
        # We'll assert that we *want* it to be English/US for consistency.
        
        # Since we haven't fixed it, this might show system locale.
        pass

if __name__ == '__main__':
    unittest.main()
