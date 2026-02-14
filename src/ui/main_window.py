from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QStackedWidget, QTextEdit, 
                             QLineEdit, QListWidget, QFrame, QListWidgetItem,
                             QAbstractItemView, QDialog, QFormLayout, QSpinBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QGraphicsOpacityEffect, QProgressBar, QSizePolicy,
                             QCheckBox, QGridLayout, QMessageBox, QFileDialog, QMenu)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve, QDate, QEvent, QParallelAnimationGroup, QLocale, QSizeF, QTimer, QPoint
from PyQt6.QtGui import QColor, QFont, QIcon, QTextDocument, QPageSize, QPdfWriter, QCursor, QPixmap
from logic.timer import PomodoroTimer
from logic.data_manager import DataManager
from logic.quote_worker import QuoteWorker
from ui.widgets import CircularProgressBar, KanbanItemWidget, KanbanList, LongBreakOverlay, SmoothButton, NumberControl
import sys, os

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

    def __init__(self, timer: PomodoroTimer):
        super().__init__()
        self.timer = timer
        self.data_manager = DataManager()
        self.current_task = None
        self.init_ui()
        self.load_saved_data()
        self.setup_connections()
        
        # Fetch Daily Quote
        self.quote_worker = QuoteWorker()
        self.quote_worker.quote_fetched.connect(self.update_daily_quote)
        self.quote_worker.start()

    def update_daily_quote(self, content, author):
        if hasattr(self, 'quote_label') and hasattr(self, 'quote_author'):
            self.quote_label.setText(content)
            self.quote_author.setText(author)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            if self.windowState() & Qt.WindowState.WindowMinimized:
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, self.switch_to_compact.emit)
        super().changeEvent(event)

    def closeEvent(self, event):
        # If the event is spontaneous (e.g., user clicked 'X'), minimize to tray
        if event.spontaneous():
            event.ignore()
            self.hide()
        else:
            # If triggered by app.quit(), let it close
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
        self.sidebar_hover_timer = QTimer()
        self.sidebar_hover_timer.setInterval(50) # Check every 50ms
        self.sidebar_hover_timer.timeout.connect(self.check_sidebar_hover)
        self.sidebar_hover_timer.start() # Always run, check logic inside
        
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
        if not self.timer.is_running:
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
                self._last_compact_mode = is_compact_width
                
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
        self.progress_bar.show()
        
        # Overlay Timer Label
        self.timer_label = QLabel("25:00")
        self.timer_label.setObjectName("TimerLabel")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet("font-size: 96px; font-weight: bold; color: #1A1A1A; font-family: 'Segoe UI', sans-serif; background: transparent;")
        
        self.progress_bar.layout.addWidget(self.timer_label)
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
        controls_layout.setSpacing(40)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Stop Button
        self.stop_btn = SmoothButton()
        self.stop_btn.setIcon(QIcon(get_resource_path("resources/icon_stop.svg")))
        self.stop_btn.setIconSize(QSize(24, 24))
        self.stop_btn.setFixedSize(50, 50)
        # Use methods instead of property for SmoothButton
        self.stop_btn.set_colors("#000000", "#333333", "#555555")
        self.stop_btn.set_border_radius(25)
        self.stop_btn.setToolTip("停止 / 重置")
        self.stop_btn.clicked.connect(self.stop_timer)
        
        # Play/Pause Button
        self.start_btn = SmoothButton()
        self.start_btn.setIcon(QIcon(get_resource_path("resources/icon_play.svg")))
        self.start_btn.setIconSize(QSize(32, 32))
        self.start_btn.setFixedSize(72, 72)
        # Main button style
        self.start_btn.set_colors("#000000", "#333333", "#555555")
        self.start_btn.set_border_radius(36)
        self.start_btn.setToolTip("开始 / 暂停")
        
        # Abandon Button
        self.abandon_btn = SmoothButton()
        self.abandon_btn.setIcon(QIcon(get_resource_path("resources/icon_abandon.svg")))
        self.abandon_btn.setIconSize(QSize(24, 24))
        self.abandon_btn.setFixedSize(50, 50)
        self.abandon_btn.set_colors("#000000", "#333333", "#555555")
        self.abandon_btn.set_border_radius(25)
        self.abandon_btn.setToolTip("放弃当前番茄")
        self.abandon_btn.clicked.connect(self.abandon_timer)
        
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addWidget(self.start_btn)
        controls_layout.addWidget(self.abandon_btn)
        
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
        from PyQt6.QtCore import QTimer
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
        self.notes_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
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
        page = QWidget()
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
        layout.addSpacing(40)
        
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
        
        return page

    def create_stat_card(self, title, value, icon, bg_color):
        card = QFrame()
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
        layout.setContentsMargins(25, 25, 25, 25)
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 32px; background: transparent;")
        
        val_label = QLabel(value)
        val_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #333; background: transparent; margin-top: 10px;")
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 14px; color: #777; background: transparent;")
        
        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(val_label)
        layout.addWidget(title_label)
        
        # Store label reference for updates
        card.val_label = val_label
        return card

    def create_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(100, 60, 100, 60)
        
        title = QLabel("设置")
        title.setProperty("class", "KanbanTitle")
        title.setStyleSheet("font-size: 28px; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # Settings Container
        settings_container = QWidget()
        settings_container.setObjectName("SettingsContainer")
        settings_container.setStyleSheet("""
            #SettingsContainer {
                background-color: #FFFFFF;
                border: 1px solid #EEEEEE;
                border-radius: 20px;
            }
        """)
        
        # Use GridLayout for better alignment
        container_layout = QGridLayout(settings_container)
        container_layout.setContentsMargins(50, 50, 50, 50)
        container_layout.setVerticalSpacing(30)
        container_layout.setHorizontalSpacing(40)
        
        # Row 1: Work Duration
        work_label = QLabel("专注时长")
        work_label.setStyleSheet("font-size: 16px; color: #333; font-weight: bold;")
        self.work_mins_spin = NumberControl()
        self.work_mins_spin.setRange(1, 120)
        self.work_mins_spin.setSuffix(" 分钟")
        
        container_layout.addWidget(work_label, 0, 0)
        container_layout.addWidget(self.work_mins_spin, 0, 1, Qt.AlignmentFlag.AlignLeft)
        
        # Row 2: Break Duration
        break_label = QLabel("休息时长")
        break_label.setStyleSheet("font-size: 16px; color: #333; font-weight: bold;")
        self.break_mins_spin = NumberControl()
        self.break_mins_spin.setRange(1, 60)
        self.break_mins_spin.setSuffix(" 分钟")
        
        container_layout.addWidget(break_label, 1, 0)
        container_layout.addWidget(self.break_mins_spin, 1, 1, Qt.AlignmentFlag.AlignLeft)
        
        # Row 3: Sound Toggle
        sound_label = QLabel("提示音")
        sound_label.setStyleSheet("font-size: 16px; color: #333; font-weight: bold;")
        self.sound_toggle = QCheckBox("开启结束提示音")
        icon_check_path = get_resource_path("resources/icon_check.svg").replace("\\", "/")
        self.sound_toggle.setStyleSheet(f"""
            QCheckBox {{ font-size: 15px; color: #555; spacing: 8px; }}
            QCheckBox::indicator {{ width: 22px; height: 22px; border-radius: 6px; border: 1px solid #CCC; }}
            QCheckBox::indicator:checked {{ background-color: #000000; border-color: #000000; image: url('{icon_check_path}'); }}
        """)
        self.sound_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        
        container_layout.addWidget(sound_label, 2, 0)
        container_layout.addWidget(self.sound_toggle, 2, 1, Qt.AlignmentFlag.AlignLeft)
        
        # Row 4: Auto-hide Sidebar Toggle
        sidebar_behavior_label = QLabel("行为")
        sidebar_behavior_label.setStyleSheet("font-size: 16px; color: #333; font-weight: bold;")
        self.auto_hide_sidebar_toggle = QCheckBox("番茄钟开始时自动隐藏侧边栏")
        self.auto_hide_sidebar_toggle.setStyleSheet(f"""
            QCheckBox {{ font-size: 15px; color: #555; spacing: 8px; }}
            QCheckBox::indicator {{ width: 22px; height: 22px; border-radius: 6px; border: 1px solid #CCC; }}
            QCheckBox::indicator:checked {{ background-color: #000000; border-color: #000000; image: url('{icon_check_path}'); }}
        """)
        self.auto_hide_sidebar_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        
        container_layout.addWidget(sidebar_behavior_label, 3, 0)
        container_layout.addWidget(self.auto_hide_sidebar_toggle, 3, 1, Qt.AlignmentFlag.AlignLeft)
        
        # Add column stretch to push everything to the left
        container_layout.setColumnStretch(2, 1)

        layout.addWidget(settings_container)
        layout.addSpacing(30)
        
        save_btn = QPushButton("保存设置")
        save_btn.setObjectName("PrimaryButton")
        save_btn.setFixedSize(200, 50)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.save_settings)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        # Sponsorship Section
        sponsor_container = QWidget()
        sponsor_layout = QVBoxLayout(sponsor_container)
        sponsor_layout.setContentsMargins(0, 20, 0, 20)
        sponsor_layout.setSpacing(10)
        
        sponsor_text = QLabel("创作不易，喜欢就请我喝杯咖啡吧~ ☕\n--无论是否赞助，感谢遇见你")
        sponsor_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sponsor_text.setStyleSheet("color: #888; font-size: 14px; font-style: italic;")
        
        sponsor_btn = QPushButton("我要赞助")
        sponsor_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sponsor_btn.setFixedWidth(120)
        sponsor_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFEBEE;
                color: #D32F2F;
                border: 1px solid #FFCDD2;
                border-radius: 15px;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FFCDD2;
            }
        """)
        sponsor_btn.clicked.connect(self.show_sponsor_dialog)
        
        sponsor_layout.addWidget(sponsor_text)
        sponsor_layout.addWidget(sponsor_btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(sponsor_container)
        
        # Author Info
        author_label = QLabel("作者：饿梦")
        author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        author_label.setStyleSheet("color: #999; font-size: 14px; margin-top: 10px; font-weight: bold;")
        layout.addWidget(author_label)
        
        layout.addStretch()
        return page

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
        
        self.start_btn.clicked.connect(self.toggle_timer)
        # self.skip_btn removed/replaced by abandon_btn
        
        self.data_manager.save_error.connect(self.show_save_error)

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
        self.sound_toggle.setChecked(settings.get("sound_enabled", True))
        self.auto_hide_sidebar_toggle.setChecked(settings.get("auto_hide_sidebar", True))
        
        self.timer.set_durations(self.work_mins_spin.value(), self.break_mins_spin.value())
        self.timer.set_sound_enabled(self.sound_toggle.isChecked())

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
        
        # Check if sidebar is already expanded (or expanding)
        if self.sidebar.width() > 50:
            return # Already expanded, let Leave event handle hide
            
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
        self.anim_group.start()

    def start_focus_on_task(self, task_data):
        self.switch_page(0) # Switch to Timer page
        self.current_task = task_data
        self.mode_label.setText(f"正在专注：{task_data.get('content', '未知任务')}")
        if not self.timer.is_running:
            self.toggle_timer()

    def stop_timer(self):
        self.timer.reset()
        self.start_btn.setIcon(QIcon(get_resource_path("resources/icon_play.svg"))) # Reset start button icon
        if self.auto_hide_sidebar_toggle.isChecked():
            self.animate_sidebar(85)

    def toggle_timer(self):
        if self.timer.is_running:
            self.timer.pause()
            self.start_btn.setIcon(QIcon(get_resource_path("resources/icon_play.svg")))
        else:
            self.timer.start()
            self.start_btn.setIcon(QIcon(get_resource_path("resources/icon_pause.svg")))
            if self.auto_hide_sidebar_toggle.isChecked():
                self.animate_sidebar(0)

    def update_timer_display(self, seconds):
        mins, secs = divmod(seconds, 60)
        self.timer_label.setText(f"{mins:02d}:{secs:02d}")
        
        # Update progress line
        if self.timer.current_mode == 'work':
            total_seconds = self.timer.work_seconds
        elif self.timer.current_mode == 'long_break':
            total_seconds = self.timer.long_break_seconds
        else:
            total_seconds = self.timer.break_seconds
            
        self.progress_line.setMaximum(total_seconds)
        self.progress_line.setValue(total_seconds - seconds)

    def update_mode_display(self, mode):
        if mode == 'work':
            self.mode_label.setText("正在专注")
            self.work_info.setProperty("class", "InfoLabelActive")
            self.break_info.setProperty("class", "InfoLabel")
            self.long_break_overlay.hide()
        elif mode == 'long_break':
            self.mode_label.setText("正在长休息")
            self.work_info.setProperty("class", "InfoLabel")
            self.break_info.setProperty("class", "InfoLabelActive")
            # Update break info text for long break
            mins = self.timer.long_break_seconds // 60
            self.break_info.setText(f"长休 {mins:02d}:00")
            self.long_break_overlay.show()
            self.long_break_overlay.raise_()
        else: # break
            self.mode_label.setText("正在休息")
            self.work_info.setProperty("class", "InfoLabel")
            self.break_info.setProperty("class", "InfoLabelActive")
            # Update break info text for normal break
            mins = self.timer.break_seconds // 60
            self.break_info.setText(f"休息 {mins:02d}:00")
            self.long_break_overlay.hide()
            
        # Ensure work info text is correct
        work_mins = self.timer.work_seconds // 60
        self.work_info.setText(f"工作 {work_mins:02d}:00")
        
        # Refresh style to apply new property classes
        self.work_info.style().unpolish(self.work_info)
        self.work_info.style().polish(self.work_info)
        self.break_info.style().unpolish(self.break_info)
        self.break_info.style().polish(self.break_info)

    def handle_timer_finished(self):
        self.start_btn.setIcon(QIcon(get_resource_path("resources/icon_play.svg")))
        if self.auto_hide_sidebar_toggle.isChecked():
            self.animate_sidebar(85)
            
        if self.timer.is_working:
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
            import uuid
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
            delete_action.setIcon(QIcon("src/resources/icon_delete_new.svg"))
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

    def save_settings(self):
        w = self.work_mins_spin.value()
        b = self.break_mins_spin.value()
        sound_enabled = self.sound_toggle.isChecked()
        auto_hide = self.auto_hide_sidebar_toggle.isChecked()
        
        settings = {
            "work_mins": w,
            "break_mins": b,
            "sound_enabled": sound_enabled,
            "auto_hide_sidebar": auto_hide
        }
        self.data_manager.update_settings(settings)
        self.timer.set_durations(w, b)
        self.timer.set_sound_enabled(sound_enabled)
