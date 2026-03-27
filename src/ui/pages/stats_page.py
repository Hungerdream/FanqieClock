"""统计页面 - 数据统计与导出"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QListWidget, QFileDialog,
                             QScrollArea, QMessageBox)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QTextDocument, QPageSize, QPdfWriter
from ui.chart_widgets import BarChartWidget, HeatmapWidget


class StatsPage(QWidget):
    """统计页面"""
    
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self._init_ui()
    
    def _init_ui(self):
        # 外层容器（直接放入 content_stack）
        outer_layout = QVBoxLayout(self)
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
        export_btn.clicked.connect(self.export_pdf)
        header_layout.addWidget(export_btn)
        
        layout.addLayout(header_layout)
        layout.addSpacing(30)
        
        # Summary Cards Grid
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)
        
        self.stat_pomos = self._create_stat_card("累计番茄", "0", "🍅", "#FFF0F0")
        self.stat_time = self._create_stat_card("专注时长", "0 分钟", "⏱️", "#F0F8FF")
        self.stat_days = self._create_stat_card("累计天数", "0", "📅", "#F5F5F5")
        self.stat_interrupts = self._create_stat_card("打断次数", "0", "⚡", "#FFF8E1")
        
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
    
    def _create_stat_card(self, title, value, icon, bg_color):
        """创建统计卡片"""
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
    
    def refresh(self):
        """刷新统计数据"""
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
        sorted_dates = sorted(history.keys(), reverse=True)[:7]  # Show last 7 days
        for date_str in sorted_dates:
            day_data = history[date_str]
            item_text = f"📅 {date_str}   |   🍅 {day_data['count']} 个番茄   |   ⏳ {day_data['minutes']} 分钟"
            self.history_list.addItem(item_text)
    
    def export_pdf(self):
        """导出PDF报告"""
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
        writer.setResolution(300)  # 300 DPI for better quality
        
        doc.print(writer)
        
        QMessageBox.information(self, "导出成功", f"报告已保存至:\n{filename}")
