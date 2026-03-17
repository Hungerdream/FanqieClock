"""
chart_widgets.py  —  纯 PyQt6 绘图实现的统计图表组件
  • BarChartWidget  : 近 N 天番茄数柱状图
  • HeatmapWidget   : Pomotroid 风格年度热力图（52 周 × 7 天，年份可切换）
"""
from __future__ import annotations
import calendar
from PyQt6.QtWidgets import QWidget, QToolTip, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSizePolicy
from PyQt6.QtCore import Qt, QRectF, QDate, QPointF, pyqtSignal
from PyQt6.QtGui import (QPainter, QColor, QFont, QPen, QFontMetrics)


# ─────────────────────────── 工具函数 ────────────────────────────────────────

def _date_range(days: int) -> list[str]:
    """返回从今日往前 days 天的 ISO 日期列表（升序）"""
    today = QDate.currentDate()
    return [today.addDays(-days + 1 + i).toString(Qt.DateFormat.ISODate)
            for i in range(days)]


# ─────────────────────────── 近 7 天柱状图 ───────────────────────────────────

class BarChartWidget(QWidget):
    """近 7 天每日番茄数量柱状图"""

    BAR_COLOR        = QColor("#E74C3C")
    BAR_HOVER_COLOR  = QColor("#C0392B")
    AXIS_COLOR       = QColor("#CCCCCC")
    TEXT_COLOR       = QColor("#888888")
    VALUE_COLOR      = QColor("#333333")
    BG_COLOR         = QColor(0, 0, 0, 0)   # 透明背景

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: dict[str, int] = {}   # { "YYYY-MM-DD": count }
        self._hover_index: int = -1
        self.setMouseTracking(True)
        self.setMinimumHeight(200)

    def set_data(self, history: dict):
        """history: { "YYYY-MM-DD": {"count": N, "minutes": M} }"""
        dates = _date_range(7)
        self._data = {d: history.get(d, {}).get("count", 0) for d in dates}
        self.update()

    # ── mouse ──────────────────────────────────────────────────────────────
    def mouseMoveEvent(self, event):
        idx = self._bar_index_at(event.position().toPoint())
        if idx != self._hover_index:
            self._hover_index = idx
            self.update()
        if idx >= 0:
            dates = list(self._data.keys())
            d = dates[idx]
            count = self._data[d]
            QToolTip.showText(event.globalPosition().toPoint(),
                              f"{d}\n{count} 个番茄", self)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover_index = -1
        self.update()
        super().leaveEvent(event)

    def _bar_index_at(self, pos) -> int:
        if not self._data:
            return -1
        n = len(self._data)
        pad_l, pad_r, pad_t, pad_b = 40, 20, 20, 40
        w = self.width() - pad_l - pad_r
        bar_w = w / n
        x = pos.x() - pad_l
        if x < 0 or x > w:
            return -1
        return int(x // bar_w)

    # ── paint ──────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        if not self._data:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        pad_l, pad_r, pad_t, pad_b = 40, 20, 20, 40
        chart_w = w - pad_l - pad_r
        chart_h = h - pad_t - pad_b

        # 背景
        painter.fillRect(self.rect(), self.BG_COLOR)

        dates  = list(self._data.keys())
        values = list(self._data.values())
        n      = len(dates)
        max_v  = max(values) if any(v > 0 for v in values) else 1

        bar_total_w = chart_w / n
        bar_w       = bar_total_w * 0.55
        bar_gap     = (bar_total_w - bar_w) / 2

        # 轴线
        pen = QPen(self.AXIS_COLOR)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(pad_l, h - pad_b, w - pad_r, h - pad_b)

        # 水平网格（3 条）
        grid_pen = QPen(QColor("#F0F0F0"))
        grid_pen.setWidth(1)
        for i in range(1, 4):
            y_grid = pad_t + chart_h - (i / 3) * chart_h
            painter.setPen(grid_pen)
            painter.drawLine(pad_l, int(y_grid), w - pad_r, int(y_grid))
            # y 轴数值标签
            painter.setPen(QPen(self.TEXT_COLOR))
            font = QFont("Segoe UI", 8)
            painter.setFont(font)
            label = str(int(max_v * i / 3))
            painter.drawText(0, int(y_grid) - 6, pad_l - 4, 14,
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                             label)

        # 柱子
        for i, (d, v) in enumerate(zip(dates, values)):
            x_bar = pad_l + i * bar_total_w + bar_gap
            bar_h = (v / max_v) * chart_h if max_v > 0 else 0
            y_bar = pad_t + chart_h - bar_h

            color = self.BAR_HOVER_COLOR if i == self._hover_index else self.BAR_COLOR
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)

            rect = QRectF(x_bar, y_bar, bar_w, bar_h)
            radius = min(4.0, bar_w / 4)
            if bar_h > 0:
                painter.drawRoundedRect(rect, radius, radius)

            # 顶部数值（有数据才显示）
            if v > 0:
                font = QFont("Segoe UI", 9)
                font.setBold(True)
                painter.setFont(font)
                painter.setPen(self.VALUE_COLOR)
                painter.drawText(int(x_bar), int(y_bar) - 18, int(bar_w), 16,
                                 Qt.AlignmentFlag.AlignCenter, str(v))

            # X 轴日期标签（显示 MM/DD）
            month_day = d[5:]  # "MM-DD"
            font = QFont("Segoe UI", 8)
            painter.setFont(font)
            painter.setPen(QPen(self.TEXT_COLOR))
            painter.drawText(int(x_bar - bar_gap / 2), h - pad_b + 4,
                             int(bar_total_w), 20,
                             Qt.AlignmentFlag.AlignCenter, month_day)

        painter.end()


# ─────────────────────────── 年度热力图画布 ───────────────────────────────────

class _HeatmapCanvas(QWidget):
    """
    内部画布：纯绘图，不含年份导航控件。
    按照 Pomotroid 风格：
      - 全年 52~53 列（每列=1周，周一在上）
      - 顶部月份标签
      - 左侧只显示"周一 / 周三 / 周五"
      - 暖米黄色阶（无数据=浅米色，有数据=暖褐色深浅）
    """

    # 番茄钟红色系色阶
    COLORS = [
        QColor("#EDE8E8"),   # 0  无数据（浅灰）
        QColor("#F4B8B0"),   # 1  少（浅红）
        QColor("#E87060"),   # 2  中低（中红）
        QColor("#E74C3C"),   # 3  中高（标准番茄红）
        QColor("#C0392B"),   # 4  多（深红）
    ]
    TEXT_COLOR  = QColor("#999999")
    LABEL_COLOR = QColor("#666666")

    PAD_L = 38    # 左边距（留给"周X"标签）
    PAD_T = 22    # 顶边距（留给月份标签）
    PAD_B = 28    # 底边距（图例）
    PAD_R = 10    # 右边距

    def __init__(self, parent=None):
        super().__init__(parent)
        self._history: dict = {}
        self._year: int = QDate.currentDate().year()
        self._cell_rects: list[tuple[QRectF, str, int]] = []
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._update_height()

    def _year_columns(self) -> int:
        """该年共有多少列（周数）"""
        jan1 = QDate(self._year, 1, 1)
        dec31 = QDate(self._year, 12, 31)
        first_day_dow = jan1.dayOfWeek()
        days_in_year = jan1.daysTo(dec31) + 1
        import math
        return math.ceil((first_day_dow - 1 + days_in_year) / 7)

    def _cell_stride(self) -> float:
        """根据当前可用宽度动态计算 cell + gap 的 stride"""
        cols = self._year_columns()
        avail = self.width() - self.PAD_L - self.PAD_R
        if avail <= 0 or cols <= 0:
            return 13.0  # 默认值
        return avail / cols

    def _update_height(self):
        """只固定高度，宽度随父容器伸展"""
        # 用默认 stride=13 估算高度
        stride = 13
        h = self.PAD_T + 7 * stride + self.PAD_B
        self.setFixedHeight(h)

    def set_year(self, year: int):
        self._year = year
        self._cell_rects = []
        self.update()

    def set_history(self, history: dict):
        self._history = history
        self._cell_rects = []
        self.update()

    def _update_size(self):
        self._update_height()

    def _cell_for_date(self, d: QDate) -> tuple[int, int] | None:
        if d.year() != self._year:
            return None
        jan1 = QDate(self._year, 1, 1)
        day_offset = jan1.daysTo(d)
        first_dow  = jan1.dayOfWeek() - 1
        col = (first_dow + day_offset) // 7
        row = (first_dow + day_offset) % 7
        return col, row

    def _color_for(self, count: int) -> QColor:
        if count <= 0: return self.COLORS[0]
        if count == 1: return self.COLORS[1]
        if count <= 3: return self.COLORS[2]
        if count <= 6: return self.COLORS[3]
        return self.COLORS[4]

    # ── mouse ──────────────────────────────────────────────────────────────

    def mouseMoveEvent(self, event):
        pos = event.position()
        for rect, d, count in self._cell_rects:
            if rect.contains(pos):
                tip = f"{d}\n{count} 个番茄" if count > 0 else f"{d}  暂无记录"
                QToolTip.showText(event.globalPosition().toPoint(), tip, self)
                return
        super().mouseMoveEvent(event)

    def resizeEvent(self, event):
        """窗口宽度变化时重绘"""
        self._cell_rects.clear()
        self.update()
        super().resizeEvent(event)

    # ── paint ──────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        self._cell_rects.clear()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 根据实际宽度计算 stride（cell+gap）
        cols   = self._year_columns()
        stride = self._cell_stride()
        cell   = max(stride * 0.77, 4.0)   # cell 约占 stride 的 77%，最小 4px
        gap    = stride - cell

        # ── 星期标签（只画 周一/周三/周五）──────────────────────────────
        day_labels = {0: "周一", 2: "周三", 4: "周五"}
        font_day = QFont("Microsoft YaHei", 8)
        painter.setFont(font_day)
        painter.setPen(QPen(self.LABEL_COLOR))
        for row, lbl in day_labels.items():
            y = self.PAD_T + row * stride + cell / 2
            painter.drawText(0, int(y - 7), self.PAD_L - 4, 14,
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                             lbl)

        # ── 格子 + 月份标签 ──────────────────────────────────────────────
        font_month = QFont("Microsoft YaHei", 8)
        painter.setFont(font_month)

        jan1  = QDate(self._year, 1, 1)
        dec31 = QDate(self._year, 12, 31)
        last_month_col: dict[int, int] = {}

        for col in range(cols):
            for row in range(7):
                first_dow = jan1.dayOfWeek() - 1
                day_idx   = col * 7 + row - first_dow
                if 0 <= day_idx < jan1.daysTo(dec31) + 1:
                    d = jan1.addDays(day_idx)
                    m = d.month()
                    if m not in last_month_col:
                        last_month_col[m] = col
                    break

        painter.setPen(QPen(self.LABEL_COLOR))
        for month, col in last_month_col.items():
            x = self.PAD_L + col * stride
            painter.drawText(int(x), 2, int(stride * 4), 18,
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                             f"{month}月")

        # 画格子
        first_dow  = jan1.dayOfWeek() - 1
        total_days = jan1.daysTo(dec31) + 1
        today_str  = QDate.currentDate().toString(Qt.DateFormat.ISODate)

        painter.setPen(Qt.PenStyle.NoPen)
        for col in range(cols):
            for row in range(7):
                day_idx = col * 7 + row - first_dow
                if day_idx < 0 or day_idx >= total_days:
                    continue
                d     = jan1.addDays(day_idx)
                d_str = d.toString(Qt.DateFormat.ISODate)
                count = self._history.get(d_str, {}).get("count", 0)
                color = self._color_for(count)

                if d_str > today_str:
                    color = QColor(color)
                    color.setAlpha(80)

                x    = self.PAD_L + col * stride
                y    = self.PAD_T + row * stride
                rect = QRectF(x, y, cell, cell)

                painter.setBrush(color)
                painter.drawRoundedRect(rect, 2.5, 2.5)
                self._cell_rects.append((rect, d_str, count))

        # ── 图例 ──────────────────────────────────────────────────────────
        total_h  = self.PAD_T + 7 * stride + self.PAD_B
        legend_y = total_h - 16
        font_leg = QFont("Microsoft YaHei", 8)
        painter.setFont(font_leg)
        painter.setPen(QPen(self.LABEL_COLOR))

        painter.drawText(self.PAD_L, int(legend_y - 5), 20, 14,
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         "少")
        lx = self.PAD_L + 22
        leg_cell = 11
        for ci, c in enumerate(self.COLORS):
            rect = QRectF(lx + ci * (leg_cell + 2), legend_y - 5, leg_cell, leg_cell)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(c)
            painter.drawRoundedRect(rect, 2, 2)
        painter.setPen(QPen(self.LABEL_COLOR))
        painter.drawText(int(lx + len(self.COLORS) * (leg_cell + 2) + 2),
                         int(legend_y - 5), 20, 14,
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         "多")

        painter.end()


# ─────────────────────────── 对外暴露的热力图组件 ────────────────────────────

class HeatmapWidget(QWidget):
    """
    Pomotroid 风格年度热力图，包含：
      - 顶部年份导航（← 2026 →）
      - 全年 52~53 列格子
      - 底部图例
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._history: dict = {}
        self._current_year = QDate.currentDate().year()
        self._min_year = 2020
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        # ── 年份导航行 ──────────────────────────────────────────────────
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 4)
        nav_layout.setSpacing(8)

        btn_style = (
            "QPushButton { background: transparent; border: none; "
            "color: #AAAAAA; font-size: 15px; padding: 0 4px; }"
            "QPushButton:hover { color: #E74C3C; }"
            "QPushButton:disabled { color: #DDDDDD; }"
        )

        self._btn_prev = QPushButton("‹")
        self._btn_prev.setFixedSize(22, 22)
        self._btn_prev.setStyleSheet(btn_style)
        self._btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_prev.clicked.connect(self._go_prev)

        self._year_label = QLabel(str(self._current_year))
        self._year_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._year_label.setStyleSheet(
            "font-size: 15px; font-weight: 600; color: #444444; "
            "font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;"
        )
        self._year_label.setFixedWidth(52)

        self._btn_next = QPushButton("›")
        self._btn_next.setFixedSize(22, 22)
        self._btn_next.setStyleSheet(btn_style)
        self._btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_next.clicked.connect(self._go_next)

        nav_layout.addSpacing(_HeatmapCanvas.PAD_L - 4)
        nav_layout.addWidget(self._btn_prev)
        nav_layout.addWidget(self._year_label)
        nav_layout.addWidget(self._btn_next)
        nav_layout.addStretch()

        # ── 画布 ────────────────────────────────────────────────────────
        self._canvas = _HeatmapCanvas()
        self._canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding,   # 水平拉伸填满
            QSizePolicy.Policy.Fixed
        )

        # ── 组合 ────────────────────────────────────────────────────────
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(nav_layout)
        layout.addWidget(self._canvas)
        layout.addStretch()

        self._refresh_nav()

    def set_data(self, history: dict):
        """接收完整历史数据（DataManager 格式）"""
        self._history = history
        # 自动推断最早年份
        if history:
            earliest = min(history.keys())
            self._min_year = int(earliest[:4])
        self._canvas.set_history(history)
        self._refresh_nav()

    # ── 导航 ──────────────────────────────────────────────────────────────

    def _go_prev(self):
        self._current_year -= 1
        self._canvas.set_year(self._current_year)
        self._year_label.setText(str(self._current_year))
        self._refresh_nav()

    def _go_next(self):
        self._current_year += 1
        self._canvas.set_year(self._current_year)
        self._year_label.setText(str(self._current_year))
        self._refresh_nav()

    def _refresh_nav(self):
        today_year = QDate.currentDate().year()
        self._btn_prev.setEnabled(self._current_year > self._min_year)
        self._btn_next.setEnabled(self._current_year < today_year)
