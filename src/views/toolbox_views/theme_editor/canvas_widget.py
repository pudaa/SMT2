"""主题画布 — 实时预览面板，支持组件选中/拖拽/删除

坐标体系:
  组件存储 面板内归一化坐标 (0.0~1.0)
  所有命中检测/选中框/拖拽计算均基于面板区域换算
"""
from __future__ import annotations
from PySide6.QtWidgets import QWidget, QMenu
from PySide6.QtGui import (
    QPainter, QPen, QColor, QFont, QPixmap, QMouseEvent,
)
from PySide6.QtCore import Qt, Signal, QPoint, QRect
from datetime import datetime
import os
from src.themes.base_theme import StickerData


class CanvasComponent:
    """画布上的一个可视组件 — 坐标均为面板内归一化值 (0.0~1.0)"""

    def __init__(self, comp_id: str, comp_type: str, name: str,
                 category: str, x: float, y: float,
                 width: float = 0.1, height: float = 0.08,
                 locked: bool = False, deletable: bool = True,
                 visible: bool = True,
                 extra: dict | None = None):
        self.comp_id = comp_id
        self.comp_type = comp_type
        self.name = name
        self.category = category
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.locked = locked
        self.deletable = deletable
        self.visible = visible
        self.extra = extra or {}

    def to_dict(self) -> dict:
        return {
            "comp_id": self.comp_id, "comp_type": self.comp_type,
            "name": self.name, "category": self.category,
            "x": self.x, "y": self.y, "width": self.width, "height": self.height,
            "locked": self.locked, "deletable": self.deletable,
            "visible": self.visible,
            "extra": self.extra,
        }

    def canvas_rect(self, panel_rect: QRect) -> QRect:
        """返回该组件在画布上的像素包围盒（基于面板区域换算）"""
        px, py, pw, ph = panel_rect.x(), panel_rect.y(), panel_rect.width(), panel_rect.height()
        cx = px + int(pw * self.x)
        cy = py + int(ph * self.y)
        w = max(int(pw * self.width), 16)
        h = max(int(ph * self.height), 16)
        return QRect(cx - w // 2, cy - h // 2, w, h)


class ThemeCanvas(QWidget):
    """中央画布 — 实时预览 + 交互编辑"""

    component_selected = Signal(object)
    component_moved = Signal(object)
    component_added = Signal(object)
    component_deleted = Signal(str)

    SNAP_GRID = 8

    def __init__(self):
        super().__init__()
        self.setObjectName("themeCanvas")
        self.setMinimumWidth(300)
        self.setMouseTracking(True)

        self.colors: dict[str, list[int]] = {}
        self._components: list[CanvasComponent] = []
        self._stickers: list[StickerData] = []
        self._theme = None
        self._preview_mode: str = "normal"
        self._custom_sizes: dict[str, tuple[int, int]] = {}

        self._selected_comp: CanvasComponent | None = None
        self._hovered_comp: CanvasComponent | None = None
        self._dragging: bool = False
        self._drag_start_canvas: QPoint = QPoint()
        self._drag_orig_x: float = 0.0
        self._drag_orig_y: float = 0.0
        self._suppress_signals: bool = False

        self.sim_day_progress = 0.35
        self.sim_month_progress = 0.18
        self.sim_year_progress = 0.35
        self.performance_mode = False

        self.setMinimumSize(320, 120)
        self.setStyleSheet("background-color: #2d2d2d;")

    # ================================================================
    # 数据接口
    # ================================================================

    def set_theme(self, theme):
        self._theme = theme

    def set_colors(self, colors: dict):
        self.colors = dict(colors)

    def set_stickers(self, stickers: list[StickerData]):
        self._stickers = list(stickers)
        self._sync_sticker_components()

    def get_stickers(self) -> list[StickerData]:
        return list(self._stickers)

    def get_component_states(self) -> dict[str, dict]:
        """导出功能组件状态（持久化用）"""
        states = {}
        for c in self._components:
            if c.category == "functional":
                states[c.comp_type] = {
                    "visible": c.visible, "x": c.x, "y": c.y,
                    "width": c.width, "height": c.height,
                }
        return states

    def apply_component_states(self, states: dict[str, dict]):
        """从持久化数据恢复组件状态"""
        for ctype, s in states.items():
            for c in self._components:
                if c.comp_type == ctype:
                    c.visible = s.get("visible", True)
                    c.x = s.get("x", c.x)
                    c.y = s.get("y", c.y)
                    c.width = s.get("width", c.width)
                    c.height = s.get("height", c.height)
                    break

    def clear_all_functional_components(self):
        """清空所有功能组件（保留贴纸）"""
        self._components = [c for c in self._components if c.category != "functional"]

    def set_preview_mode(self, mode: str):
        self._preview_mode = mode
        self.update()

    def set_panel_size(self, mode: str, width: int, height: int):
        """动态更新指定模式的画布面板尺寸"""
        self._custom_sizes[mode] = (width, height)
        if mode == self._preview_mode:
            self.update()

    def _sync_sticker_components(self):
        self._components = [c for c in self._components if c.comp_type != "sticker"]
        for s in self._stickers:
            self._components.append(CanvasComponent(
                comp_id=s.sticker_id, comp_type="sticker",
                name=s.name or "贴纸", category="decorative",
                x=s.x, y=s.y, width=0.15, height=0.15,
                locked=False, deletable=True,
                extra={"image_path": s.image_path, "scale": s.scale,
                       "rotation": s.rotation, "opacity": s.opacity},
            ))

    # ================================================================
    # 组件增删
    # ================================================================

    def add_component_by_type(self, comp_type: str):
        import uuid

        if comp_type.startswith("sticker:"):
            image_path = comp_type.split(":", 1)[1]
            sid = uuid.uuid4().hex[:12]
            s = StickerData(sticker_id=sid, name=os.path.basename(image_path),
                            image_path=image_path, x=0.5, y=0.5, scale=0.5)
            self._stickers.append(s)
            self._sync_sticker_components()
            for c in self._components:
                if c.comp_id == sid:
                    self._selected_comp = c
                    self.component_added.emit(c.to_dict())
                    self.component_selected.emit(c.to_dict())
                    break
            self.update()
            return

        defaults = {
            "time":       {"name": "时间",    "x": 0.07, "y": 0.30, "locked": True, "deletable": False},
            "date":       {"name": "日期",    "x": 0.07, "y": 0.50, "locked": True, "deletable": False},
            "day_ring":   {"name": "日进度环","x": 0.82, "y": 0.44, "locked": True, "deletable": False},
            "week_ring":  {"name": "周进度环","x": 0.22, "y": 0.44, "locked": True, "deletable": False},
            "month_ring": {"name": "月进度环","x": 0.42, "y": 0.44, "locked": True, "deletable": False},
            "year_ring":  {"name": "年进度环","x": 0.62, "y": 0.44, "locked": True, "deletable": False},
            "month_info": {"name": "月/年",   "x": 0.07, "y": 0.70, "locked": True, "deletable": False},
            "todo_line":  {"name": "待办",    "x": 0.50, "y": 0.90, "locked": True, "deletable": False},
            "divider":    {"name": "分隔线",  "x": 0.50, "y": 0.82, "locked": False, "deletable": True},
        }
        d = defaults.get(comp_type, {"name": comp_type, "x": 0.5, "y": 0.5, "locked": False, "deletable": True})

        comp = CanvasComponent(
            comp_id=uuid.uuid4().hex[:12], comp_type=comp_type,
            name=d["name"], category="functional" if d["locked"] else "decorative",
            x=d["x"], y=d["y"], width=0.18, height=0.10,
            locked=d["locked"], deletable=d["deletable"],
        )
        self._components.append(comp)
        self._selected_comp = comp
        self.component_added.emit(comp.to_dict())
        if not self._suppress_signals:
            self.component_selected.emit(comp.to_dict())
        self.update()

    def delete_component(self, comp_id: str):
        if not self._selected_comp or self._selected_comp.comp_id != comp_id:
            return
        if self._selected_comp.locked:
            return
        if self._selected_comp.comp_type == "sticker":
            self._stickers = [s for s in self._stickers if s.sticker_id != comp_id]
        self._components = [c for c in self._components if c.comp_id != comp_id]
        self.component_deleted.emit(comp_id)
        self._selected_comp = None
        self.component_selected.emit(None)
        self.update()

    def update_component_property(self, comp_id: str, key: str, value):
        for c in self._components:
            if c.comp_id != comp_id:
                continue
            if key in ("x", "y", "width", "height"):
                setattr(c, key, float(value))
            elif key == "visible":
                c.visible = bool(value)
            elif key == "color_token":
                color_key = c.extra.get("color_key", "")
                if color_key and isinstance(value, (list, tuple)):
                    self.colors[color_key] = list(value)
                    c.extra[key] = list(value)
            else:
                c.extra[key] = value
            if c.comp_type == "sticker":
                self._sync_sticker_from_component(c)
            self.update()
            return

    def _sync_sticker_from_component(self, comp: CanvasComponent):
        for s in self._stickers:
            if s.sticker_id == comp.comp_id:
                s.x = comp.x
                s.y = comp.y
                s.scale = comp.extra.get("scale", s.scale)
                s.rotation = comp.extra.get("rotation", s.rotation)
                s.opacity = comp.extra.get("opacity", s.opacity)
                s.name = comp.extra.get("name", s.name)
                return

    # ================================================================
    # 事件处理 — 全部基于面板区域
    # ================================================================

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() != Qt.LeftButton:
            return
        panel = self._panel_rect()
        hit = self._hit_test(event.pos(), panel)
        if hit:
            self._selected_comp = hit
            self._dragging = True
            self._drag_start_canvas = event.pos()
            self._drag_orig_x = hit.x
            self._drag_orig_y = hit.y
            self.setCursor(Qt.ClosedHandCursor)
            self.component_selected.emit(hit.to_dict())
        else:
            self._selected_comp = None
            self.component_selected.emit(None)
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        panel = self._panel_rect()
        pw, ph = panel.width(), panel.height()

        if self._dragging and self._selected_comp:
            dx_px = event.pos().x() - self._drag_start_canvas.x()
            dy_px = event.pos().y() - self._drag_start_canvas.y()
            dx = dx_px / max(pw, 1)
            dy = dy_px / max(ph, 1)
            new_x = self._drag_orig_x + dx
            new_y = self._drag_orig_y + dy
            snap = self.SNAP_GRID
            px_in_panel = new_x * pw
            py_in_panel = new_y * ph
            new_x = (round(px_in_panel / snap) * snap) / max(pw, 1)
            new_y = (round(py_in_panel / snap) * snap) / max(ph, 1)
            self._selected_comp.x = max(0.0, min(1.0, new_x))
            self._selected_comp.y = max(0.0, min(1.0, new_y))
            if self._selected_comp.comp_type == "sticker":
                self._sync_sticker_from_component(self._selected_comp)
            self.component_moved.emit(self._selected_comp.to_dict())
            self.update()
        else:
            hit = self._hit_test(event.pos(), panel)
            prev = self._hovered_comp
            if hit:
                self._hovered_comp = hit
                self.setCursor(Qt.OpenHandCursor)
            else:
                self._hovered_comp = None
                self.setCursor(Qt.ArrowCursor)
            if prev != self._hovered_comp:
                self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._dragging = False

    def contextMenuEvent(self, event):
        if not self._selected_comp:
            return
        menu = QMenu(self)
        if self._selected_comp.deletable and not self._selected_comp.locked:
            comp_id = self._selected_comp.comp_id
            del_action = menu.addAction("🗑️ 删除")
            del_action.triggered.connect(lambda cid=comp_id: self.delete_component(cid))
        menu.addAction("📋 复制坐标").triggered.connect(self._copy_coords)
        menu.exec(event.globalPos())

    def _copy_coords(self):
        if self._selected_comp:
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(
                f"x={self._selected_comp.x:.3f}, y={self._selected_comp.y:.3f}"
            )

    # ================================================================
    # 碰撞检测 — 基于面板区域
    # ================================================================

    def _hit_test(self, canvas_pos: QPoint, panel_rect: QRect) -> CanvasComponent | None:
        for c in reversed(self._components):
            if not c.visible:
                continue
            r = c.canvas_rect(panel_rect)
            r = r.adjusted(-6, -6, 6, 6)
            if r.contains(canvas_pos):
                return c
        return None

    # ================================================================
    # 绘制
    # ================================================================

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        cw, ch = self.width(), self.height()

        painter.fillRect(0, 0, cw, ch, QColor(45, 45, 45))

        panel = self._panel_rect()
        px, py, pw, ph = panel.x(), panel.y(), panel.width(), panel.height()

        # 面板外边框
        pen = QPen(QColor(100, 100, 100, 60), 1, Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(panel)

        # 面板背景
        bg = self.colors.get("performance_panel_background", [60, 60, 60, 220])
        painter.setBrush(QColor(*bg))
        painter.setPen(QPen(QColor(90, 90, 90), 1))
        painter.drawRoundedRect(px, py, pw, ph, 8, 8)

        painter.save()
        painter.setClipRect(panel)
        self._draw_time_text(painter, panel)
        self._draw_date_text(painter, panel)
        self._draw_all_rings(painter, panel)
        self._draw_month_year(painter, panel)
        self._draw_divider(painter, panel)
        self._draw_todo_text(painter, panel)
        self._draw_stickers(painter, panel)
        painter.restore()

        self._draw_selection_indicators(painter, panel)
        self._draw_grid(painter, panel)

    def _panel_rect(self) -> QRect:
        cw, ch = self.width(), self.height()
        sizes = {"normal": (180, 80), "compact": (190, 66), "mini": (95, 40)}
        sizes.update(self._custom_sizes)
        pw, ph = sizes.get(self._preview_mode, (180, 80))
        return QRect((cw - pw) // 2, (ch - ph) // 2, pw, ph)

    def _comp_px(self, comp, panel, dx, dy):
        x = comp.x if comp else dx
        y = comp.y if comp else dy
        return int(panel.x() + panel.width() * x), int(panel.y() + panel.height() * y)

    def _find(self, ctype):
        for c in self._components:
            if c.comp_type == ctype:
                return c
        return None

    def _draw_time_text(self, painter, panel):
        c = self._find("time")
        if c and not c.visible:
            return
        cx, cy = self._comp_px(c, panel, 0.07, 0.30)
        color = self.colors.get("performance_panel_time", [255, 255, 255])
        painter.setFont(QFont("Microsoft YaHei UI", 13, QFont.Bold))
        painter.setPen(QColor(*color))
        painter.drawText(cx, cy, datetime.now().strftime("%H:%M:%S"))

    def _draw_date_text(self, painter, panel):
        c = self._find("date")
        if not c or not c.visible:
            return
        cx, cy = self._comp_px(c, panel, 0.07, 0.50)
        color = self.colors.get("performance_panel_date", [190, 190, 190])
        painter.setFont(QFont("Microsoft YaHei UI", 9))
        painter.setPen(QColor(*color))
        now = datetime.now()
        wd = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        painter.drawText(cx, cy, f"{now.month}月{now.day}日 {wd[now.weekday()]}")

    def _draw_all_rings(self, painter, panel):
        """绘制所有进度环（日/周/月/年），仅绘制存在且可见的组件"""
        ring_types = [
            ("day_ring",   self.sim_day_progress,   "日"),
            ("week_ring",  0.50,                    "周"),
            ("month_ring", self.sim_month_progress, "月"),
            ("year_ring",  self.sim_year_progress,  "年"),
        ]
        for ctype, progress, label in ring_types:
            c = self._find(ctype)
            if not c or not c.visible:
                continue
            self._draw_single_canvas_ring(painter, panel, c, ctype, progress, label)

    def _draw_single_canvas_ring(self, painter, panel, c, ctype, progress, label):
        """绘制单个进度环（canvas 版本，归一化坐标）"""
        default_pos = {
            "day_ring": (0.82, 0.44), "week_ring": (0.22, 0.44),
            "month_ring": (0.42, 0.44), "year_ring": (0.62, 0.44),
        }
        dx, dy = default_pos.get(ctype, (0.5, 0.5))
        if c:
            dx, dy = c.x, c.y
        cx = int(panel.x() + panel.width() * dx)
        cy = int(panel.y() + panel.height() * dy)
        # 半径 ≈ 面板宽度的 1/8（与 modern_theme 44/180≈0.24 匹配）
        r = max(8, panel.width() // 8)

        ring_bg = self.colors.get("performance_panel_progress_ring_background", [72, 72, 72, 140])
        ring_fg = self.colors.get("performance_panel_progress_ring_foreground", [240, 240, 240])
        pen = QPen(QColor(*ring_bg), 2)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)
        pen.setColor(QColor(*ring_fg))
        painter.setPen(pen)
        span = int(360 * max(0.0, min(1.0, progress)) * 16)
        painter.drawArc(cx - r, cy - r, r * 2, r * 2, 90 * 16, -span)

        font = QFont("Microsoft YaHei UI", 7, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QColor(*self.colors.get("performance_panel_progress_text", [245, 245, 245])))
        pct = f"{round(progress * 100)}%"
        fm = painter.fontMetrics()
        painter.drawText(cx - fm.horizontalAdvance(pct) // 2, cy + fm.ascent() // 2, pct)

    def _draw_month_year(self, painter, panel):
        c = self._find("month_info")
        if not c or not c.visible:
            return
        cx, cy = self._comp_px(c, panel, 0.07, 0.68)
        color = self.colors.get("performance_panel_sub_info", [150, 150, 150])
        painter.setFont(QFont("Microsoft YaHei UI", 8))
        painter.setPen(QColor(*color))
        painter.drawText(cx, cy, f"月 {round(self.sim_month_progress*100)}% · 年 {round(self.sim_year_progress*100)}%")

    def _draw_divider(self, painter, panel):
        c = self._find("divider")
        if not c or not c.visible:
            return
        cx, cy = self._comp_px(c, panel, 0.50, 0.82)
        color = self.colors.get("performance_panel_divider", [100, 100, 100, 80])
        painter.setPen(QPen(QColor(*color), 1))
        lw = panel.width() * 0.75
        lx = int(panel.x() + panel.width() * 0.125)
        painter.drawLine(lx, cy, int(lx + lw), cy)

    def _draw_todo_text(self, painter, panel):
        c = self._find("todo_line")
        if not c or not c.visible:
            return
        cx, cy = self._comp_px(c, panel, 0.50, 0.92)
        color = self.colors.get("performance_panel_todo_text", [170, 170, 170])
        painter.setFont(QFont("Microsoft YaHei UI", 8))
        painter.setPen(QColor(*color))
        text = "📋 示例待办事项..."
        fm = painter.fontMetrics()
        painter.drawText(cx - fm.horizontalAdvance(text) // 2, cy, text)

    def _draw_stickers(self, painter, panel):
        for s in sorted(self._stickers, key=lambda s: s.z_order):
            if not s.visible or not os.path.isfile(s.image_path):
                continue
            pixmap = QPixmap(s.image_path)
            if pixmap.isNull():
                continue
            tw = int(pixmap.width() * s.scale)
            th = int(pixmap.height() * s.scale)
            tx = int(panel.x() + panel.width() * s.x) - tw // 2
            ty = int(panel.y() + panel.height() * s.y) - th // 2
            painter.save()
            painter.setOpacity(s.opacity)
            if s.rotation != 0:
                painter.translate(tx + tw / 2, ty + th / 2)
                painter.rotate(s.rotation)
                painter.drawPixmap(int(-tw / 2), int(-th / 2), tw, th, pixmap)
            else:
                painter.drawPixmap(tx, ty, tw, th, pixmap)
            painter.restore()

    def _draw_selection_indicators(self, painter, panel):
        for c in self._components:
            if not c.visible:
                continue
            r = c.canvas_rect(panel)
            if c is self._selected_comp:
                pen = QPen(QColor(74, 144, 226), 2, Qt.DashLine)
                painter.setPen(pen)
                painter.setBrush(QColor(74, 144, 226, 25))
                painter.drawRect(r)
                cx = panel.x() + int(panel.width() * c.x)
                cy = panel.y() + int(panel.height() * c.y)
                painter.setPen(QColor(74, 144, 226))
                painter.drawLine(cx - 5, cy, cx + 5, cy)
                painter.drawLine(cx, cy - 5, cx, cy + 5)
            elif c is self._hovered_comp:
                pen = QPen(QColor(200, 200, 200, 120), 1, Qt.DashLine)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(r)

    def _draw_grid(self, painter, panel):
        px, py, pw, ph = panel.x(), panel.y(), panel.width(), panel.height()
        grid = self.SNAP_GRID
        painter.setPen(QPen(QColor(255, 255, 255, 10), 1))
        for gx in range(px, px + pw, grid):
            painter.drawLine(gx, py, gx, py + ph)
        for gy in range(py, py + ph, grid):
            painter.drawLine(px, gy, px + pw, gy)
