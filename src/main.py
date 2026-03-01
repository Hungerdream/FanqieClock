import sys
import os
import ctypes
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtCore import Qt, QSharedMemory
from PyQt6.QtGui import QIcon
from logic.timer import PomodoroTimer
from ui.main_window import MainWindow
from ui.floating_window import FloatingWindow

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if hasattr(sys, 'frozen'):
        # PyInstaller
        if hasattr(sys, '_MEIPASS'):
            # OneFile mode
            base_path = sys._MEIPASS
        else:
            # OneDir mode
            base_path = os.path.dirname(sys.executable)
    else:
        # Dev mode: src/main.py -> src
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)

class PomodoroApp:
    def __init__(self):
        # Single instance check using QSharedMemory
        self.shared_memory = QSharedMemory("FanqieClock_SingleInstance")
        if not self.shared_memory.create(1):
            # Another instance is already running
            print("番茄钟已经在运行中")
            sys.exit(1)
        
        # Set AppUserModelID for Windows Taskbar Icon
        myappid = 'Trae.FanqieClock.App.1.0' # arbitrary string
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass # Fails on non-Windows

        self.app = QApplication(sys.argv)
        
        # Load stylesheet
        style_path = get_resource_path(os.path.join("styles", "style.qss"))
        if os.path.exists(style_path):
            with open(style_path, "r", encoding="utf-8") as f:
                self.app.setStyleSheet(f.read())
        
        # Set App Icon
        icon_path = get_resource_path(os.path.join("resources", "icon_app.svg"))
        if os.path.exists(icon_path):
            app_icon = QIcon(icon_path)
            self.app.setWindowIcon(app_icon)
        
        self.timer = PomodoroTimer()
        self.main_window = MainWindow(self.timer)
        self.floating_window = FloatingWindow(self.timer)
        
        self.setup_tray()
        
        # Connect mode switching
        self.main_window.switch_to_compact.connect(self.show_compact)
        self.floating_window.switch_to_main.connect(self.show_main)
        self.timer.finished.connect(self.notify_finished)
        
        self.main_window.show()

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self.app)
        
        # Use our custom icon
        icon_path = get_resource_path(os.path.join("resources", "icon_app.svg"))
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            self.tray_icon.setIcon(QIcon.fromTheme("appointment-new"))
        
        self.tray_menu = QMenu()
        show_action = self.tray_menu.addAction("显示主界面")
        show_action.triggered.connect(self.show_main)
        
        quit_action = self.tray_menu.addAction("退出")
        quit_action.triggered.connect(self.app.quit)
        
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_main()

    def notify_finished(self):
        # self.timer.current_mode is the mode that JUST finished (signal emitted before switch)
        if self.timer.current_mode == 'work':
            title = "专注时间结束！"
            message = "休息一下，放松眼睛和大脑。"
        elif self.timer.current_mode == 'long_break':
            title = "长休息结束！"
            message = "充电完毕，准备好开始新的专注了吗？"
        else:
            title = "休息时间结束！"
            message = "准备好开始新的专注了吗？"
        
        self.tray_icon.showMessage(
            title,
            message,
            QSystemTrayIcon.MessageIcon.Information,
            5000
        )
        # Sound feedback is already handled in Timer class thread

    def show_compact(self):
        self.main_window.hide()
        # Position floating window near the top right of the screen
        screen = QApplication.primaryScreen().geometry()
        self.floating_window.move(screen.width() - 250, 50)
        self.floating_window.show()

    def show_main(self):
        self.floating_window.hide()
        
        # Ensure window is not minimized and bring to front
        self.main_window.setWindowState(Qt.WindowState.WindowNoState)
        self.main_window.show()
        self.main_window.activateWindow()

    def run(self):
        try:
            sys.exit(self.app.exec())
        finally:
            # Clean up shared memory
            self.shared_memory.detach()

if __name__ == "__main__":
    app = PomodoroApp()
    app.run()
