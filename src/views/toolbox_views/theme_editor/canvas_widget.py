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
        self.sim_week_progress = 0.25
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
        TEXT_TYPES = ("time", "date", "month_info", "todo_line")
        states = {}
        for c in self._components:
            if c.category == "functional" and c.comp_type != "background":
                entry = {
                    "visible": c.visible, "x": c.x, "y": c.y,
                    "width": c.width, "height": c.height,
                }
                if c.comp_type in TEXT_TYPES:
                    entry["font_size"] = c.extra.get("font_size", 0)
                states[c.comp_type] = entry
        return states

    def apply_component_states(self, states: dict[str, dict]):
        """从持久化数据恢复组件状态"""
        TEXT_TYPES = ("time", "date", "month_info", "todo_line")
        for ctype, s in states.items():
            for c in self._components:
                if c.comp_type == ctype:
                    c.visible = s.get("visible", True)
                    c.x = s.get("x", c.x)
                    c.y = s.get("y", c.y)
                    c.width = s.get("width", c.width)
                    c.height = s.get("height", c.height)
                    if ctype in TEXT_TYPES:
                        fs = s.get("font_size", 0)
                        if fs:
                            c.extra["font_size"] = fs
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
            "background":{"name": "背景",    "x": 0.5, "y": 0.5, "locked": True, "deletable": False},
            "time":      {"name": "时间",    "x": 0.07, "y": 0.30, "locked": True, "deletable": False},
            "date":      {"name": "日期",    "x": 0.07, "y": 0.50, "locked": True, "deletable": False},
            "day_ring":   {"name": "日进度环","x": 0.82, "y": 0.44, "locked": True, "deletable": False},
            "week_ring":  {"name": "周进度环","x": 0.22, "y": 0.44, "locked": True, "deletable": False},
            "month_ring": {"name": "月进度环","x": 0.42, "y": 0.44, "locked": True, "deletable": False},
            "year_ring":  {"name": "年进度环","x": 0.62, "y": 0.44, "locked": True, "deletable": False},
            "month_info": {"name": "月/年",   "x": 0.07, "y": 0.70, "locked": True, "deletable": False},
            "todo_line":  {"name": "待办",    "x": 0.50, "y": 0.90, "locked": True, "deletable": False,
                           "width": 0.40, "height": 0.12},
            "divider":    {"name": "分隔线",  "x": 0.50, "y": 0.82, "locked": False, "deletable": True,
                           "width": 0.40, "height": 0.12, "category": "functional"},
        }
        d = defaults.get(comp_type, {"name": comp_type, "x": 0.5, "y": 0.5, "locked": False, "deletable": True})

        comp = CanvasComponent(
            comp_id=uuid.uuid4().hex[:12], comp_type=comp_type,
            name=d["name"],
            category=d.get("category", "functional" if d["locked"] else "decorative"),
            x=d["x"], y=d["y"],
            width=d.get("width", 0.18), height=d.get("height", 0.10),
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
            elif key == "font_size":
                c.extra["font_size"] = int(value)
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
            if not c.visible or c.comp_type == "background":
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

        # 根据当前主题的 panel 背景色亮度决定画布背景色
        bg_color = self.colors.get("performance_panel_background", [60, 60, 60, 200])
        luminance = 0.299 * bg_color[0] + 0.587 * bg_color[1] + 0.114 * bg_color[2]
        canvas_bg = QColor(220, 220, 220) if luminance > 128 else QColor(45, 45, 45)
        painter.fillRect(0, 0, cw, ch, canvas_bg)

        panel = self._panel_rect()

        # 面板外边框
        pen = QPen(QColor(100, 100, 100, 60), 1, Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(panel)

        # 委托给通用渲染引擎
        cs = self._build_component_states_dict()
        sim = _SimData(self.sim_day_progress, self.sim_week_progress,
                       self.sim_month_progress, self.sim_year_progress)
        if self._theme:
            self._theme._colors = self.colors
            self._theme._stickers = self._stickers
            self._theme.draw_generic_panel(painter, panel, cs, sim)
        else:
            from src.themes.base_theme import ThemeDefinition
            self._draw_generic_fallback(painter, panel, cs, sim)

        self._draw_selection_indicators(painter, panel)
        self._draw_grid(painter, panel)

    def _panel_rect(self) -> QRect:
        cw, ch = self.width(), self.height()
        sizes = {"normal": (180, 80), "compact": (190, 66), "mini": (95, 40)}
        sizes.update(self._custom_sizes)
        pw, ph = sizes.get(self._preview_mode, (180, 80))
        return QRect((cw - pw) // 2, (ch - ph) // 2, pw, ph)

    def _find(self, ctype):
        for c in self._components:
            if c.comp_type == ctype:
                return c
        return None

    def _build_component_states_dict(self) -> dict:
        """从画布组件列表构建 component_states 字典"""
        TEXT_TYPES = ("time", "date", "month_info", "todo_line")
        cs = {}
        for c in self._components:
            if c.category == "functional" and c.comp_type != "background":
                entry = {
                    "visible": c.visible, "x": c.x, "y": c.y,
                    "width": c.width, "height": c.height,
                }
                if c.comp_type in TEXT_TYPES:
                    fs = c.extra.get("font_size", 0)
                    if fs:
                        entry["font_size"] = fs
                cs[c.comp_type] = entry
        return cs

    def _draw_generic_fallback(self, painter, panel, cs, sim):
        """无主题时的回退渲染（与 draw_generic_panel 逻辑一致）"""
        # 这只是字体渲染在无主题时的回退色
        from PySide6.QtCore import Qt as QtCore
        px, py, pw, ph = panel.x(), panel.y(), panel.width(), panel.height()
        bg = QColor(*self.colors.get("performance_panel_background", [60, 60, 60, 220]))
        painter.setBrush(bg)
        painter.setPen(QPen(QColor(90, 90, 90), 1))
        painter.drawRoundedRect(px, py, pw, ph, 8, 8)
        # 委托给 draw_generic_panel 通过临时主题实例
        from src.themes.base_theme import CustomTheme
        tmp = CustomTheme(colors=self.colors, based_on="modern")
        tmp._stickers = self._stickers
        tmp.draw_generic_panel(painter, panel, cs, sim)

    def _draw_selection_indicators(self, painter, panel):
        for c in self._components:
            if not c.visible or c.comp_type == "background":
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


class _SimData:
    """模拟数据提供者，供画布预览使用"""
    __slots__ = ('day_progress', 'week_progress', 'month_progress', 'year_progress', 'first_todo_text')

    def __init__(self, day, week, month, year):
        self.day_progress = day
        self.week_progress = week
        self.month_progress = month
        self.year_progress = year
        self.first_todo_text = "示例待办事项"
