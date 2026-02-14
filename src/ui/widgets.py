from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QListWidget, QListWidgetItem, QAbstractItemView)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRectF, pyqtProperty, QPointF
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPainterPath
import sys, os

def get_resource_path(relative_path):
    if hasattr(sys, 'frozen'):
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(sys.executable)
    else:
        # src/ui/widgets.py -> src
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

class SmoothButton(QPushButton):
    """
    A rounded button with antialiasing enabled to prevent jagged edges.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._bg_color = QColor("#000000")
        self._hover_color = QColor("#333333")
        self._pressed_color = QColor("#555555")
        self._border_radius = 0
        self._is_hovered = False
        self._is_pressed = False

    def set_colors(self, bg, hover, pressed):
        self._bg_color = QColor(bg)
        self._hover_color = QColor(hover)
        self._pressed_color = QColor(pressed)
        self.update()

    def set_border_radius(self, radius):
        self._border_radius = radius
        self.update()

    def enterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_pressed = False
            self.update()
            # self.clicked.emit() # Removed to prevent double signal
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Determine background color
        if self._is_pressed:
            bg = self._pressed_color
        elif self._is_hovered:
            bg = self._hover_color
        else:
            bg = self._bg_color

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)

        # Draw rounded background
        # Adjust rect by 1px to ensure anti-aliasing has space to render smoothly without clipping
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        
        # If radius is not set, use half height for pill/circle shape
        radius = self._border_radius if self._border_radius > 0 else min(rect.width(), rect.height()) / 2
        
        painter.drawRoundedRect(rect, radius, radius)

        # Draw Icon
        if not self.icon().isNull():
            icon_size = self.iconSize()
            # Calculate centered position
            x = (self.width() - icon_size.width()) / 2
            y = (self.height() - icon_size.height()) / 2
            
            self.icon().paint(painter, int(x), int(y), icon_size.width(), icon_size.height())

class CircularProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 100
        self._max_value = 100
        self._color = QColor("#BB86FC")
        self.setMinimumSize(400, 400)
        
        # Layout for centered content
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.setContentsMargins(0, 0, 0, 0)

    @pyqtProperty(float)
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        self._value = val
        self.update()

    def set_max_value(self, max_val):
        self._max_value = max_val
        self.update()

    def set_color(self, color_str):
        self._color = QColor(color_str)
        self.update()

    def paintEvent(self, event):
        width = self.width()
        height = self.height()
        side = min(width, height) - 20
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Center the coordinate system
        painter.translate(width / 2, height / 2)
        
        # Background Circle
        bg_pen = QPen(QColor("#F0F0F0"))
        bg_pen.setWidth(10)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawEllipse(QRectF(-side/2, -side/2, side, side))
        
        # Progress Arc
        if self._max_value > 0:
            progress_pen = QPen(self._color)
            progress_pen.setWidth(10)
            progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(progress_pen)
            
            # Calculate angle (in 1/16th of a degree)
            # 90 degrees is the top (start angle)
            # Clockwise progress: span angle should be negative
            span_angle = int(-(self._value / self._max_value) * 360 * 16)
            painter.drawArc(QRectF(-side/2, -side/2, side, side), 90 * 16, span_angle)

class KanbanItemWidget(QWidget):
    focus_requested = pyqtSignal(dict)
    delete_requested = pyqtSignal()
    
    def __init__(self, task_data, parent=None):
        super().__init__(parent)
        self.task_data = task_data
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 5, 5)
        
        # Content Layout
        content_layout = QVBoxLayout()
        content_layout.setSpacing(2)
        
        self.label = QLabel(task_data.get("content", ""))
        self.label.setObjectName("KanbanItemLabel")
        self.label.setWordWrap(True)
        self.label.setStyleSheet("font-family: 'Microsoft YaHei', 'Segoe UI'; font-size: 14px; color: #333; line-height: 1.4;")
        
        # Pomodoro Count
        pomo_count = task_data.get("pomodoros", 0)
        self.pomo_label = QLabel(f"🍅 {pomo_count}" if pomo_count > 0 else "")
        self.pomo_label.setStyleSheet("color: #FF6B6B; font-size: 12px; font-weight: bold;")
        
        content_layout.addWidget(self.label)
        if pomo_count > 0:
            content_layout.addWidget(self.pomo_label)
        
        self.focus_btn = QPushButton()
        self.focus_btn.setFixedSize(30, 30)
        self.focus_btn.setIcon(QIcon(get_resource_path("resources/icon_item_focus.svg")))
        self.focus_btn.setIconSize(QSize(24, 24))
        self.focus_btn.setToolTip("开始专注此任务")
        self.focus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.focus_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 15px;
            }
            QPushButton:hover {
                background: #E3F2FD;
            }
        """)
        self.focus_btn.clicked.connect(lambda: self.focus_requested.emit(self.task_data))
        
        self.delete_btn = QPushButton()
        self.delete_btn.setFixedSize(30, 30)
        self.delete_btn.setIcon(QIcon(get_resource_path("resources/icon_item_delete.svg")))
        self.delete_btn.setIconSize(QSize(20, 20))
        self.delete_btn.setToolTip("删除任务")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 15px;
                margin-left: 5px;
            }
            QPushButton:hover {
                background: #FFEBEE;
            }
        """)
        self.delete_btn.clicked.connect(self.delete_requested.emit)
        
        layout.addLayout(content_layout, 1)
        layout.addWidget(self.focus_btn)
        layout.addWidget(self.delete_btn)

class KanbanList(QListWidget):
    item_deleted = pyqtSignal()
    order_changed = pyqtSignal()
    focus_task = pyqtSignal(dict)

    def __init__(self, data_manager, category):
        super().__init__()
        self.data_manager = data_manager
        self.category = category
        self.setObjectName("KanbanList")
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setProperty("class", "KanbanList")
        self.setStyleSheet("""
            QListWidget::item { 
                margin: 5px; 
                background: #FFFFFF; 
                border-radius: 12px;
            }
        """)

    def add_task_item(self, task_data):
        item = QListWidgetItem(self)
        # Store dict in UserRole
        item.setData(Qt.ItemDataRole.UserRole, task_data)
        item.setSizeHint(QSize(0, 80))
        self.addItem(item)
        
        widget = KanbanItemWidget(task_data)
        widget.focus_requested.connect(self.focus_task.emit)
        widget.delete_requested.connect(lambda: self.handle_delete_item(item))
        self.setItemWidget(item, widget)

    def handle_delete_item(self, item):
        row = self.row(item)
        self.takeItem(row)
        self.item_deleted.emit()

    def dropEvent(self, event):
        super().dropEvent(event)
        # Re-apply widgets after drop
        for i in range(self.count()):
            item = self.item(i)
            item.setSizeHint(QSize(0, 80))
            if not self.itemWidget(item):
                # Retrieve data from UserRole
                task_data = item.data(Qt.ItemDataRole.UserRole)
                if task_data:
                    widget = KanbanItemWidget(task_data)
                    widget.focus_requested.connect(self.focus_task.emit)
                    widget.delete_requested.connect(lambda it=item: self.handle_delete_item(it))
                    self.setItemWidget(item, widget)
        
        self.order_changed.emit()

class LongBreakOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: rgba(26, 35, 126, 0.95);") # Deep indigo overlay
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        label = QLabel("🧘 长休息时间")
        label.setStyleSheet("color: white; font-size: 48px; font-weight: bold;")
        
        guide = QLabel("请离开座位，放松双眼。\n\n建议动作：\n1. 颈部拉伸\n2. 眺望远方\n3. 深呼吸三分钟")
        guide.setStyleSheet("color: #E8EAF6; font-size: 24px; margin-top: 40px; line-height: 1.6;")
        guide.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(label)
        layout.addWidget(guide)
        
    def mousePressEvent(self, event):
        # Block interaction
        event.accept()

class NumberControl(QWidget):
    valueChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._min = 0
        self._max = 100
        self._step = 1
        self._suffix = ""
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Minus Button
        self.minus_btn = QPushButton()
        self.minus_btn.setIcon(QIcon(get_resource_path("resources/icon_minus.svg")))
        self.minus_btn.setIconSize(QSize(18, 18))
        self.minus_btn.setFixedSize(36, 36)
        self.minus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.minus_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #EEEEEE;
                border-color: #CCCCCC;
            }
            QPushButton:pressed {
                background-color: #E0E0E0;
            }
        """)
        self.minus_btn.clicked.connect(self.decrement)
        
        # Value Display
        self.value_label = QLabel()
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333; background: transparent;")
        self.value_label.setMinimumWidth(60)
        
        # Plus Button
        self.plus_btn = QPushButton()
        self.plus_btn.setIcon(QIcon(get_resource_path("resources/icon_plus.svg")))
        self.plus_btn.setIconSize(QSize(18, 18))
        self.plus_btn.setFixedSize(36, 36)
        self.plus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.plus_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #EEEEEE;
                border-color: #CCCCCC;
            }
            QPushButton:pressed {
                background-color: #E0E0E0;
            }
        """)
        self.plus_btn.clicked.connect(self.increment)
        
        layout.addWidget(self.minus_btn)
        layout.addWidget(self.value_label)
        layout.addWidget(self.plus_btn)
        
        self.update_display()

    def setRange(self, min_val, max_val):
        self._min = min_val
        self._max = max_val
        if self._value < min_val: self.setValue(min_val)
        if self._value > max_val: self.setValue(max_val)

    def setSuffix(self, text):
        self._suffix = text
        self.update_display()

    def value(self):
        return self._value

    def setValue(self, val):
        val = max(self._min, min(val, self._max))
        if val != self._value:
            self._value = val
            self.update_display()
            self.valueChanged.emit(val)

    def increment(self):
        self.setValue(self._value + self._step)

    def decrement(self):
        self.setValue(self._value - self._step)

    def update_display(self):
        self.value_label.setText(f"{self._value}{self._suffix}")

