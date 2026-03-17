from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QStackedWidget, QTextEdit, 
                             QLineEdit, QListWidget, QFrame, QListWidgetItem,
                             QAbstractItemView, QDialog, QFormLayout, QSpinBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QGraphicsOpacityEffect, QProgressBar, QSizePolicy,
                             QCheckBox, QGridLayout, QMessageBox, QFileDialog, QMenu, QStackedLayout,
                             QApplication, QScrollArea)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve, QDate, QEvent, QParallelAnimationGroup, QTimer
from PyQt6.QtGui import QColor, QFont, QIcon, QTextDocument, QPageSize, QPdfWriter, QCursor, QPixmap
import sys, os
import uuid
from logic.timer import PomodoroTimer
from logic.data_manager import DataManager
from logic.quote_worker import QuoteWorker
from ui.widgets import CircularProgressBar, KanbanItemWidget, KanbanList, LongBreakOverlay, SmoothButton, NumberControl
from ui.chart_widgets import BarChartWidget, HeatmapWidget

# 全局快捷键（可选依赖）
try:
    import keyboard as _keyboard
    _KEYBOARD_AVAILABLE = True
except ImportError:
    _KEYBOARD_AVAILABLE = False

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
        # Dev mode: src/ui/main_window.py -> src
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

class MainWindow(QMainWindow):
    switch_to_compact = pyqtSignal()
    # 全局快捷键触发信号（keyboard 钩子在子线程，需要信号切回主线程）
    _global_shortcut_triggered = pyqtSignal(str)

    def __init__(self, timer: PomodoroTimer):
        super().__init__()
        self.timer = timer
        self.data_manager = DataManager()
        self.current_task = None
        self.init_ui()
        self.load_saved_data()
        self.setup_connections()
        self._setup_global_shortcuts()
        
        # Fetch Daily Quote
        self.quote_worker = QuoteWorker()
        self.quote_worker.quote_fetched.connect(self.update_daily_quote)
        self.quote_worker.start()

    def _setup_global_shortcuts(self):
        """注册全局快捷键（窗口最小化/隐藏时也有效）"""
        self._global_shortcut_triggered.connect(self._handle_global_shortcut)
        if not _KEYBOARD_AVAILABLE:
            print("[Shortcut] keyboard lib not installed, global hotkey unavailable. Window-focus space key only.")
            return
        try:
            # 空格键：开始/放弃计时
            _keyboard.add_hotkey("space", lambda: self._global_shortcut_triggered.emit("space"),
                                  suppress=False)
            print("[Shortcut] Global hotkey registered: Space=start/pause")
        except Exception as e:
            print(f"[Shortcut] Failed to register global hotkey: {e}")

    def _handle_global_shortcut(self, key: str):
        """在主线程中处理全局快捷键事件"""
        if key == "space":
            # 如果焦点在文本输入框，忽略（避免打断正常输入）
            focused = QApplication.focusWidget()
            if isinstance(focused, (QLineEdit, QTextEdit)):
                return
            # 切换到计时页并触发 toggle
            if self.content_stack.currentIndex() != 0:
                self.switch_page(0)
                # 如果窗口隐藏/最小化，先恢复
                if self.isMinimized() or not self.isVisible():
                    self.showNormal()
                    self.activateWindow()
            self.toggle_timer()

    def update_daily_quote(self, content, author):
        if hasattr(self, 'quote_label') and hasattr(self, 'quote_author'):
            self.quote_label.setText(content)
            self.quote_author.setText(author)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            if self.windowState() & Qt.WindowState.WindowMinimized:
                QTimer.singleShot(0, self.switch_to_compact.emit)
        super().changeEvent(event)

    def closeEvent(self, event):
        # If the event is spontaneous (e.g., user clicked 'X'), minimize to tray
        if event.spontaneous():
            event.ignore()
            self.hide()
        else:
            # Stop all timers to prevent callbacks after destruction
            self.sidebar_hide_timer.stop()
            self.sidebar_hover_timer.stop()
            # Clean up QuoteWorker thread
            if hasattr(self, 'quote_worker') and self.quote_worker.isRunning():
                self.quote_worker.quit()
                self.quote_worker.wait(2000)  # Wait up to 2s
            # 清理全局快捷键钩子
            if _KEYBOARD_AVAILABLE:
                try:
                    _keyboard.unhook_all()
                except Exception:
                    pass
            # If triggered by app.quit(), save data and let it close
            try:
                self.data_manager.save_data_sync()
            except Exception as e:
                print(f"Error saving data on close: {e}")
            event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            if self.content_stack.currentIndex() == 0: # Timer page
                self.toggle_timer()
        else:
            super().keyPressEvent(event)

    def init_ui(self):
        self.setWindowTitle("番茄钟")
        self.setMinimumSize(1100, 750)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QHBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. Sidebar (Persistent)
        self.sidebar = QFrame()
        self.sidebar.setFrameShape(QFrame.Shape.NoFrame)
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(85) # Set initial fixed width for animation
        self.sidebar.installEventFilter(self) # Install event filter for hover logic
        sidebar_layout = QVBoxLayout(self.sidebar)
        # Add left margin > 4px to ensure content is clipped/hidden when width is small
        sidebar_layout.setContentsMargins(10, 30, 10, 10) 
        
        # Sidebar Hide Timer (Debounce)
        self.sidebar_hide_timer = QTimer()
        self.sidebar_hide_timer.setSingleShot(True)
        self.sidebar_hide_timer.setInterval(300) # 300ms delay
        self.sidebar_hide_timer.timeout.connect(self.check_and_hide_sidebar)
        
        # Sidebar Hover Polling Timer (For wider trigger area)
        # Only runs when sidebar is collapsed, to detect hot-zone entry
        self.sidebar_hover_timer = QTimer()
        self.sidebar_hover_timer.setInterval(50) # Check every 50ms
        self.sidebar_hover_timer.timeout.connect(self.check_sidebar_hover)
        self.sidebar_hover_timer.start() # Will self-stop when sidebar expands
        
        self.nav_btns = []
        
        nav_items = [
            (get_resource_path("resources/icon_focus.svg"), "专注"),
            (get_resource_path("resources/icon_tasks.svg"), "任务"),
            (get_resource_path("resources/icon_notes.svg"), "笔记"),
            (get_resource_path("resources/icon_stats.svg"), "统计"),
            (get_resource_path("resources/icon_settings.svg"), "设置")
        ]
        
        for i, (icon_path, label) in enumerate(nav_items):
            btn = QPushButton()
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QSize(24, 24))
            btn.setProperty("class", "SidebarButton")
            btn.setToolTip(label)
            btn.setCheckable(True)
            # Allow button to shrink below its content size
            btn.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            if i == 0: 
                btn.setChecked(True)
                btn.setProperty("active", "true")
            btn.clicked.connect(lambda checked, index=i: self.switch_page(index))
            sidebar_layout.addWidget(btn)
            self.nav_btns.append(btn)
        
        sidebar_layout.addStretch()
        
        # Add sidebar to layout
        self.main_layout.addWidget(self.sidebar)

        # 2. Main Content Stack
        self.content_stack = QStackedWidget()
        
        # Pages
        self.content_stack.addWidget(self.create_timer_page())
        self.content_stack.addWidget(self.create_kanban_page())
        self.content_stack.addWidget(self.create_notes_page())
        self.content_stack.addWidget(self.create_stats_page())
        self.content_stack.addWidget(self.create_settings_page())
        
        self.main_layout.addWidget(self.content_stack)
        
        # Long Break Overlay
        self.long_break_overlay = LongBreakOverlay(self)
        self.long_break_overlay.hide()
        
        # Default to Timer Page
        self.switch_page(0)

    def resizeEvent(self, event):
        if hasattr(self, 'long_break_overlay'):
            self.long_break_overlay.resize(self.size())
            
        # Responsive Sidebar Logic
        # Only trigger if timer is NOT running (timer auto-hide takes precedence)
        if not hasattr(self, 'timer') or not self.timer.is_running:
            width = event.size().width()
            settings = self.data_manager.data.get("settings", {})
            manual_state = settings.get("sidebar_manual_state", None)
            
            # If user has manually set state, respect it (unless it was just a toggle)
            # Actually, "responsive" usually means adapting to screen size.
            # If user toggles manually, we set manual_state.
            # But if window is resized across breakpoint, should we override manual?
            # User requirement: "Expand mobile trigger threshold to >= 1200px"
            # Let's say: 
            # < 1200: Compact (collapsed)
            # >= 1200: Expanded
            # UNLESS manual override is set? 
            # Let's keep it simple first: responsive overrides manual on breakpoint cross,
            # or manual overrides responsive?
            # A common pattern: Manual toggle sets a "preference". 
            # But responsive layout is "structural".
            # Let's implement: If width < 1200, collapse. If width >= 1200, expand.
            # BUT only if we haven't already done so for this size range.
            
            # We need to store current "responsive mode" to detect change
            is_compact_width = width < 1200
            if not hasattr(self, '_last_compact_mode'):
                # Initialize from the OLD size so we can detect a crossing event
                old_width = event.oldSize().width()
                self._last_compact_mode = (old_width < 1200) if old_width > 0 else (not is_compact_width)
                
            if is_compact_width != self._last_compact_mode:
                # Mode changed
                if is_compact_width:
                    self.animate_sidebar(0)
                else:
                    self.animate_sidebar(85)
                self._last_compact_mode = is_compact_width
                
        super().resizeEvent(event)



    def create_timer_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        container = QWidget()
        container.setObjectName("TimerContainer")
        container_layout = QVBoxLayout(container)
        
        # Top Header
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(30, 20, 30, 0)
        
        # Hamburger Menu for Sidebar (In Header - Removing as we moved it to sidebar itself)
        # self.menu_btn = QPushButton("☰")
        # ...
        # header_layout.addWidget(self.menu_btn)
        
        logo = QLabel("番茄钟")
        logo.setStyleSheet("font-size: 20px; font-weight: bold; color: #333; margin-left: 10px;")
        
        header_layout.addWidget(logo)
        header_layout.addStretch()
        
        icon_btns_layout = QHBoxLayout()
        icon_btns_layout.setSpacing(20)
        
        # Header Icons including Compact Mode
        # (key, tooltip, icon_path)
        header_btns_data = [
            ("compact", "切换小窗模式", get_resource_path("resources/icon_compact.svg")),
            ("theme", "深色模式", get_resource_path("resources/icon_theme.svg"))
        ]

        for key, tooltip, icon_path in header_btns_data:
            btn = QPushButton()
            btn.setFixedSize(35, 35)
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QSize(20, 20))
            
            # WCAG 2.1 Compliant Style
            # High contrast: Dark Grey (#333) on Light Background
            # Border: 1px Solid #CCC for clear boundary
            # Hover/Pressed states for feedback
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #F8F9FA;
                    border: 1px solid #CCCCCC;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #E9ECEF;
                    border-color: #999999;
                }
                QPushButton:pressed {
                    background-color: #DEE2E6;
                    border-color: #666666;
                }
            """)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tooltip)
            
            icon_btns_layout.addWidget(btn)
            
            if key == "compact":
                self.compact_mode_btn = btn
                btn.clicked.connect(self.switch_to_compact.emit)
            elif key == "theme":
                self.theme_btn = btn
                self.theme_btn.setCheckable(True)
                self.theme_btn.toggled.connect(self.on_theme_toggled)
        
        header_layout.addLayout(icon_btns_layout)
        container_layout.addWidget(header)
        
        # Top Spacer
        container_layout.addStretch(1)
        
        # Mode Label
        self.mode_label = QLabel("准备开始")
        self.mode_label.setObjectName("ModeLabel")
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.mode_label)
        
        # Circular Progress Bar
        progress_container = QWidget()
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.progress_bar = CircularProgressBar(progress_container)
        self.progress_bar.setMinimumSize(360, 360) 
        self.progress_bar.set_color("#000000") 
        self.progress_bar.set_bg_color("#F0F0F0")
        self.progress_bar.show()
        
        # Stacked Layout for Timer and Long Break Overlay
        self.display_stack = QStackedLayout()
        self.progress_bar.content_layout.addLayout(self.display_stack)

        # Timer Label (in the stack)
        self.timer_label = QLabel("25:00")
        self.timer_label.setObjectName("TimerLabel")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet("font-size: 96px; font-weight: bold; color: #1A1A1A; font-family: 'Segoe UI', sans-serif; background: transparent;")
        self.display_stack.addWidget(self.timer_label)

        progress_layout.addWidget(self.progress_bar)
        
        container_layout.addWidget(progress_container)
        container_layout.addSpacing(20)

        # Interruption Buttons
        int_layout = QHBoxLayout()
        int_layout.setSpacing(15)
        int_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_int_in = QPushButton("🧠 内部冲动")
        btn_int_in.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_int_in.setStyleSheet("background: #FFF3E0; color: #E65100; border: none; padding: 5px 15px; border-radius: 15px;")
        btn_int_in.clicked.connect(lambda: self.record_interruption("internal"))
        
        btn_int_ex = QPushButton("🔔 外部打扰")
        btn_int_ex.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_int_ex.setStyleSheet("background: #FFEBEE; color: #C62828; border: none; padding: 5px 15px; border-radius: 15px;")
        btn_int_ex.clicked.connect(lambda: self.record_interruption("external"))
        
        int_layout.addWidget(btn_int_in)
        int_layout.addWidget(btn_int_ex)
        container_layout.addLayout(int_layout)
        container_layout.addSpacing(20)
        
        # Controls
        controls_layout = QHBoxLayout()
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Main Start/Abandon Button
        self.start_btn = SmoothButton()
        self.start_btn.setIcon(QIcon(get_resource_path("resources/icon_play.svg")))
        self.start_btn.setIconSize(QSize(32, 32))
        self.start_btn.setFixedSize(80, 80) # Slightly larger for single button
        self.start_btn.set_colors("#000000", "#333333", "#555555")
        self.start_btn.set_border_radius(40)
        self.start_btn.setToolTip("开始专注")
        
        controls_layout.addWidget(self.start_btn)
        
        container_layout.addLayout(controls_layout)
        container_layout.addStretch(2)
        
        # Bottom Info Bar
        info_bar = QWidget()
        info_bar.setObjectName("InfoBar")
        info_bar_layout = QHBoxLayout(info_bar)
        info_bar_layout.setContentsMargins(50, 0, 50, 40)
        
        self.work_info = QLabel("工作 25:00")
        self.work_info.setProperty("class", "InfoLabelActive")
        
        self.progress_line = QProgressBar()
        self.progress_line.setTextVisible(False)
        self.progress_line.setFixedHeight(4)
        self.progress_line.setStyleSheet("""
            QProgressBar {
                background-color: #F0F0F0;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #000000;
                border-radius: 2px;
            }
        """)
        
        self.break_info = QLabel("休息 05:00")
        self.break_info.setProperty("class", "InfoLabel")
        
        info_bar_layout.addWidget(self.work_info)
        info_bar_layout.addWidget(self.progress_line, 1)
        info_bar_layout.addWidget(self.break_info)
        
        container_layout.addWidget(info_bar)
        layout.addWidget(container)
        
        return page

    def abandon_timer(self):
        self.timer.reset()
        self.mode_label.setText("已放弃")
        if self.auto_hide_sidebar_toggle.isChecked():
            self.animate_sidebar(85)

    def record_interruption(self, type_name):
        self.data_manager.record_interruption(type_name)
        self.mode_label.setText(f"已记录：{'内部' if type_name=='internal' else '外部'}打断")
        QTimer.singleShot(1500, lambda: self.update_mode_display(self.timer.current_mode))

    def create_kanban_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("任务矩阵 (四象限)")
        title.setProperty("class", "KanbanTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Quadrant Grid
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)
        
        self.kanban_cols = {}
        # Quadrant Config: (key, title, row, col, bg_color)
        quadrants = [
            ("q1", "🔥 重要且紧急", 0, 0, "#FFEBEE"),
            ("q2", "📅 重要不紧急", 0, 1, "#E3F2FD"),
            ("q3", "⚡ 紧急不重要", 1, 0, "#FFF3E0"),
            ("q4", "☕ 不重要不紧急", 1, 1, "#F3E5F5")
        ]
        
        for key, title, r, c, bg_color in quadrants:
            frame = QFrame()
            frame.setObjectName(f"Quadrant_{key}")
            frame.setStyleSheet(f"""
                #Quadrant_{key} {{
                    background-color: {bg_color};
                    border-radius: 12px;
                    border: 1px solid transparent;
                }}
            """)
            v_layout = QVBoxLayout(frame)
            v_layout.setContentsMargins(10, 10, 10, 10)
            
            header_lbl = QLabel(title)
            header_lbl.setStyleSheet("font-weight: bold; font-size: 15px; color: #555; margin-bottom: 5px;")
            v_layout.addWidget(header_lbl)
            
            # Input for this quadrant
            input_field = QLineEdit()
            input_field.setPlaceholderText("＋ 添加任务...")
            input_field.setStyleSheet("background: rgba(255,255,255,0.7); border: none; border-radius: 5px; padding: 5px;")
            # Use closure to capture key
            input_field.returnPressed.connect(lambda k=key, f=input_field: self.add_kanban_task(k, f))
            v_layout.addWidget(input_field)
            
            list_widget = KanbanList(self.data_manager, key)
            list_widget.item_deleted.connect(self.save_kanban_state)
            list_widget.order_changed.connect(self.save_kanban_state)
            list_widget.focus_task.connect(self.start_focus_on_task)
            
            v_layout.addWidget(list_widget)
            self.kanban_cols[key] = list_widget
            
            grid_layout.addWidget(frame, r, c)
            
        layout.addLayout(grid_layout, 1)
        
        # Completed Section (Collapsible-like)
        comp_frame = QFrame()
        comp_frame.setStyleSheet("background-color: #FAFAFA; border-radius: 10px; border: 1px solid #EEE;")
        comp_layout = QVBoxLayout(comp_frame)
        comp_layout.setContentsMargins(10, 10, 10, 10)
        
        comp_header = QLabel("✅ 已完成任务")
        comp_header.setStyleSheet("font-weight: bold; color: #888;")
        comp_layout.addWidget(comp_header)
        
        self.completed_list = KanbanList(self.data_manager, "completed")
        self.completed_list.setMaximumHeight(150) # Limit height
        self.completed_list.item_deleted.connect(self.save_kanban_state)
        self.completed_list.order_changed.connect(self.save_kanban_state)
        self.kanban_cols["completed"] = self.completed_list
        
        comp_layout.addWidget(self.completed_list)
        layout.addWidget(comp_frame)
            
        return page

    def create_notes_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Daily Quote Card
        quote_card = QFrame()
        quote_card.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border-radius: 15px;
                border: 1px solid #EEE;
            }
        """)
        quote_layout = QVBoxLayout(quote_card)
        quote_layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("每日一句")
        title.setStyleSheet("font-size: 14px; color: #999; font-weight: bold; margin-bottom: 5px;")
        
        self.quote_label = QLabel("正在获取灵感...")
        self.quote_label.setWordWrap(True)
        self.quote_label.setStyleSheet("font-size: 18px; color: #333; font-family: 'Kaiti', 'Microsoft YaHei'; line-height: 1.5;")
        
        self.quote_author = QLabel("")
        self.quote_author.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.quote_author.setStyleSheet("font-size: 14px; color: #666; margin-top: 10px;")
        
        quote_layout.addWidget(title)
        quote_layout.addWidget(self.quote_label)
        quote_layout.addWidget(self.quote_author)
        
        layout.addWidget(quote_card)
        layout.addSpacing(30)
        
        # Header: New, Search, Filter
        header = QHBoxLayout()
        self.new_note_btn = QPushButton("新建笔记")
        self.new_note_btn.setObjectName("PrimaryButton")
        self.new_note_btn.clicked.connect(self.show_note_dialog)
        
        self.note_search = QLineEdit()
        self.note_search.setPlaceholderText("🔍 搜索笔记标题或内容...")
        self.note_search.textChanged.connect(self.filter_notes)
        
        header.addWidget(self.new_note_btn)
        header.addSpacing(20)
        header.addWidget(self.note_search, 1)
        
        # Notes Table
        self.notes_table = QTableWidget(0, 2)
        self.notes_table.setObjectName("NotesTable")
        self.notes_table.setHorizontalHeaderLabels(["标题", "摘要"])
        self.notes_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.notes_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.notes_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.notes_table.verticalHeader().setVisible(False)
        self.notes_table.setShowGrid(False)
        self.notes_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.notes_table.itemDoubleClicked.connect(self.edit_note)
        
        # Context Menu
        self.notes_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.notes_table.customContextMenuRequested.connect(self.show_note_context_menu)
        
        layout.addLayout(header)
        layout.addWidget(self.notes_table)
        return page

    def create_stats_page(self):
        # 外层容器（直接放入 content_stack）
        outer = QWidget()
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # 滚动区域，内容超出时可以滚动，避免卡片被压缩
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        outer_layout.addWidget(scroll)

        page = QWidget()
        page.setStyleSheet("background: transparent;")
        scroll.setWidget(page)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(50, 40, 50, 40)
        
        # Header with Title and Date
        header_layout = QHBoxLayout()
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("专注统计")
        title.setProperty("class", "KanbanTitle")
        title.setStyleSheet("font-size: 28px; margin-bottom: 5px;")
        
        subtitle = QLabel("查看您的专注历史与数据分析")
        subtitle.setStyleSheet("color: #888; font-size: 14px;")
        
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        
        header_layout.addWidget(title_container)
        header_layout.addStretch()
        
        # Export Button
        export_btn = QPushButton("导出报告 (PDF)")
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.clicked.connect(self.export_stats_pdf)
        header_layout.addWidget(export_btn)
        
        layout.addLayout(header_layout)
        layout.addSpacing(30)
        
        # Summary Cards Grid
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)
        
        self.stat_pomos = self.create_stat_card("累计番茄", "0", "🍅", "#FFF0F0")
        self.stat_time = self.create_stat_card("专注时长", "0 分钟", "⏱️", "#F0F8FF")
        self.stat_days = self.create_stat_card("累计天数", "0", "📅", "#F5F5F5")
        self.stat_interrupts = self.create_stat_card("打断次数", "0", "⚡", "#FFF8E1")
        
        cards_layout.addWidget(self.stat_pomos)
        cards_layout.addWidget(self.stat_time)
        cards_layout.addWidget(self.stat_days)
        cards_layout.addWidget(self.stat_interrupts)
        
        layout.addLayout(cards_layout)
        layout.addSpacing(30)

        # ── 近7天柱状图 ──────────────────────────────────────────────────
        chart_title = QLabel("近 7 天番茄数")
        chart_title.setStyleSheet("font-size: 15px; font-weight: 600; color: #444; margin-bottom: 6px;")
        layout.addWidget(chart_title)

        self.bar_chart = BarChartWidget()
        self.bar_chart.setFixedHeight(180)
        layout.addWidget(self.bar_chart)

        layout.addSpacing(20)

        # ── 热力图（Pomotroid 年度视图，含年份导航）────────────────────
        heatmap_title = QLabel("历史打卡热力图")
        heatmap_title.setStyleSheet("font-size: 15px; font-weight: 600; color: #444; margin-bottom: 2px;")
        layout.addWidget(heatmap_title)

        self.heatmap = HeatmapWidget()
        # 不设固定高度，让其自适应（内部画布会计算自身高度）
        layout.addWidget(self.heatmap)

        layout.addSpacing(30)
        
        # Today's Detail
        self.today_stat_label = QLabel("今日专注：0个番茄")
        self.today_stat_label.setStyleSheet("font-size: 18px; color: #333333; margin-bottom: 20px; font-weight: bold;")
        layout.addWidget(self.today_stat_label)
        
        # History Section
        history_title = QLabel("最近记录")
        history_title.setProperty("class", "KanbanTitle")
        history_title.setStyleSheet("font-size: 18px; margin-bottom: 15px;")
        layout.addWidget(history_title)
        
        self.history_list = QListWidget()
        self.history_list.setProperty("class", "KanbanList")
        self.history_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; }
            QListWidget::item { 
                background: #FFFFFF; 
                border-radius: 10px; 
                margin-bottom: 10px; 
                padding: 15px; 
                border: 1px solid #F0F0F0;
                color: #555;
            }
            QListWidget::item:hover { background: #FAFAFA; border-color: #EEE; }
        """)
        layout.addWidget(self.history_list)
        layout.addStretch()

        return outer

    def create_stat_card(self, title, value, icon, bg_color):
        card = QFrame()
        card.setFixedHeight(140)
        card.setMinimumWidth(160)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 20px;
                border: 1px solid transparent;
            }}
            QFrame:hover {{
                border: 1px solid #DDD;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(4)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 28px; background: transparent;")

        val_label = QLabel(value)
        val_label.setStyleSheet("font-size: 26px; font-weight: bold; color: #333; background: transparent; margin-top: 6px;")

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 13px; color: #777; background: transparent;")

        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(val_label)
        layout.addWidget(title_label)

        # Store label reference for updates
        card.val_label = val_label
        return card

    def create_settings_page(self):
        """Pomotroid 风格：左侧导航列表 + 右侧分页内容区"""
        page = QWidget()
        page.setObjectName("SettingsPage")
        outer = QHBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── 公共样式 ─────────────────────────────────────────────────────────
        icon_check_path = get_resource_path("resources/icon_check.svg").replace("\\", "/")
        _FONT_CSS = '"Segoe UI", "Microsoft YaHei", sans-serif'
        checkbox_style = f"""
            QCheckBox {{ font-size: 14px; color: #444; spacing: 8px; font-family: {_FONT_CSS}; }}
            QCheckBox::indicator {{ width: 20px; height: 20px; border-radius: 5px; border: 1.5px solid #CCC; background: #FFF; }}
            QCheckBox::indicator:checked {{ background-color: #1A1A1A; border-color: #1A1A1A; image: url('{icon_check_path}'); }}
        """

        # ── 左侧导航 ─────────────────────────────────────────────────────────
        nav_panel = QWidget()
        nav_panel.setObjectName("SettingsNavPanel")
        nav_panel.setFixedWidth(180)
        nav_panel.setStyleSheet("""
            QWidget#SettingsNavPanel {
                background-color: #F8F8F8;
                border-right: 1px solid #EEEEEE;
            }
        """)
        nav_layout = QVBoxLayout(nav_panel)
        nav_layout.setContentsMargins(0, 40, 0, 20)
        nav_layout.setSpacing(2)

        nav_items = ["计时器", "通知", "系统", "关于"]
        self._settings_nav_btns = []
        self._settings_stack = QStackedWidget()

        for i, label in enumerate(nav_items):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(44)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 0 24px;
                    font-size: 14px;
                    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                    color: #666;
                    background: transparent;
                    border: none;
                    border-left: 3px solid transparent;
                    font-weight: normal;
                }
                QPushButton:checked {
                    color: #1A1A1A;
                    font-weight: 600;
                    background-color: rgba(0,0,0,0.04);
                    border-left: 3px solid #1A1A1A;
                }
                QPushButton:hover:!checked {
                    background-color: rgba(0,0,0,0.03);
                    color: #333;
                }
            """)
            btn.clicked.connect(lambda _, idx=i: self._switch_settings_tab(idx))
            nav_layout.addWidget(btn)
            self._settings_nav_btns.append(btn)

        nav_layout.addStretch()
        outer.addWidget(nav_panel)

        # ── 右侧内容区 ───────────────────────────────────────────────────────
        outer.addWidget(self._settings_stack, 1)

        # ── 辅助：滚动容器 ───────────────────────────────────────────────────
        def make_scroll_page():
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setStyleSheet("QScrollArea { background: #FFFFFF; } QScrollBar:vertical { width: 6px; }")
            inner = QWidget()
            inner.setStyleSheet("background: transparent;")
            vbox = QVBoxLayout(inner)
            vbox.setContentsMargins(50, 50, 50, 50)
            vbox.setSpacing(20)
            scroll.setWidget(inner)
            return scroll, vbox

        _FONT = '"Segoe UI", "Microsoft YaHei", sans-serif'

        def make_section_title(text):
            lbl = QLabel(text)
            lbl.setStyleSheet(f"font-size: 11px; font-weight: 600; color: #999; letter-spacing: 1px; font-family: {_FONT};")
            return lbl

        def make_row_item(label_text, desc_text=""):
            """返回一个包含左侧文本+右侧控件槽位的 HBox"""
            row = QHBoxLayout()
            row.setSpacing(16)
            text_col = QVBoxLayout()
            text_col.setSpacing(2)
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"font-size: 14px; color: #222; font-weight: 500; font-family: {_FONT};")
            text_col.addWidget(lbl)
            if desc_text:
                desc = QLabel(desc_text)
                desc.setStyleSheet(f"font-size: 12px; color: #999; font-family: {_FONT};")
                text_col.addWidget(desc)
            row.addLayout(text_col, 1)
            return row

        def make_divider():
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setStyleSheet("background: #EEEEEE; border: none; max-height: 1px;")
            return line

        # ═══════════════════════════════════════════════════════════════════
        # 页1：计时器
        # ═══════════════════════════════════════════════════════════════════
        p1_scroll, p1 = make_scroll_page()

        p1.addWidget(make_section_title("时长"))
        # 专注时长
        r_work = make_row_item("专注", "每轮专注工作时长")
        self.work_mins_spin = NumberControl()
        self.work_mins_spin.setRange(1, 120)
        self.work_mins_spin.setSuffix(" 分钟")
        r_work.addWidget(self.work_mins_spin)
        p1.addLayout(r_work)

        p1.addWidget(make_divider())

        # 短休息时长
        r_break = make_row_item("短休息", "专注轮结束后的短暂休息")
        self.break_mins_spin = NumberControl()
        self.break_mins_spin.setRange(1, 60)
        self.break_mins_spin.setSuffix(" 分钟")
        r_break.addWidget(self.break_mins_spin)
        p1.addLayout(r_break)

        p1.addWidget(make_divider())

        # 长休息时长
        r_long_break = make_row_item("长休息", "每隔若干轮后的长休息时长")
        self.long_break_mins_spin = NumberControl()
        self.long_break_mins_spin.setRange(5, 60)
        self.long_break_mins_spin.setSuffix(" 分钟")
        r_long_break.addWidget(self.long_break_mins_spin)
        p1.addLayout(r_long_break)

        p1.addWidget(make_divider())

        # 每N轮长休息
        r_long_interval = make_row_item("长休息间隔", "每隔几轮专注后触发长休息")
        self.long_break_interval_spin = NumberControl()
        self.long_break_interval_spin.setRange(2, 10)
        self.long_break_interval_spin.setSuffix(" 轮")
        r_long_interval.addWidget(self.long_break_interval_spin)
        p1.addLayout(r_long_interval)

        p1.addSpacing(32)
        p1.addWidget(make_section_title("行为"))

        # 自动隐藏侧边栏
        r_autohide = make_row_item("自动隐藏侧边栏", "专注开始时折叠侧边栏")
        self.auto_hide_sidebar_toggle = QCheckBox()
        self.auto_hide_sidebar_toggle.setStyleSheet(checkbox_style)
        self.auto_hide_sidebar_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        r_autohide.addWidget(self.auto_hide_sidebar_toggle)
        p1.addLayout(r_autohide)

        p1.addStretch()

        self._settings_stack.addWidget(p1_scroll)

        # ═══════════════════════════════════════════════════════════════════
        # 页2：通知（提示音 + 滴答声）
        # ═══════════════════════════════════════════════════════════════════
        p2_scroll, p2 = make_scroll_page()

        p2.addWidget(make_section_title("结束提示音"))

        # 提示音总开关
        r_sound_on = make_row_item("开启提示音", "阶段结束时播放提示音")
        self.sound_toggle = QCheckBox()
        self.sound_toggle.setStyleSheet(checkbox_style)
        self.sound_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        r_sound_on.addWidget(self.sound_toggle)
        p2.addLayout(r_sound_on)

        p2.addSpacing(32)
        p2.addWidget(make_section_title("滴答声"))

        # 工作滴答声
        r_tick_work = make_row_item("工作时段", "专注期间播放滴答声")
        self.tick_work_toggle = QCheckBox()
        self.tick_work_toggle.setStyleSheet(checkbox_style)
        self.tick_work_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        # 勾选变化时立即同步到 timer
        self.tick_work_toggle.toggled.connect(
            lambda v: self.timer.set_tick_enabled(v, self.tick_break_toggle.isChecked())
        )
        r_tick_work.addWidget(self.tick_work_toggle)
        p2.addLayout(r_tick_work)

        p2.addWidget(make_divider())

        # 休息滴答声
        r_tick_break = make_row_item("休息时段", "休息期间播放滴答声")
        self.tick_break_toggle = QCheckBox()
        self.tick_break_toggle.setStyleSheet(checkbox_style)
        self.tick_break_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tick_break_toggle.toggled.connect(
            lambda v: self.timer.set_tick_enabled(self.tick_work_toggle.isChecked(), v)
        )
        r_tick_break.addWidget(self.tick_break_toggle)
        p2.addLayout(r_tick_break)

        p2.addStretch()

        self._settings_stack.addWidget(p2_scroll)

        # ═══════════════════════════════════════════════════════════════════
        # 页3：系统
        # ═══════════════════════════════════════════════════════════════════
        p3_scroll, p3 = make_scroll_page()
        p3.addWidget(make_section_title("系统"))

        r_theme_info = make_row_item("主题", "通过右上角按钮切换深色/浅色模式")
        p3.addLayout(r_theme_info)

        p3.addStretch()
        self._settings_stack.addWidget(p3_scroll)

        # ═══════════════════════════════════════════════════════════════════
        # 页4：关于
        # ═══════════════════════════════════════════════════════════════════
        p4_scroll, p4 = make_scroll_page()
        p4.addWidget(make_section_title("关于"))

        about_lbl = QLabel("FanqieClock · 番茄钟")
        about_lbl.setStyleSheet(f"font-size: 20px; font-weight: bold; color: #222; font-family: {_FONT};")
        p4.addWidget(about_lbl)

        author_lbl = QLabel("作者：饿梦")
        author_lbl.setStyleSheet(f"font-size: 14px; color: #777; margin-top: 4px; font-family: {_FONT};")
        p4.addWidget(author_lbl)

        p4.addSpacing(24)

        # 赞助
        sponsor_text = QLabel("创作不易，喜欢就请我喝杯咖啡吧 ☕\n无论是否赞助，感谢遇见你")
        sponsor_text.setStyleSheet(f"color: #888; font-size: 13px; line-height: 1.6; font-family: {_FONT};")
        p4.addWidget(sponsor_text)

        sponsor_btn = QPushButton("我要赞助 ❤️")
        sponsor_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sponsor_btn.setFixedWidth(130)
        sponsor_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFEBEE;
                color: #D32F2F;
                border: 1px solid #FFCDD2;
                border-radius: 12px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #FFCDD2; }
        """)
        sponsor_btn.clicked.connect(self.show_sponsor_dialog)
        p4.addWidget(sponsor_btn)
        p4.addStretch()
        self._settings_stack.addWidget(p4_scroll)

        # 默认显示第一个 tab
        self._switch_settings_tab(0)

        return page

    def _switch_settings_tab(self, index):
        """切换设置分页"""
        self._settings_stack.setCurrentIndex(index)
        for i, btn in enumerate(self._settings_nav_btns):
            btn.setChecked(i == index)


    def show_sponsor_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("感谢支持")
        dialog.setFixedSize(400, 300)
        layout = QVBoxLayout(dialog)
        
        msg = QLabel("感谢您的认可！❤️")
        msg.setStyleSheet("font-size: 20px; font-weight: bold; color: #333; margin-bottom: 10px;")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        qr_label = QLabel()
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_label.setFixedSize(250, 250)
        
        # Try to load image
        pixmap = QPixmap(get_resource_path("resources/赞赏码.jpg"))
        if not pixmap.isNull():
            qr_label.setPixmap(pixmap.scaled(250, 250, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            qr_label.setText("图片加载失败\n请检查 resources/赞赏码.jpg")
            qr_label.setStyleSheet("background: #F5F5F5; color: #AAA; border: 2px dashed #DDD; border-radius: 10px; font-size: 14px;")
        
        layout.addWidget(msg)
        layout.addWidget(qr_label, 0, Qt.AlignmentFlag.AlignCenter)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec()

    def create_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #F0F0F0; border: none; max-height: 1px;")
        return line

    def setup_connections(self):
        self.timer.tick.connect(self.update_timer_display)
        self.timer.mode_changed.connect(self.update_mode_display)
        self.timer.finished.connect(self.handle_timer_finished)
        self.timer.started.connect(self.update_play_pause_button)
        self.timer.paused.connect(self.update_play_pause_button)
        self.timer.abandoned.connect(self.update_play_pause_button)
        
        self.start_btn.clicked.connect(self.toggle_timer)
        # self.skip_btn removed/replaced by abandon_btn
        
        self.data_manager.save_error.connect(self.show_save_error)

        # ── 设置项实时自动保存（任何变动立即生效并持久化）────────────────────
        self.work_mins_spin.valueChanged.connect(self._auto_save_settings)
        self.break_mins_spin.valueChanged.connect(self._auto_save_settings)
        self.long_break_mins_spin.valueChanged.connect(self._auto_save_settings)
        self.long_break_interval_spin.valueChanged.connect(self._auto_save_settings)
        self.sound_toggle.toggled.connect(self._auto_save_settings)
        self.auto_hide_sidebar_toggle.toggled.connect(self._auto_save_settings)
        # tick toggles 在 create_settings_page 里已连接 set_tick_enabled，
        # 这里额外连持久化
        self.tick_work_toggle.toggled.connect(self._auto_save_settings)
        self.tick_break_toggle.toggled.connect(self._auto_save_settings)

    def show_save_error(self, message):
        QMessageBox.warning(self, "数据保存失败", f"无法保存数据，请检查磁盘空间或权限。\n错误信息: {message}")

    def load_saved_data(self):
        data = self.data_manager.data
        tasks = data.get("tasks", {})
        for key, items in tasks.items():
            if key in self.kanban_cols:
                self.kanban_cols[key].clear()
                for item_data in items:
                    # item_data is a dict now
                    self.kanban_cols[key].add_task_item(item_data)
        
        self.refresh_notes_table()
        self.refresh_stats()
        
        settings = data.get("settings", {})
        self.work_mins_spin.setValue(settings.get("work_mins", 25))
        self.break_mins_spin.setValue(settings.get("break_mins", 5))
        self.long_break_mins_spin.setValue(settings.get("long_break_mins", 15))
        self.long_break_interval_spin.setValue(settings.get("long_break_interval", 4))
        self.sound_toggle.setChecked(settings.get("sound_enabled", True))
        self.auto_hide_sidebar_toggle.setChecked(settings.get("auto_hide_sidebar", True))

        # 加载滴答声开关（默认开启）
        self.tick_work_toggle.setChecked(settings.get("tick_enabled_work", True))
        self.tick_break_toggle.setChecked(settings.get("tick_enabled_break", True))

        self.timer.set_durations(self.work_mins_spin.value(), self.break_mins_spin.value(), self.long_break_mins_spin.value())
        self.timer.set_long_break_interval(self.long_break_interval_spin.value())
        self.timer.set_sound_enabled(self.sound_toggle.isChecked())
        self.timer.set_sound_paths(
            work=settings.get("sound_work"),
            short_break=settings.get("sound_break"),
            long_break=settings.get("sound_long_break")
        )
        self.timer.set_tick_enabled(
            work_tick=settings.get("tick_enabled_work", True),
            break_tick=settings.get("tick_enabled_break", True)
        )
        
        # Apply saved theme preference
        theme = settings.get("theme", "light")
        self.apply_theme(theme)
        if hasattr(self, 'theme_btn'):
            self.theme_btn.blockSignals(True)
            self.theme_btn.setChecked(theme == "dark")
            self.theme_btn.blockSignals(False)

    def switch_page(self, index):
        if self.content_stack.currentIndex() == index: return
        
        self.content_stack.setCurrentIndex(index)
        
        # Update active state of nav buttons    
        for i, btn in enumerate(self.nav_btns):
            btn.setChecked(i == index)
            btn.setProperty("active", "true" if i == index else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        
        if index == 3: self.refresh_stats()

    def eventFilter(self, obj, event):
        if obj == self.sidebar:
            if event.type() == QEvent.Type.Enter:
                self.sidebar_hide_timer.stop() # Cancel pending hide
                if self.sidebar.width() < 85:
                    self.animate_sidebar(85)
            elif event.type() == QEvent.Type.Leave:
                # Determine if we should auto-hide based on state
                should_hide = False
                
                # Condition 1: Timer is running and Auto-Hide preference is On
                if self.timer.is_running and hasattr(self, 'auto_hide_sidebar_toggle') and self.auto_hide_sidebar_toggle.isChecked():
                    should_hide = True
                # Condition 2: Window is narrow (Responsive mode)
                elif self.width() < 1200:
                    should_hide = True
                    
                if should_hide:
                    self.sidebar_hide_timer.start() # Schedule hide check
                    
        return super().eventFilter(obj, event)

    def check_sidebar_hover(self):
        # Polling for "Hot Zone" trigger
        # Allow expanding if sidebar is collapsed, regardless of timer state
        
        # If sidebar is already expanded, stop the polling timer — no need to poll
        if self.sidebar.width() > 50:
            self.sidebar_hover_timer.stop()
            return
            
        cursor_pos = QCursor.pos()
        local_pos = self.mapFromGlobal(cursor_pos)
        
        # Check if cursor is within window bounds and left 50px
        if self.rect().contains(local_pos):
            if local_pos.x() <= 50: # Wider trigger zone
                self.sidebar_hide_timer.stop()
                self.animate_sidebar(85)

    def check_and_hide_sidebar(self):
        # Verify if cursor is still outside sidebar geometry
        cursor_pos = QCursor.pos()
        mapped_pos = self.sidebar.mapFromGlobal(cursor_pos)
        if not self.sidebar.rect().contains(mapped_pos):
            self.animate_sidebar(0)

    def toggle_sidebar(self):
        # Manual toggle
        width = self.sidebar.width()
        # If collapsed (<=0), expand to 85. If expanded (>0), collapse to 0.
        target = 85 if width <= 0 else 0
        self.animate_sidebar(target)
        
        # Save manual state
        state = "expanded" if target == 85 else "collapsed"
        settings = self.data_manager.data.get("settings", {})
        settings["sidebar_manual_state"] = state
        self.data_manager.update_settings(settings)

    def animate_sidebar(self, target_width):
        # Check if currently animating
        is_animating = hasattr(self, 'anim_group') and self.anim_group.state() == QParallelAnimationGroup.State.Running
        if is_animating:
            if self.anim_min.endValue() == target_width:
                return # Already animating to target
            self.anim_group.stop() # Stop previous animation
            
        width = self.sidebar.width()
        if width == target_width: return
        
        # Animate minimumWidth
        self.anim_min = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self.anim_min.setDuration(300) 
        self.anim_min.setStartValue(width)
        self.anim_min.setEndValue(target_width)
        self.anim_min.setEasingCurve(QEasingCurve.Type.OutCubic) 
        
        # Animate maximumWidth
        self.anim_max = QPropertyAnimation(self.sidebar, b"maximumWidth")
        self.anim_max.setDuration(300)
        self.anim_max.setStartValue(width)
        self.anim_max.setEndValue(target_width)
        self.anim_max.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Group animations
        self.anim_group = QParallelAnimationGroup()
        self.anim_group.addAnimation(self.anim_min)
        self.anim_group.addAnimation(self.anim_max)
        # When sidebar collapses back to 0, restart hover polling.
        # Use a dedicated slot to avoid lambda accumulation on repeated calls.
        if target_width == 0:
            self.anim_group.finished.connect(self._on_sidebar_collapsed)
        self.anim_group.start()

    def _on_sidebar_collapsed(self):
        """Called once when sidebar collapse animation finishes."""
        self.sidebar_hover_timer.start()

    def start_focus_on_task(self, task_data):
        self.switch_page(0) # Switch to Timer page
        self.current_task = task_data
        self.mode_label.setText(f"正在专注：{task_data.get('content', '未知任务')}")
        if not self.timer.is_running:
            self.toggle_timer()

    def stop_timer(self):
        self.timer.reset()
        if self.auto_hide_sidebar_toggle.isChecked():
            self.animate_sidebar(85)

    def toggle_timer(self):
        if self.timer.is_running:
            reply = QMessageBox.question(
                self, '放弃当前番茄钟？',
                '根据番茄工作法，番茄钟一旦开始就不应暂停。确定要放弃当前这一组计时吗？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.timer.abandon()
                if self.auto_hide_sidebar_toggle.isChecked():
                    self.animate_sidebar(85)
        else:
            self.timer.start()
            if self.auto_hide_sidebar_toggle.isChecked():
                self.animate_sidebar(0)

    def update_play_pause_button(self):
        if self.timer.is_running:
            self.start_btn.setIcon(QIcon(get_resource_path("resources/icon_abandon.svg")))
            self.start_btn.setToolTip("放弃专注")
        else:
            self.start_btn.setIcon(QIcon(get_resource_path("resources/icon_play.svg")))
            self.start_btn.setToolTip("开始专注")

    def update_timer_display(self, seconds):
        mins, secs = divmod(seconds, 60)
        self.timer_label.setText(f"{mins:02d}:{secs:02d}")
        
        # Update progress line and circular progress bar
        if self.timer.current_mode == 'work':
            total_seconds = self.timer.work_seconds
        elif self.timer.current_mode == 'long_break':
            total_seconds = self.timer.long_break_seconds
        else:
            total_seconds = self.timer.break_seconds
            
        self.progress_line.setMaximum(total_seconds)
        self.progress_line.setValue(total_seconds - seconds)
        
        # 修复：同步更新环形进度条（之前一直是满格）
        self.progress_bar.set_max_value(total_seconds)
        self.progress_bar.value = total_seconds - seconds

    def update_mode_display(self, mode):
        if mode == 'work':
            self.mode_label.setText("正在专注")
            self.work_info.setProperty("class", "InfoLabelActive")
            self.break_info.setProperty("class", "InfoLabel")
            self.display_stack.setCurrentWidget(self.timer_label)
        elif mode == 'long_break':
            self.mode_label.setText("正在长休息")
            self.work_info.setProperty("class", "InfoLabel")
            self.break_info.setProperty("class", "InfoLabelActive")
            # Update break info text for long break
            mins = self.timer.long_break_seconds // 60
            self.break_info.setText(f"长休 {mins:02d}:00")
            self.display_stack.setCurrentWidget(self.timer_label) # Show timer, not overlay
        else: # break
            self.mode_label.setText("正在休息")
            self.work_info.setProperty("class", "InfoLabel")
            self.break_info.setProperty("class", "InfoLabelActive")
            mins = self.timer.break_seconds // 60
            self.break_info.setText(f"短休 {mins:02d}:00")
            self.display_stack.setCurrentWidget(self.timer_label)
        
        # Update play/pause button icon based on timer state
        self.update_play_pause_button()
            
        # Ensure work info text is correct
        work_mins = self.timer.work_seconds // 60
        self.work_info.setText(f"工作 {work_mins:02d}:00")
        
        # Refresh style to apply new property classes
        self.work_info.style().unpolish(self.work_info)
        self.work_info.style().polish(self.work_info)
        self.break_info.style().unpolish(self.break_info)
        self.break_info.style().polish(self.break_info)

    def handle_timer_finished(self):
        if self.auto_hide_sidebar_toggle.isChecked():
            self.animate_sidebar(85)
            
        if self.timer.current_mode == 'work':
            if hasattr(self, 'current_task') and self.current_task:
                self.update_task_pomo_count(self.current_task['id'])
                
            self.data_manager.record_session(self.work_mins_spin.value())
            self.refresh_stats()

    def update_task_pomo_count(self, task_id):
        found = False
        for key, col in self.kanban_cols.items():
            for i in range(col.count()):
                item = col.item(i)
                data = item.data(Qt.ItemDataRole.UserRole)
                if data and data.get('id') == task_id:
                    data['pomodoros'] = data.get('pomodoros', 0) + 1
                    item.setData(Qt.ItemDataRole.UserRole, data)
                    # Refresh widget display
                    widget = col.itemWidget(item)
                    if widget:
                        widget.pomo_label.setText(f"🍅 {data['pomodoros']}")
                        # widget.task_data is a reference, but we updated 'data' dict.
                        # Since widget.task_data = task_data in constructor, they might be same object if we passed it.
                        # But QListWidgetItem copies data? No, python objects are refs.
                        # However, let's be safe and update widget.task_data
                        widget.task_data = data 
                    found = True
                    break
            if found: break
        if found:
            self.save_kanban_state()

    def add_kanban_task(self, key, input_field):
        text = input_field.text().strip()
        if text:
            task_data = {
                "id": None, # Will be generated by DataManager
                "content": text,
                "pomodoros": 0,
                "created_at": QDate.currentDate().toString(Qt.DateFormat.ISODate)
            }
            # Ensure DataManager processes it to add UUID if needed, but here we construct it.
            # Actually DataManager._ensure_task_obj handles strings, but we can pass dict.
            # Let's let DataManager generate ID if missing.
            # For now, generate ID here or rely on list reload. 
            # Better to be explicit.
            task_data["id"] = str(uuid.uuid4())
            
            self.kanban_cols[key].add_task_item(task_data)
            input_field.clear()
            self.save_kanban_state()

    def save_kanban_state(self):
        tasks_dict = {}
        for key, col in self.kanban_cols.items():
            tasks = []
            for i in range(col.count()):
                item = col.item(i)
                task_data = item.data(Qt.ItemDataRole.UserRole)
                if task_data:
                    tasks.append(task_data)
            tasks_dict[key] = tasks
        self.data_manager.update_tasks(tasks_dict)

    # Notes Logic
    def refresh_notes_table(self, filter_text=""):
        notes = self.data_manager.data.get("notes", [])
        self.notes_table.setRowCount(0)
        
        for i, note in enumerate(notes):
            # Filtering logic
            if filter_text and filter_text.lower() not in note['title'].lower() and filter_text.lower() not in note['content'].lower():
                continue
                
            self.notes_table.insertRow(self.notes_table.rowCount())
            row = self.notes_table.rowCount() - 1
            
            # Title item
            title_item = QTableWidgetItem(note['title'])
            title_item.setData(Qt.ItemDataRole.UserRole, i) # Store original index
            self.notes_table.setItem(row, 0, title_item)
            
            # Summary item
            content_summary = note['content'][:60].replace("\n", " ")
            if len(note['content']) > 60: content_summary += "..."
            self.notes_table.setItem(row, 1, QTableWidgetItem(content_summary))

    def show_note_context_menu(self, pos):
        item = self.notes_table.itemAt(pos)
        if item:
            row = item.row()
            # Select the row first
            self.notes_table.selectRow(row)
            
            # Create menu
            menu = QMenu(self.notes_table)
            
            delete_action = QAction("删除笔记", self)
            delete_action.setIcon(QIcon(get_resource_path("resources/icon_delete_new.svg")))
            # Use closure to capture row index, but delete_note expects logic index
            # The row index in table might differ from data list if filtered?
            # Yes, filter logic just skips insertion, so table rows match displayed items.
            # But `delete_note` uses `self.data_manager.data.get("notes", []).pop(idx)`
            # This implies `idx` is index in the SOURCE list.
            
            # Wait, refresh_notes_table:
            # title_item.setData(Qt.ItemDataRole.UserRole, i) # Store original index
            
            # So we must retrieve the original index from the item!
            title_item = self.notes_table.item(row, 0)
            original_index = title_item.data(Qt.ItemDataRole.UserRole)
            
            delete_action.triggered.connect(lambda: self.delete_note(original_index))
            
            menu.addAction(delete_action)
            menu.exec(self.notes_table.mapToGlobal(pos))

    def show_note_dialog(self, original_index=None):
        # Handle signal sending boolean (False) when clicked
        if isinstance(original_index, bool):
            original_index = None
            
        notes = self.data_manager.data.get("notes", [])
        note_data = notes[original_index] if original_index is not None else None
        
        dialog = QDialog(self)
        dialog.setWindowTitle("笔记编辑" if note_data else "新建笔记")
        dialog.setMinimumSize(600, 500)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        
        title_edit = QLineEdit()
        title_edit.setPlaceholderText("💡 这里写标题...")
        title_edit.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        
        content_edit = QTextEdit()
        content_edit.setPlaceholderText("✍️ 记录此刻的想法、灵感或复盘...")
        content_edit.setStyleSheet("font-size: 15px; line-height: 1.5;")
        
        if note_data:
            title_edit.setText(note_data['title'])
            content_edit.setPlainText(note_data['content'])
            
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        save_btn = QPushButton("保存笔记")
        save_btn.setObjectName("PrimaryButton")
        save_btn.setMinimumWidth(120)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        
        def save():
            new_note = {
                "title": title_edit.text() or "未命名笔记",
                "content": content_edit.toPlainText(),
                "date": QDate.currentDate().toString(Qt.DateFormat.ISODate)
            }
            if original_index is not None:
                notes[original_index] = new_note
            else:
                notes.insert(0, new_note)
            
            self.data_manager.update_notes(notes)
            self.refresh_notes_table()
            dialog.accept()
            
        save_btn.clicked.connect(save)
        cancel_btn.clicked.connect(dialog.reject)
        
        layout.addWidget(QLabel("标题"))
        layout.addWidget(title_edit)
        layout.addWidget(QLabel("正文"))
        layout.addWidget(content_edit)
        layout.addLayout(btn_layout)
        dialog.exec()

    def edit_note(self, item):
        # Get the title item of the row to retrieve the original index
        row = item.row()
        title_item = self.notes_table.item(row, 0)
        original_index = title_item.data(Qt.ItemDataRole.UserRole)
        self.show_note_dialog(original_index)

    def delete_note(self, idx):
        # Confirmation Dialog
        reply = QMessageBox.question(self, '确认删除', 
                                     '您确定要删除这条笔记吗？此操作无法撤销。',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)
                                     
        if reply == QMessageBox.StandardButton.Yes:
            notes = self.data_manager.data.get("notes", [])
            if 0 <= idx < len(notes):
                notes.pop(idx)
                self.data_manager.update_notes(notes)
                self.refresh_notes_table()

    def filter_notes(self):
        self.refresh_notes_table(self.note_search.text())

    # Stats Logic
    def refresh_stats(self):
        stats = self.data_manager.data.get("stats", {})
        
        # Summary
        self.stat_pomos.val_label.setText(str(stats.get("total_pomodoros", 0)))
        
        total_mins = stats.get("total_minutes", 0)
        if total_mins < 60:
            time_str = f"{total_mins} 分钟"
        else:
            time_str = f"{total_mins/60:.1f} 小时"
        self.stat_time.val_label.setText(time_str)
        
        self.stat_days.val_label.setText(str(stats.get("total_days", 0)))
        
        # Interruptions
        interrupts = self.data_manager.data.get("interruptions", [])
        self.stat_interrupts.val_label.setText(str(len(interrupts)))
        
        # Today's detail
        today = QDate.currentDate().toString(Qt.DateFormat.ISODate)
        history = stats.get("history", {})
        today_data = history.get(today, {"count": 0, "minutes": 0})
        
        # Count today's interruptions
        today_interrupts = sum(1 for i in interrupts if i['timestamp'].startswith(today))
        
        self.today_stat_label.setText(f"🔥 今日专注：{today_data['count']} 个番茄 ({today_data['minutes']} 分钟) | ⚡ 打断：{today_interrupts} 次")
        
        # 刷新图表
        if hasattr(self, 'bar_chart'):
            self.bar_chart.set_data(history)
        if hasattr(self, 'heatmap'):
            self.heatmap.set_data(history)

        # Update history list
        self.history_list.clear()
        sorted_dates = sorted(history.keys(), reverse=True)[:7] # Show last 7 days
        for date_str in sorted_dates:
            day_data = history[date_str]
            item_text = f"📅 {date_str}   |   🍅 {day_data['count']} 个番茄   |   ⏳ {day_data['minutes']} 分钟"
            self.history_list.addItem(item_text)

    def export_stats_pdf(self):
        filename, _ = QFileDialog.getSaveFileName(self, "导出专注报告", "FocusReport.pdf", "PDF Files (*.pdf)")
        if not filename:
            return
            
        stats = self.data_manager.data.get("stats", {})
        interrupts = self.data_manager.data.get("interruptions", [])
        
        # Calculate summary
        total_pomos = stats.get("total_pomodoros", 0)
        total_mins = stats.get("total_minutes", 0)
        total_days = stats.get("total_days", 0)
        
        # Generate HTML
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Microsoft YaHei', sans-serif; padding: 40px; }}
                h1 {{ color: #333; border-bottom: 2px solid #000; padding-bottom: 10px; }}
                .summary {{ display: flex; justify-content: space-between; margin: 30px 0; }}
                .card {{ background: #F9F9F9; padding: 20px; border-radius: 10px; text-align: center; width: 20%; }}
                .value {{ font-size: 24px; font-weight: bold; color: #000; display: block; }}
                .label {{ color: #666; font-size: 14px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ border: 1px solid #EEE; padding: 12px; text-align: left; }}
                th {{ background-color: #F0F0F0; }}
            </style>
        </head>
        <body>
            <h1>🍅 番茄钟 专注报告</h1>
            <p>生成日期: {QDate.currentDate().toString(Qt.DateFormat.ISODate)}</p>
            
            <h3>数据概览</h3>
            <table style="border: none;">
                <tr style="border: none;">
                    <td style="border: none; background: #FFF0F0; padding: 20px; text-align: center;">
                        <span class="value">{total_pomos}</span><br>
                        <span class="label">累计番茄</span>
                    </td>
                    <td style="border: none; background: #F0F8FF; padding: 20px; text-align: center;">
                        <span class="value">{total_mins}</span><br>
                        <span class="label">专注分钟</span>
                    </td>
                    <td style="border: none; background: #F5F5F5; padding: 20px; text-align: center;">
                        <span class="value">{total_days}</span><br>
                        <span class="label">累计天数</span>
                    </td>
                    <td style="border: none; background: #FFF8E1; padding: 20px; text-align: center;">
                        <span class="value">{len(interrupts)}</span><br>
                        <span class="label">打断次数</span>
                    </td>
                </tr>
            </table>
            
            <h3>最近7天记录</h3>
            <table>
                <tr>
                    <th>日期</th>
                    <th>番茄数</th>
                    <th>专注时长 (分钟)</th>
                </tr>
        """
        
        history = stats.get("history", {})
        sorted_dates = sorted(history.keys(), reverse=True)[:7]
        for date_str in sorted_dates:
            day_data = history[date_str]
            html += f"""
                <tr>
                    <td>{date_str}</td>
                    <td>{day_data['count']}</td>
                    <td>{day_data['minutes']}</td>
                </tr>
            """
            
        html += """
            </table>
        </body>
        </html>
        """
        
        doc = QTextDocument()
        doc.setHtml(html)
        
        writer = QPdfWriter(filename)
        writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        writer.setResolution(300) # 300 DPI for better quality
        
        doc.print(writer)
        
        QMessageBox.information(self, "导出成功", f"报告已保存至:\n{filename}")

    def _auto_save_settings(self, *_args):
        """任意设置项变动时自动调用，立即同步到 timer 并持久化。"""
        w = self.work_mins_spin.value()
        b = self.break_mins_spin.value()
        lb = self.long_break_mins_spin.value()
        lb_interval = self.long_break_interval_spin.value()
        sound_enabled = self.sound_toggle.isChecked()
        auto_hide = self.auto_hide_sidebar_toggle.isChecked()

        # 读取当前音效路径（从已存储的设置里取，UI 只显示文件名）
        current_settings = self.data_manager.data.get("settings", {})
        sound_work = current_settings.get("sound_work")
        sound_break = current_settings.get("sound_break")
        sound_long_break = current_settings.get("sound_long_break")

        # Preserve current theme setting
        current_theme = current_settings.get("theme", "light")
        settings = {
            "work_mins": w,
            "break_mins": b,
            "long_break_mins": lb,
            "long_break_interval": lb_interval,
            "sound_enabled": sound_enabled,
            "sound_work": sound_work,
            "sound_break": sound_break,
            "sound_long_break": sound_long_break,
            "tick_enabled_work": self.tick_work_toggle.isChecked(),
            "tick_enabled_break": self.tick_break_toggle.isChecked(),
            "auto_hide_sidebar": auto_hide,
            "theme": current_theme
        }
        self.data_manager.update_settings(settings)
        self.timer.set_durations(w, b, lb)
        self.timer.set_long_break_interval(lb_interval)
        self.timer.set_sound_enabled(sound_enabled)
        self.timer.set_sound_paths(
            work=sound_work,
            short_break=sound_break,
            long_break=sound_long_break
        )
        self.timer.set_tick_enabled(
            work_tick=self.tick_work_toggle.isChecked(),
            break_tick=self.tick_break_toggle.isChecked()
        )

    def on_theme_toggled(self, checked):
        theme = "dark" if checked else "light"
        self.apply_theme(theme)
        self.data_manager.update_settings({"theme": theme})

    def apply_theme(self, theme):
        app = QApplication.instance()
        if theme == "dark":
            style_path = get_resource_path(os.path.join("styles", "style_dark.qss"))
            if os.path.exists(style_path):
                with open(style_path, "r", encoding="utf-8") as f:
                    app.setStyleSheet(f.read())
            if hasattr(self, "timer_label"):
                self.timer_label.setStyleSheet("font-size: 96px; font-weight: bold; color: #E6E6E6; font-family: 'Segoe UI', sans-serif; background: transparent;")
            if hasattr(self, "progress_bar"):
                self.progress_bar.set_color("#E6E6E6")
                self.progress_bar.set_bg_color("#2A2A2A")
            if hasattr(self, "progress_line"):
                self.progress_line.setStyleSheet("""
                    QProgressBar {
                        background-color: #1E1E1E;
                        border: none;
                        border-radius: 2px;
                    }
                    QProgressBar::chunk {
                        background-color: #CFCFCF;
                        border-radius: 2px;
                    }
                """)
        else:
            style_path = get_resource_path(os.path.join("styles", "style.qss"))
            if os.path.exists(style_path):
                with open(style_path, "r", encoding="utf-8") as f:
                    app.setStyleSheet(f.read())
            if hasattr(self, "timer_label"):
                self.timer_label.setStyleSheet("font-size: 96px; font-weight: bold; color: #1A1A1A; font-family: 'Segoe UI', sans-serif; background: transparent;")
            if hasattr(self, "progress_bar"):
                self.progress_bar.set_color("#000000")
                self.progress_bar.set_bg_color("#F0F0F0")
            if hasattr(self, "progress_line"):
                self.progress_line.setStyleSheet("""
                    QProgressBar {
                        background-color: #F0F0F0;
                        border: none;
                        border-radius: 2px;
                    }
                    QProgressBar::chunk {
                        background-color: #000000;
                        border-radius: 2px;
                    }
                """)
