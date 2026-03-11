from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup, QParallelAnimationGroup, QSize
from PyQt6.QtGui import QIcon
from logic.timer import PomodoroTimer
from ui.widgets import get_resource_path

class FloatingWindow(QWidget):
    switch_to_main = pyqtSignal()

    def __init__(self, timer: PomodoroTimer):
        super().__init__()
        self.timer = timer
        self.init_ui()
        self.setup_connections()
        self.old_pos = None
        
        # Entrance animation
        self.setWindowOpacity(0)
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(300)
        self.fade_anim.setStartValue(0)
        self.fade_anim.setEndValue(1)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_anim.start()

    def init_ui(self):
        self.setObjectName("FloatingWindow")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(220, 160)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.container = QFrame()
        self.container.setObjectName("FloatingContainer")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(12, 10, 12, 15)
        container_layout.setSpacing(5)
        
        # Header: Mode dot and Return button
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        
        self.mode_dot = QLabel("●")
        self.mode_dot.setStyleSheet("color: #000000; font-size: 14px;")
        
        self.mode_text = QLabel("专注中")
        self.mode_text.setProperty("class", "FloatingLabel")
        self.mode_text.setStyleSheet("color: #666; font-size: 11px; margin-left: 5px;")
        
        self.return_btn = QPushButton()
        self.return_btn.setIcon(QIcon(get_resource_path("resources/icon_restore.svg")))
        self.return_btn.setIconSize(QSize(18, 18))
        self.return_btn.setProperty("class", "FloatingControlBtn")
        self.return_btn.setFixedSize(28, 28)
        self.return_btn.setToolTip("返回主界面")
        self.return_btn.clicked.connect(self.switch_to_main.emit)
        
        header.addWidget(self.mode_dot)
        header.addWidget(self.mode_text)
        header.addStretch()
        header.addWidget(self.return_btn)
        
        # Timer Display
        self.timer_label = QLabel("25:00")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setObjectName("FloatingTimerLabel")
        self.timer_label.setStyleSheet("""
            font-size: 36px; 
            font-weight: bold; 
            font-family: 'Consolas', 'Segoe UI'; 
            margin: 2px 0;
        """)
        
        # Controls Row
        controls_layout = QHBoxLayout()
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Main Start/Abandon Button
        self.play_btn = self.create_control_btn(get_resource_path("resources/icon_play.svg"), "开始专注", "FloatingPlay")
        self.play_btn.setFixedSize(50, 50)
        self.play_btn.setIconSize(QSize(24, 24))
        # Remove manual styleSheet to avoid overriding QSS colors and hover effects
        
        controls_layout.addWidget(self.play_btn)
        
        container_layout.addLayout(header)
        container_layout.addWidget(self.timer_label)
        container_layout.addLayout(controls_layout)
        
        layout.addWidget(self.container)

    def create_control_btn(self, icon_path, text, object_name):
        btn = QPushButton()
        btn.setIcon(QIcon(icon_path))
        btn.setObjectName(object_name)
        btn.setProperty("class", "CircleControlBtn")
        btn.setToolTip(text)
        btn.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips)
        
        # Connect button click
        if object_name == "FloatingPlay":
            btn.clicked.connect(self.toggle_timer)
        
        return btn
        

    def setup_connections(self):
        self.timer.tick.connect(self.update_timer_display)
        self.timer.mode_changed.connect(self.update_mode_display)
        self.timer.started.connect(self.update_play_pause_button)
        self.timer.paused.connect(self.update_play_pause_button)
        self.timer.abandoned.connect(self.update_play_pause_button)
        
        # Initial UI sync
        self.update_timer_display(self.timer.remaining_seconds)
        self.update_mode_display(self.timer.current_mode)
        self.update_play_pause_button()

    def update_timer_display(self, seconds):
        mins, secs = divmod(seconds, 60)
        self.timer_label.setText(f"{mins:02d}:{secs:02d}")

    def update_play_pause_button(self):
        if self.timer.is_running:
            self.play_btn.setIcon(QIcon(get_resource_path("resources/icon_abandon.svg")))
            self.play_btn.setToolTip("放弃专注")
        else:
            self.play_btn.setIcon(QIcon(get_resource_path("resources/icon_play.svg")))
            self.play_btn.setToolTip("开始专注")

    def update_mode_display(self, mode):
        is_work = mode == 'work'
        self.mode_text.setText("专注中" if is_work else "休息中")
        self.mode_dot.setStyleSheet(f"color: #000000; font-size: 14px;")
        
        # Update play/pause button icon based on timer state
        self.update_play_pause_button()

    def toggle_timer(self):
        if self.timer.is_running:
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, '放弃当前番茄钟？',
                '确定要放弃当前这一组计时吗？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.timer.abandon()
        else:
            self.timer.start()
        
        # Simple scale animation for feedback
        self.anim = QPropertyAnimation(self.play_btn, b"iconSize")
        self.anim.setDuration(150)
        self.anim.setStartValue(QSize(20, 20))
        self.anim.setEndValue(QSize(24, 24))
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self.anim.start()

    # Mouse events for dragging with smooth movement
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def enterEvent(self, event):
        # Hover effect: slightly increase shadow or border
        # Removed dark background change
        super().enterEvent(event)

    def leaveEvent(self, event):
        super().leaveEvent(event)
