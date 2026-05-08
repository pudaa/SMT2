"""现代简约主题 — 时间大字靠左 + 单日进度环靠右 + 待办底部提醒"""
from __future__ import annotations
from PySide6.QtGui import QColor, QFont, QPen, QPainter
from PySide6.QtCore import Qt
from datetime import datetime
from src.themes.base_theme import ThemeDefinition, PanelMetrics, PanelCompactMetrics, PanelMiniMetrics


class ModernTheme(ThemeDefinition):
    """现代极简 — 无边框、单圆环、待办嵌入"""

    name = "modern"
    display_name = "Modern 现代"

    # ========== 颜色令牌（黑白灰） ==========
    _COLORS: dict[str, list[int]] = {
        "performance_panel_background":              [28, 28, 28, 200],
        "performance_panel_shadow":                  [0, 0, 0, 0],       # 无阴影
        "performance_panel_time":                    [255, 255, 255],
        "performance_panel_progress_ring_background": [72, 72, 72, 140],
        "performance_panel_progress_ring_foreground": [240, 240, 240],
        "performance_panel_progress_title":           [150, 150, 150],
        "performance_panel_progress_text":            [245, 245, 245],
        # 新增令牌
        "performance_panel_date":                     [190, 190, 190],
        "performance_panel_sub_info":                 [150, 150, 150],
        "performance_panel_divider":                  [100, 100, 100, 80],
        "performance_panel_todo_text":                [170, 170, 170],
        "performance_panel_todo_icon":               [170, 170, 170],
        # ---- TodoPanel ----
        "todo_panel_todoitem_background":                     [28, 28, 28, 100],
        "todo_panel_todoitem_foreground":                     [220, 220, 220],
        "todo_panel_todoitem_checkbox_unchecked_border":      [140, 140, 140],
        "todo_panel_todoitem_checkbox_checked_border":        [100, 100, 100],
        "todo_panel_todoitem_checkbox_checked_background":    [160, 160, 160],
        "todo_panel_todoitem_lineedit_foreground":            [220, 220, 220],
        "todo_panel_todoitem_lineedit_focus":                 [200, 200, 200],
        "todo_panel_todoitem_lineedit_finished":              [130, 130, 130],
        "todo_panel_todoitem_draglabel":                      [140, 140, 140],
        "todo_panel_titlelabel_foreground":                   [220, 220, 220],
        "todo_panel_titlelabel_background":                   [28, 28, 28, 200],
        "todo_panel_tagscrollarea_background":                 [28, 28, 28, 200],
        "todo_panel_tagbutton_background":                     [70, 70, 70],
        "todo_panel_tagbutton_foreground":                     [220, 220, 220],
        "todo_panel_tagbutton_checked_background":             [160, 160, 160],
        "todo_panel_tagbutton_checked_foreground":             [28, 28, 28],
        "todo_panel_tagbutton_check_hover_background":         [100, 100, 100],
        "todo_panel_tagbutton_checked_hover_background":       [180, 180, 180],
        "todo_panel_scrollarea_background":                    [28, 28, 28, 200],
        "todo_panel_scrollbar_background":                     [80, 80, 80],
    }

    def get_color(self, token: str) -> list[int]:
        return list(self._COLORS.get(token, [220, 220, 220]))

    def get_stylesheet(self) -> str:
        return ""

    # ========== 面板尺寸 ==========

    @property
    def metrics_normal(self) -> PanelMetrics:
        return PanelMetrics(
            panel_width=180,
            panel_height=80,
            ring_diameter=44,
            ring_spacing=0,
            ring_start_x=0,
            ring_y=0,
            ring_width=3,
            time_y=24,
            font_size_time=15,
            time_align_left=True,
            time_x=12,
            font_size_ring_title=7,
            font_size_ring_value=8,
            # 待办面板紧凑参数
            todo_border_radius=5,
            todo_item_height=28,
            todo_checkbox_size=15,
            todo_font_size=11,
            todo_title_font_size=13,
            todo_tag_font_size=10,
            todo_drag_font_size=12,
        )

    @property
    def metrics_compact(self) -> PanelCompactMetrics:
        return PanelCompactMetrics(
            panel_width=190,
            panel_height=66,
            ring_diameter=36,
            ring_spacing=0,
            ring_start_x=0,
            ring_y=0,
            ring_width=2,
            time_y=18,
            font_size_time=11,
            time_align_left=True,
            time_x=10,
            font_size_ring_title=7,
            font_size_ring_value=7,
        )

    @property
    def metrics_mini(self) -> PanelMiniMetrics:
        return PanelMiniMetrics(
            panel_width=95,
            panel_height=40,
            font_size_time=12,
        )

    @property
    def font_family(self) -> str:
        return "Microsoft YaHei UI"

    # ================================================================
    # 现代布局绘制
    # ================================================================

    def paint_panel(self, painter: QPainter, panel):
        """现代布局:
        
        ┌──────────────────────────────────┐
        │  16:30:25            ╭──────╮   │
        │  5月7日 周三          │ 34%  │   │
        │  月 18% · 年 35%     ╰──────╯   │
        │                     今日进度    │
        │  ────────────────────────────   │
        │  📋 提交项目周报文档...          │
        └──────────────────────────────────┘
        """
        w, h = panel.width(), panel.height()
        mode = panel._panel_mode
        m = panel._resolve_metrics()

        # ---- 背景（无边框、无阴影） ----
        bg = self.get_color("performance_panel_background")
        painter.setBrush(QColor(*bg))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, w, h, 5, 5)

        # ---- mini 模式：仅居中时间 ----
        if mode == "mini":
            self._draw_mini_time(painter, panel)
            self.paint_stickers(painter, panel.rect())
            return

        # ---- 左侧信息区 ----
        self._draw_left_info(painter, panel, m)
        
        # ---- 右侧日进度圆环 ----
        self._draw_day_ring(painter, panel, m)

        # ---- 分隔线 + 待办事项 ----
        self._draw_todo_section(painter, panel)

        # ---- 贴纸层（最上层） ----
        self.paint_stickers(painter, panel.rect())

    # ---------------------------------------------------------------
    # 分区绘制
    # ---------------------------------------------------------------

    def _draw_mini_time(self, painter: QPainter, panel):
        """极简模式 — 时间文本上下左右完全居中"""
        w, h = panel.width(), panel.height()
        m = panel._resolve_metrics()
        time_font = QFont(self.font_family, m.font_size_time)
        painter.setFont(time_font)
        painter.setPen(QColor(*self.get_color("performance_panel_time")))
        time_str = datetime.now().strftime("%H:%M:%S")
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(time_str)
        # 垂直居中：基线 y = 面板高度一半 + (ascent - descent)/2
        text_y = (h + fm.ascent() - fm.descent()) // 2
        painter.drawText((w - tw) // 2, text_y, time_str)

    def _draw_left_info(self, painter: QPainter, panel, m):
        """左侧：时间 + 日期 + 月度年度进度（紧凑纵向间距）"""
        font_family = self.font_family
        left_margin = m.time_x

        # ---- 时间：大字加粗 ----
        time_font = QFont(font_family, m.font_size_time, QFont.Bold)
        painter.setFont(time_font)
        painter.setPen(QColor(*self.get_color("performance_panel_time")))
        time_str = datetime.now().strftime("%H:%M:%S")
        painter.drawText(left_margin, m.time_y, time_str)

        # ---- 日期：小字（紧跟时间） ----
        date_font = QFont(font_family, 9)
        painter.setFont(date_font)
        painter.setPen(QColor(*self.get_color("performance_panel_date")))
        now = datetime.now()
        weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        date_str = f"{now.month}月{now.day}日 {weekday_names[now.weekday()]}"
        painter.drawText(left_margin, m.time_y + 16, date_str)

        # ---- 月/年进度（紧跟日期） ----
        sub_font = QFont(font_family, 8)
        painter.setFont(sub_font)
        painter.setPen(QColor(*self.get_color("performance_panel_sub_info")))
        month_pct = f"月 {round(panel.month_progress * 100)}%"
        year_pct = f"年 {round(panel.year_progress * 100)}%"
        info_y = m.time_y + 30
        painter.drawText(left_margin, info_y, f"{month_pct} · {year_pct}")

        # ---- 性能模式下显示 CPU/MEM ----
        if panel.performance_mode:
            perf_text = f"CPU {panel.cpu_percent:.0f}%  MEM {panel.memory_percent:.0f}%"
            painter.drawText(left_margin, info_y + 14, perf_text)

    def _draw_day_ring(self, painter: QPainter, panel, m):
        """右侧：今日时间占比圆环，上下居中，紧凑靠近左侧信息区"""
        w, h = panel.width(), panel.height()
        d = m.ring_diameter
        rw = m.ring_width
        
        # 圆环右边缘距右边 15px，垂直居中
        ring_right = w - 15
        ring_x = ring_right - d
        ring_y = (h - d) // 2
        
        # ---- 背景轨 ----
        pen = QPen(QColor(*self.get_color("performance_panel_progress_ring_background")))
        pen.setWidth(rw)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawEllipse(ring_x, ring_y, d, d)

        # ---- 进度弧 ----
        pen.setColor(QColor(*self.get_color("performance_panel_progress_ring_foreground")))
        painter.setPen(pen)
        progress = panel.day_progress
        span_angle = int(360 * progress * 16)
        painter.drawArc(ring_x, ring_y, d, d, 90 * 16, -span_angle)

        # ---- 圆环中心百分比（使用当前字体的 metrics） ----
        val_font = QFont(self.font_family, m.font_size_ring_value, QFont.Bold)
        painter.setFont(val_font)
        painter.setPen(QColor(*self.get_color("performance_panel_progress_text")))
        pct = f"{round(progress * 100)}%"
        val_fm = painter.fontMetrics()
        pct_w = val_fm.horizontalAdvance(pct)
        painter.drawText(ring_x + (d - pct_w) // 2,
                         ring_y + d // 2 + val_fm.ascent() // 2 - 1,
                         pct)

        # ---- 圆环下方标签（与圆环中轴对齐） ----
        # label_font = QFont(self.font_family, m.font_size_ring_title, QFont.Bold)
        # painter.setFont(label_font)
        # painter.setPen(QColor(*self.get_color("performance_panel_progress_title")))
        # label = "今日进度"
        # label_fm = painter.fontMetrics()
        # lw = label_fm.horizontalAdvance(label)
        # painter.drawText(ring_x + (d - lw) // 2,
        #                  ring_y + d + label_fm.ascent() + 2,
        #                  label)

    def _draw_todo_section(self, painter: QPainter, panel):
        """底部分隔线 + 首个待办事项（紧凑间距）"""
        w, h = panel.width(), panel.height()
        todo_text = getattr(panel, 'first_todo_text', '')
        if not todo_text:
            return

        todo_font = QFont(self.font_family, 9)
        painter.setFont(todo_font)
        fm = painter.fontMetrics()
        line_h = fm.height()

        # ---- 分隔线（紧贴待办上方） ----
        line_y = h - line_h - 6
        pen = QPen(QColor(*self.get_color("performance_panel_divider")))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(12, line_y, w - 80, line_y)

        # ---- 待办文本 ----
        painter.setPen(QColor(*self.get_color("performance_panel_todo_text")))
        max_todo_w = w - 40
        elided = fm.elidedText(todo_text, Qt.ElideRight, max_todo_w)
        painter.drawText(6, line_y + fm.ascent() + 2, f"📋 {elided}")
