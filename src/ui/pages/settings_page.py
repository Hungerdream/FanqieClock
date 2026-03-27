"""设置页面 - 应用设置管理"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QScrollArea, QStackedWidget,
                             QCheckBox, QDialog)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from ui.widgets import NumberControl
from utils import get_resource_path


class SettingsPage(QWidget):
    """设置页面 - Pomotroid 风格：左侧导航列表 + 右侧分页内容区"""
    
    # 设置变更信号
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, data_manager, timer, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.timer = timer
        self._init_ui()
    
    def _init_ui(self):
        self.setObjectName("SettingsPage")
        outer = QHBoxLayout(self)
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
            btn.clicked.connect(lambda _, idx=i: self._switch_tab(idx))
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

        # 自动开始下一阶段
        r_autostart = make_row_item("自动开始下一阶段", "阶段结束后自动开始休息/工作")
        self.auto_start_toggle = QCheckBox()
        self.auto_start_toggle.setStyleSheet(checkbox_style)
        self.auto_start_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        r_autostart.addWidget(self.auto_start_toggle)
        p1.addLayout(r_autostart)

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

        # 连接所有设置项变更信号
        self._connect_settings_signals()

        # 默认显示第一个 tab
        self._switch_tab(0)
    
    def _connect_settings_signals(self):
        """连接设置项变更信号"""
        self.work_mins_spin.valueChanged.connect(self._on_settings_changed)
        self.break_mins_spin.valueChanged.connect(self._on_settings_changed)
        self.long_break_mins_spin.valueChanged.connect(self._on_settings_changed)
        self.long_break_interval_spin.valueChanged.connect(self._on_settings_changed)
        self.sound_toggle.toggled.connect(self._on_settings_changed)
        self.auto_hide_sidebar_toggle.toggled.connect(self._on_settings_changed)
        self.auto_start_toggle.toggled.connect(self._on_settings_changed)
        self.tick_work_toggle.toggled.connect(self._on_settings_changed)
        self.tick_break_toggle.toggled.connect(self._on_settings_changed)
    
    def _on_settings_changed(self, *_args):
        """设置变更时的处理"""
        settings = self.get_settings()
        # 立即应用到 timer
        self.timer.auto_start = settings.get("auto_start", True)
        self.timer.set_durations(
            settings.get("work_mins", 25),
            settings.get("break_mins", 5),
            settings.get("long_break_mins", 15)
        )
        self.timer.set_long_break_interval(settings.get("long_break_interval", 4))
        self.timer.set_sound_enabled(settings.get("sound_enabled", True))
        self.timer.set_tick_enabled(
            work_tick=settings.get("tick_enabled_work", True),
            break_tick=settings.get("tick_enabled_break", True)
        )
        # 发出信号通知主窗口
        self.settings_changed.emit(settings)
    
    def _switch_tab(self, index):
        """切换设置分页"""
        self._settings_stack.setCurrentIndex(index)
        for i, btn in enumerate(self._settings_nav_btns):
            btn.setChecked(i == index)
    
    def show_sponsor_dialog(self):
        """显示赞助对话框"""
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
    
    def get_settings(self):
        """获取当前设置值"""
        current_settings = self.data_manager.data.get("settings", {})
        return {
            "work_mins": self.work_mins_spin.value(),
            "break_mins": self.break_mins_spin.value(),
            "long_break_mins": self.long_break_mins_spin.value(),
            "long_break_interval": self.long_break_interval_spin.value(),
            "sound_enabled": self.sound_toggle.isChecked(),
            "sound_work": current_settings.get("sound_work"),
            "sound_break": current_settings.get("sound_break"),
            "sound_long_break": current_settings.get("sound_long_break"),
            "tick_enabled_work": self.tick_work_toggle.isChecked(),
            "tick_enabled_break": self.tick_break_toggle.isChecked(),
            "auto_hide_sidebar": self.auto_hide_sidebar_toggle.isChecked(),
            "auto_start": self.auto_start_toggle.isChecked(),
            "theme": current_settings.get("theme", "light")
        }
    
    def load_settings(self, settings):
        """加载设置值"""
        self.work_mins_spin.setValue(settings.get("work_mins", 25))
        self.break_mins_spin.setValue(settings.get("break_mins", 5))
        self.long_break_mins_spin.setValue(settings.get("long_break_mins", 15))
        self.long_break_interval_spin.setValue(settings.get("long_break_interval", 4))
        self.sound_toggle.setChecked(settings.get("sound_enabled", True))
        self.auto_hide_sidebar_toggle.setChecked(settings.get("auto_hide_sidebar", True))
        self.auto_start_toggle.setChecked(settings.get("auto_start", True))
        self.tick_work_toggle.setChecked(settings.get("tick_enabled_work", True))
        self.tick_break_toggle.setChecked(settings.get("tick_enabled_break", True))
