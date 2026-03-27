"""主窗口框架 - 番茄钟应用程序主窗口"""
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QStackedWidget, QLineEdit, 
                             QTextEdit, QFrame, QMessageBox, QApplication, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve, QEvent, QParallelAnimationGroup, QTimer
from PyQt6.QtGui import QColor, QIcon, QCursor, QShortcut, QKeySequence
from logic.timer import PomodoroTimer
from logic.data_manager import DataManager
from logic.quote_worker import QuoteWorker
from ui.widgets import CircularProgressBar, LongBreakOverlay, SmoothButton
from ui.pages import KanbanPage, NotesPage, StatsPage, SettingsPage
from utils import get_resource_path
import sys
import os


class MainWindow(QMainWindow):
    switch_to_compact = pyqtSignal()

    def __init__(self, timer: PomodoroTimer):
        super().__init__()
        self.timer = timer
        self.data_manager = DataManager()
        self.current_task = None
        
        self._init_ui()
        self._load_saved_data()
        self._setup_connections()
        self._setup_shortcuts()
        
        # Fetch Daily Quote
        self.quote_worker = QuoteWorker()
        self.quote_worker.quote_fetched.connect(self._update_daily_quote)
        self.quote_worker.start()

    def _setup_shortcuts(self):
        """注册快捷键（窗口有焦点时有效）"""
        # 空格键：开始/放弃计时
        space_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        space_shortcut.activated.connect(self._on_space_pressed)

    def _on_space_pressed(self):
        """空格键按下时的处理"""
        focused = QApplication.focusWidget()
        if isinstance(focused, (QLineEdit, QTextEdit)):
            return
        if self.content_stack.currentIndex() == 0:
            self.toggle_timer()

    def _update_daily_quote(self, content, author):
        """更新每日一句"""
        if hasattr(self, 'notes_page'):
            self.notes_page.update_quote(content, author)

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
            # Wait for any pending save workers to finish before sync save
            self.data_manager.thread_pool.waitForDone(3000)
            # If triggered by app.quit(), save data and let it close
            try:
                self.data_manager.save_data_sync()
            except Exception as e:
                print(f"Error saving data on close: {e}")
            event.accept()

    def _init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("番茄钟")
        self.setMinimumSize(1100, 750)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QHBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. Sidebar (Persistent)
        self._init_sidebar()
        
        # 2. Main Content Stack
        self._init_content_stack()
        
        # Long Break Overlay
        self.long_break_overlay = LongBreakOverlay(self)
        self.long_break_overlay.hide()
        
        # Default to Timer Page
        self.switch_page(0)

    def _init_sidebar(self):
        """初始化侧边栏"""
        self.sidebar = QFrame()
        self.sidebar.setFrameShape(QFrame.Shape.NoFrame)
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(85)
        self.sidebar.installEventFilter(self)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(10, 30, 10, 10)
        
        # Sidebar Hide Timer (Debounce)
        self.sidebar_hide_timer = QTimer()
        self.sidebar_hide_timer.setSingleShot(True)
        self.sidebar_hide_timer.setInterval(300)
        self.sidebar_hide_timer.timeout.connect(self._check_and_hide_sidebar)
        
        # Sidebar Hover Polling Timer (For wider trigger area)
        self.sidebar_hover_timer = QTimer()
        self.sidebar_hover_timer.setInterval(50)
        self.sidebar_hover_timer.timeout.connect(self._check_sidebar_hover)
        self.sidebar_hover_timer.start()
        
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
            btn.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            if i == 0: 
                btn.setChecked(True)
                btn.setProperty("active", "true")
            btn.clicked.connect(lambda checked, index=i: self.switch_page(index))
            sidebar_layout.addWidget(btn)
            self.nav_btns.append(btn)
        
        sidebar_layout.addStretch()
        self.main_layout.addWidget(self.sidebar)

    def _init_content_stack(self):
        """初始化内容堆栈"""
        self.content_stack = QStackedWidget()
        
        # 创建各个页面
        self.timer_page = self._create_timer_page()
        self.kanban_page = KanbanPage(self.data_manager, self)
        self.notes_page = NotesPage(self.data_manager, self)
        self.stats_page = StatsPage(self.data_manager, self)
        self.settings_page = SettingsPage(self.data_manager, self.timer, self)
        
        # 连接信号
        self.kanban_page.focus_task.connect(self.start_focus_on_task)
        self.settings_page.settings_changed.connect(self._on_settings_saved)
        
        # 添加页面到堆栈
        self.content_stack.addWidget(self.timer_page)
        self.content_stack.addWidget(self.kanban_page)
        self.content_stack.addWidget(self.notes_page)
        self.content_stack.addWidget(self.stats_page)
        self.content_stack.addWidget(self.settings_page)
        
        self.main_layout.addWidget(self.content_stack)

    def _create_timer_page(self):
        """创建计时器页面"""
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
        
        logo = QLabel("番茄钟")
        logo.setStyleSheet("font-size: 20px; font-weight: bold; color: #333; margin-left: 10px;")
        
        header_layout.addWidget(logo)
        header_layout.addStretch()
        
        icon_btns_layout = QHBoxLayout()
        icon_btns_layout.setSpacing(20)
        
        header_btns_data = [
            ("compact", "切换小窗模式", get_resource_path("resources/icon_compact.svg")),
            ("theme", "深色模式", get_resource_path("resources/icon_theme.svg"))
        ]

        for key, tooltip, icon_path in header_btns_data:
            btn = QPushButton()
            btn.setFixedSize(35, 35)
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QSize(20, 20))
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
                self.theme_btn.toggled.connect(self._on_theme_toggled)
        
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
        from PyQt6.QtWidgets import QStackedLayout
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
        self.start_btn.setFixedSize(80, 80)
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
        
        from PyQt6.QtWidgets import QProgressBar
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

    def resizeEvent(self, event):
        if hasattr(self, 'long_break_overlay'):
            self.long_break_overlay.resize(self.size())
            
        # Responsive Sidebar Logic
        if not hasattr(self, 'timer') or not self.timer.is_running:
            width = event.size().width()
            
            is_compact_width = width < 1200
            if not hasattr(self, '_last_compact_mode'):
                old_width = event.oldSize().width()
                self._last_compact_mode = (old_width < 1200) if old_width > 0 else (not is_compact_width)
                
            if is_compact_width != self._last_compact_mode:
                if is_compact_width:
                    self.animate_sidebar(0)
                else:
                    self.animate_sidebar(85)
                self._last_compact_mode = is_compact_width
                
        super().resizeEvent(event)

    # ─── Timer 相关方法 ─────────────────────────────────────────────────────

    def abandon_timer(self):
        """放弃计时"""
        self.timer.reset()
        self.mode_label.setText("已放弃")
        if self.settings_page.auto_hide_sidebar_toggle.isChecked():
            self.animate_sidebar(85)

    def record_interruption(self, type_name):
        """记录打断"""
        self.data_manager.record_interruption(type_name)
        self.mode_label.setText(f"已记录：{'内部' if type_name=='internal' else '外部'}打断")
        QTimer.singleShot(1500, lambda: self._update_mode_display(self.timer.current_mode))

    def start_focus_on_task(self, task_data):
        """开始专注某个任务"""
        self.switch_page(0)  # Switch to Timer page
        self.current_task = task_data
        self.mode_label.setText(f"正在专注：{task_data.get('content', '未知任务')}")
        if not self.timer.is_running:
            self.toggle_timer()

    def stop_timer(self):
        """停止计时"""
        self.timer.reset()
        if self.settings_page.auto_hide_sidebar_toggle.isChecked():
            self.animate_sidebar(85)

    def toggle_timer(self):
        """切换计时器状态"""
        if self.timer.is_running:
            reply = QMessageBox.question(
                self, '放弃当前番茄钟？',
                '根据番茄工作法，番茄钟一旦开始就不应暂停。确定要放弃当前这一组计时吗？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.timer.abandon()
                if self.settings_page.auto_hide_sidebar_toggle.isChecked():
                    self.animate_sidebar(85)
        else:
            self.timer.start()
            if self.settings_page.auto_hide_sidebar_toggle.isChecked():
                self.animate_sidebar(0)

    def _update_play_pause_button(self):
        """更新播放/暂停按钮"""
        if self.timer.is_running:
            self.start_btn.setIcon(QIcon(get_resource_path("resources/icon_abandon.svg")))
            self.start_btn.setToolTip("放弃专注")
        else:
            self.start_btn.setIcon(QIcon(get_resource_path("resources/icon_play.svg")))
            self.start_btn.setToolTip("开始专注")

    def _update_timer_display(self, seconds):
        """更新计时器显示"""
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
        
        self.progress_bar.set_max_value(total_seconds)
        self.progress_bar.value = total_seconds - seconds

    def _update_mode_display(self, mode):
        """更新模式显示"""
        if mode == 'work':
            self.mode_label.setText("正在专注")
            self.work_info.setProperty("class", "InfoLabelActive")
            self.break_info.setProperty("class", "InfoLabel")
            self.display_stack.setCurrentWidget(self.timer_label)
        elif mode == 'long_break':
            self.mode_label.setText("正在长休息")
            self.work_info.setProperty("class", "InfoLabel")
            self.break_info.setProperty("class", "InfoLabelActive")
            mins = self.timer.long_break_seconds // 60
            self.break_info.setText(f"长休 {mins:02d}:00")
            self.display_stack.setCurrentWidget(self.timer_label)
        else:  # break
            self.mode_label.setText("正在休息")
            self.work_info.setProperty("class", "InfoLabel")
            self.break_info.setProperty("class", "InfoLabelActive")
            mins = self.timer.break_seconds // 60
            self.break_info.setText(f"短休 {mins:02d}:00")
            self.display_stack.setCurrentWidget(self.timer_label)
        
        self._update_play_pause_button()
            
        work_mins = self.timer.work_seconds // 60
        self.work_info.setText(f"工作 {work_mins:02d}:00")
        
        self.work_info.style().unpolish(self.work_info)
        self.work_info.style().polish(self.work_info)
        self.break_info.style().unpolish(self.break_info)
        self.break_info.style().polish(self.break_info)

    def _handle_timer_finished(self):
        """处理计时结束"""
        if self.settings_page.auto_hide_sidebar_toggle.isChecked():
            self.animate_sidebar(85)
            
        if self.timer.current_mode == 'work':
            if hasattr(self, 'current_task') and self.current_task:
                self.kanban_page.update_task_pomo_count(self.current_task['id'])
                
            self.data_manager.record_session(self.settings_page.work_mins_spin.value())
            self.stats_page.refresh()

    # ─── Sidebar 相关方法 ───────────────────────────────────────────────────

    def switch_page(self, index):
        """切换页面"""
        if self.content_stack.currentIndex() == index: 
            return
        
        self.content_stack.setCurrentIndex(index)
        
        # Update active state of nav buttons    
        for i, btn in enumerate(self.nav_btns):
            btn.setChecked(i == index)
            btn.setProperty("active", "true" if i == index else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        
        if index == 3: 
            self.stats_page.refresh()

    def eventFilter(self, obj, event):
        if obj == self.sidebar:
            if event.type() == QEvent.Type.Enter:
                self.sidebar_hide_timer.stop()
                if self.sidebar.width() < 85:
                    self.animate_sidebar(85)
            elif event.type() == QEvent.Type.Leave:
                should_hide = False
                
                if self.timer.is_running and hasattr(self, 'settings_page') and self.settings_page.auto_hide_sidebar_toggle.isChecked():
                    should_hide = True
                elif self.width() < 1200:
                    should_hide = True
                    
                if should_hide:
                    self.sidebar_hide_timer.start()
                    
        return super().eventFilter(obj, event)

    def _check_sidebar_hover(self):
        """检查侧边栏悬停"""
        if self.sidebar.width() > 50:
            self.sidebar_hover_timer.stop()
            return
            
        cursor_pos = QCursor.pos()
        local_pos = self.mapFromGlobal(cursor_pos)
        
        if self.rect().contains(local_pos):
            if local_pos.x() <= 50:
                self.sidebar_hide_timer.stop()
                self.animate_sidebar(85)

    def _check_and_hide_sidebar(self):
        """检查并隐藏侧边栏"""
        cursor_pos = QCursor.pos()
        mapped_pos = self.sidebar.mapFromGlobal(cursor_pos)
        if not self.sidebar.rect().contains(mapped_pos):
            self.animate_sidebar(0)

    def toggle_sidebar(self):
        """切换侧边栏"""
        width = self.sidebar.width()
        target = 85 if width <= 0 else 0
        self.animate_sidebar(target)
        
        state = "expanded" if target == 85 else "collapsed"
        settings = self.data_manager.data.get("settings", {})
        settings["sidebar_manual_state"] = state
        self.data_manager.update_settings(settings)

    def animate_sidebar(self, target_width):
        """动画侧边栏"""
        is_animating = hasattr(self, 'anim_group') and self.anim_group.state() == QParallelAnimationGroup.State.Running
        if is_animating:
            if self.anim_min.endValue() == target_width:
                return
            self.anim_group.stop()
            
        width = self.sidebar.width()
        if width == target_width: 
            return
        
        self.anim_min = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self.anim_min.setDuration(300) 
        self.anim_min.setStartValue(width)
        self.anim_min.setEndValue(target_width)
        self.anim_min.setEasingCurve(QEasingCurve.Type.OutCubic) 
        
        self.anim_max = QPropertyAnimation(self.sidebar, b"maximumWidth")
        self.anim_max.setDuration(300)
        self.anim_max.setStartValue(width)
        self.anim_max.setEndValue(target_width)
        self.anim_max.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.anim_group = QParallelAnimationGroup()
        self.anim_group.addAnimation(self.anim_min)
        self.anim_group.addAnimation(self.anim_max)
        if target_width == 0:
            self.anim_group.finished.connect(self._on_sidebar_collapsed)
        self.anim_group.start()

    def _on_sidebar_collapsed(self):
        """侧边栏折叠完成时的回调"""
        self.sidebar_hover_timer.start()

    # ─── 数据加载与保存 ─────────────────────────────────────────────────────

    def _load_saved_data(self):
        """加载保存的数据"""
        data = self.data_manager.data
        
        # 加载看板数据
        tasks = data.get("tasks", {})
        self.kanban_page.load_data(tasks)
        
        # 刷新笔记和统计
        self.notes_page.refresh_table()
        self.stats_page.refresh()
        
        # 加载设置
        settings = data.get("settings", {})
        self.settings_page.load_settings(settings)
        
        # 应用 timer 设置
        self.timer.set_durations(
            self.settings_page.work_mins_spin.value(),
            self.settings_page.break_mins_spin.value(),
            self.settings_page.long_break_mins_spin.value()
        )
        self.timer.set_long_break_interval(self.settings_page.long_break_interval_spin.value())
        self.timer.set_sound_enabled(self.settings_page.sound_toggle.isChecked())
        self.timer.set_sound_paths(
            work=settings.get("sound_work"),
            short_break=settings.get("sound_break"),
            long_break=settings.get("sound_long_break")
        )
        self.timer.set_tick_enabled(
            work_tick=settings.get("tick_enabled_work", True),
            break_tick=settings.get("tick_enabled_break", True)
        )
        self.timer.auto_start = settings.get("auto_start", True)
        
        # Apply saved theme preference
        theme = settings.get("theme", "light")
        self.apply_theme(theme)
        if hasattr(self, 'theme_btn'):
            self.theme_btn.blockSignals(True)
            self.theme_btn.setChecked(theme == "dark")
            self.theme_btn.blockSignals(False)

    def _setup_connections(self):
        """设置信号连接"""
        self.timer.tick.connect(self._update_timer_display)
        self.timer.mode_changed.connect(self._update_mode_display)
        self.timer.finished.connect(self._handle_timer_finished)
        self.timer.started.connect(self._update_play_pause_button)
        self.timer.paused.connect(self._update_play_pause_button)
        self.timer.abandoned.connect(self._update_play_pause_button)
        
        self.start_btn.clicked.connect(self.toggle_timer)
        
        self.data_manager.save_error.connect(self._show_save_error)

    def _show_save_error(self, message):
        """显示保存错误"""
        QMessageBox.warning(self, "数据保存失败", f"无法保存数据，请检查磁盘空间或权限。\n错误信息: {message}")

    def _on_settings_saved(self, settings):
        """设置保存时的处理"""
        self.data_manager.update_settings(settings)
        self.timer.set_sound_paths(
            work=settings.get("sound_work"),
            short_break=settings.get("sound_break"),
            long_break=settings.get("sound_long_break")
        )

    # ─── 主题相关 ───────────────────────────────────────────────────────────

    def _on_theme_toggled(self, checked):
        """主题切换"""
        theme = "dark" if checked else "light"
        self.apply_theme(theme)
        self.data_manager.update_settings({"theme": theme})

    def apply_theme(self, theme):
        """应用主题"""
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
