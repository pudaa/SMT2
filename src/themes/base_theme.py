"""主题基类 - 定义所有主题必须实现的接口"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Optional
import uuid
import os


@dataclass
class PanelMetrics:
    """面板尺寸与布局参数"""
    panel_width: int = 250
    panel_height: int = 90          # 基础高度（不含todo面板）
    ring_diameter: int = 50
    ring_spacing: int = 60          # 相邻圆环中心间距
    ring_start_x: int = 10          # 第一个圆环的x坐标
    ring_y: int = 20
    ring_width: int = 2
    # 时间文本
    time_y: int = 15                # 时间文本基线 y（相对于面板顶部）
    font_size_time: int = 9
    time_align_left: bool = False   # True=靠左定位，False=居中
    time_x: int = 0                 # 靠左时的 x 坐标（align_left=True 时生效）
    font_size_ring_title: int = 8
    font_size_ring_value: int = 8
    # ---- 待办面板指标 ----
    todo_border_radius: int = 20    # 面板圆角半径
    todo_item_height: int = 32      # 单行事项高度
    todo_checkbox_size: int = 18    # 复选框尺寸
    todo_font_size: int = 12        # 事项文字字号
    todo_title_font_size: int = 15  # 标题字号
    todo_tag_font_size: int = 11    # 标签字号
    todo_drag_font_size: int = 14   # 拖动柄字号


@dataclass
class PanelCompactMetrics:
    """紧凑模式下的面板尺寸"""
    panel_width: int = 180
    panel_height: int = 70
    ring_diameter: int = 36
    ring_spacing: int = 44
    ring_start_x: int = 8
    ring_y: int = 16
    ring_width: int = 2
    time_y: int = 12
    font_size_time: int = 8
    time_align_left: bool = False
    time_x: int = 0
    font_size_ring_title: int = 7
    font_size_ring_value: int = 7


@dataclass
class PanelMiniMetrics:
    """极简模式 - 只显示时间"""
    panel_width: int = 85
    panel_height: int = 40
    ring_diameter: int = 0          # 不绘制
    ring_spacing: int = 0
    ring_start_x: int = 0
    ring_y: int = 0
    ring_width: int = 0
    time_y: int = 12                # 保留做基线参考，实际使用动态居中
    font_size_time: int = 10
    font_size_ring_title: int = 0
    font_size_ring_value: int = 0


@dataclass
class StickerData:
    """用户贴纸 —— 装饰性 PNG 图片叠加在面板上
    
    坐标采用相对于面板的归一化值 (0.0~1.0)，
    保证在不同面板尺寸下贴纸位置一致。
    """
    sticker_id: str = ""            # UUID，唯一标识
    name: str = ""                  # 用户命名，如 "角落猫咪"
    image_path: str = ""            # 磁盘上的 PNG 绝对路径
    x: float = 0.5                  # 中心点 x (0.0~1.0 相对面板宽度)
    y: float = 0.5                  # 中心点 y (0.0~1.0 相对面板高度)
    scale: float = 1.0              # 缩放倍数
    rotation: float = 0.0           # 旋转角度（度）
    opacity: float = 1.0            # 透明度 (0.0~1.0)
    z_order: int = 0                # 层叠顺序
    visible: bool = True

    def __post_init__(self):
        if not self.sticker_id:
            self.sticker_id = uuid.uuid4().hex[:12]


class ThemeDefinition(ABC):
    """主题抽象基类
    
    每个主题子类需要实现:
      - 颜色令牌 (get_color)
      - QSS 样式表 (get_stylesheet)
      - 面板尺寸/紧凑/极简指标
      - 字体族
      - **paint_panel** (自定义面板绘制)
    """

    # ---- 元信息 ----
    name: str = "base"
    display_name: str = "基础主题"

    # ---- 颜色令牌 ----
    @abstractmethod
    def get_color(self, token: str) -> list[int]:
        """根据令牌名称返回 RGBA 颜色值 [r, g, b, a] 或 [r, g, b]"""
        ...

    # ---- QSS ----
    def get_stylesheet(self) -> str:
        """返回全局 QSS 样式表（可选覆盖）"""
        return ""

    # ---- 面板尺寸 ----
    @property
    def metrics_normal(self) -> PanelMetrics:
        return PanelMetrics()

    @property
    def metrics_compact(self) -> PanelCompactMetrics:
        return PanelCompactMetrics()

    @property
    def metrics_mini(self) -> PanelMiniMetrics:
        return PanelMiniMetrics()

    # ---- 字体 ----
    @property
    def font_family(self) -> str:
        return "Microsoft YaHei UI"

    # ---- 贴纸 ----

    _stickers: list[StickerData] = []

    def get_stickers(self) -> list[StickerData]:
        """返回当前主题的贴纸列表"""
        return list(self._stickers)

    def set_stickers(self, stickers: list[StickerData]):
        """替换全部贴纸"""
        self._stickers = list(stickers)

    def paint_stickers(self, painter, panel_rect):
        """绘制贴纸到面板上
        
        参数:
            painter:   QPainter（已设置好抗锯齿）
            panel_rect: 面板矩形区域
        """
        from PySide6.QtGui import QPixmap
        stickers = self.get_stickers()
        if not stickers:
            return
        pw, ph = panel_rect.width(), panel_rect.height()
        for sticker in sorted(stickers, key=lambda s: s.z_order):
            if not sticker.visible or not os.path.isfile(sticker.image_path):
                continue
            pixmap = QPixmap(sticker.image_path)
            if pixmap.isNull():
                continue
            # 按缩放比计算目标尺寸
            target_w = int(pixmap.width() * sticker.scale)
            target_h = int(pixmap.height() * sticker.scale)
            # 归一化坐标 → 像素坐标
            target_x = int(pw * sticker.x) - target_w // 2
            target_y = int(ph * sticker.y) - target_h // 2

            painter.save()
            painter.setOpacity(sticker.opacity)
            if sticker.rotation != 0:
                cx, cy = target_x + target_w / 2, target_y + target_h / 2
                painter.translate(cx, cy)
                painter.rotate(sticker.rotation)
                painter.drawPixmap(
                    int(-target_w / 2), int(-target_h / 2),
                    target_w, target_h, pixmap
                )
            else:
                painter.drawPixmap(target_x, target_y, target_w, target_h, pixmap)
            painter.restore()

    # ================================================================
    # 绘制入口 —— 子类可覆写以实现完全自定义的布局
    # ================================================================

    def paint_panel(self, painter, panel):
        """默认绘制逻辑：经典风格（4 圆环 / 2 圆环 / 极简）
        
        参数:
            painter: QPainter
            panel: PerformancePanel 实例（可访问 cpu_percent, day_progress 等）
        """
        from PySide6.QtGui import QColor, QFont, QPen
        from PySide6.QtCore import Qt
        from datetime import datetime
        
        m = panel._resolve_metrics()
        mode = panel._panel_mode
        
        # ---- 背景 ----
        bg = self.get_color("performance_panel_background")
        painter.setBrush(QColor(*bg))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, panel.width(), panel.height(), 12, 12)
        
        # ---- 阴影 ----
        sd = self.get_color("performance_panel_shadow")
        painter.setBrush(QColor(*sd))
        painter.drawRoundedRect(2, 2, panel.width()-4, panel.height()-4, 12, 12)
        
        # ---- 时间文本 ----
        time_font = QFont(self.font_family, m.font_size_time)
        painter.setFont(time_font)
        painter.setPen(QColor(*self.get_color("performance_panel_time")))
        time_str = datetime.now().strftime("%H:%M:%S")
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(time_str)
        
        if mode == "mini":
            text_y = (panel.height() + fm.ascent() - fm.descent()) // 2
            painter.drawText((panel.width() - tw) // 2, text_y, time_str)
            self.paint_stickers(painter, panel.rect())
            return
        
        if getattr(m, 'time_align_left', False):
            painter.drawText(getattr(m, 'time_x', 12), m.time_y, time_str)
        else:
            painter.drawText((panel.width() - tw) // 2, m.time_y, time_str)
        
        # ---- 圆环 ----
        if m.ring_diameter <= 0:
            return
        
        if panel.performance_mode:
            self._draw_classic_performance_rings(painter, panel, m, mode)
        else:
            self._draw_classic_time_rings(painter, panel, m, mode)

        # ---- 贴纸层（最上层） ----
        self.paint_stickers(painter, panel.rect())

    # ---------------------------------------------------------------
    # 经典布局辅助方法（子类可复用）
    # ---------------------------------------------------------------

    def _draw_single_ring(self, painter, x, metrics, progress, label):
        """绘制单个圆环（经典布局复用）"""
        from PySide6.QtGui import QColor, QFont, QPen
        from PySide6.QtCore import Qt
        
        d = metrics.ring_diameter
        y = metrics.ring_y
        rw = metrics.ring_width
        percentage = f"{round(progress * 100)}%"
        
        # 背景环
        pen = QPen(QColor(*self.get_color("performance_panel_progress_ring_background")))
        pen.setWidth(rw)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawEllipse(x, y, d, d)
        
        # 进度弧
        pen.setColor(QColor(*self.get_color("performance_panel_progress_ring_foreground")))
        painter.setPen(pen)
        span_angle = int(360 * progress * 16)
        painter.drawArc(x, y, d, d, 90 * 16, -span_angle)
        
        # 百分比文字
        val_font = QFont(self.font_family, metrics.font_size_ring_value, QFont.Bold)
        painter.setFont(val_font)
        painter.setPen(QColor(*self.get_color("performance_panel_progress_text")))
        fm = painter.fontMetrics()
        vw = fm.horizontalAdvance(percentage)
        painter.drawText(x + (d - vw) // 2, y + d // 2 + fm.ascent() // 2, percentage)
        
        # 标签文字
        title_font = QFont(self.font_family, metrics.font_size_ring_title, QFont.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor(*self.get_color("performance_panel_progress_title")))
        fm = painter.fontMetrics()
        lw = fm.horizontalAdvance(label)
        painter.drawText(x + (d - lw) // 2, y + d + fm.ascent() + 4, label)

    def _draw_classic_performance_rings(self, painter, panel, metrics, mode):
        rings_data = [
            (panel.cpu_percent, "CPU"),
            (panel.memory_percent, "MEM"),
            (panel.disk_percent, "DISK"),
            (panel.battery_percent, "BAT"),
        ]
        if mode == "compact":
            rings_data = rings_data[:2]
        for i, (value, label) in enumerate(rings_data):
            x = metrics.ring_start_x + i * metrics.ring_spacing
            self._draw_single_ring(painter, x, metrics, value, label)

    def _draw_classic_time_rings(self, painter, panel, metrics, mode):
        from datetime import datetime
        weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        now = datetime.now()
        rings_data = [
            (panel.day_progress,   now.strftime("%d日")),
            (panel.week_progress,  weekday_names[now.weekday()]),
            (panel.month_progress, now.strftime("%m月")),
            (panel.year_progress,  now.strftime("%Y年")),
        ]
        if mode == "compact":
            rings_data = rings_data[:2]
        for i, (value, label) in enumerate(rings_data):
            x = metrics.ring_start_x + i * metrics.ring_spacing
            self._draw_single_ring(painter, x, metrics, value, label)


class CustomTheme(ThemeDefinition):
    """用户自定义主题 —— 颜色、尺寸、贴纸、组件状态均可持久化

    _panel_sizes: {"normal": (180,80), "compact": (190,66), "mini": (95,40)}
    _component_states: {comp_type: {"visible": True, "x": 0.07, "y": 0.30}}
    """

    name = "custom"
    display_name = "自定义"

    def __init__(self, theme_name: str = "custom", display_name: str = "自定义",
                 colors: dict[str, list[int]] | None = None,
                 based_on: str = "modern",
                 stickers: list[StickerData] | None = None,
                 panel_sizes: dict[str, list[int]] | None = None,
                 component_states: dict[str, dict] | None = None):
        self.name = theme_name
        self.display_name = display_name
        self._colors: dict[str, list[int]] = colors or {}
        self._based_on = based_on
        self._stickers: list[StickerData] = list(stickers) if stickers else []
        self._panel_sizes: dict[str, list[int]] = panel_sizes or {}
        self._component_states: dict[str, dict] = component_states or {}

    def get_panel_size(self, mode: str) -> tuple[int, int] | None:
        """获取自定义面板尺寸，未设置返回 None"""
        sz = self._panel_sizes.get(mode)
        return (sz[0], sz[1]) if sz else None

    def set_panel_size(self, mode: str, width: int, height: int):
        self._panel_sizes[mode] = [width, height]

    def get_color(self, token: str) -> list[int]:
        return list(self._colors.get(token, [200, 200, 200]))

    def get_stylesheet(self) -> str:
        return ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "colors": self._colors,
            "based_on": self._based_on,
            "stickers": [asdict(s) for s in self._stickers],
            "panel_sizes": self._panel_sizes,
            "component_states": self._component_states,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CustomTheme":
        stickers_raw = data.get("stickers", [])
        stickers = [StickerData(**s) for s in stickers_raw]
        return cls(
            theme_name=data.get("name", "custom"),
            display_name=data.get("display_name", "自定义"),
            colors=data.get("colors", {}),
            based_on=data.get("based_on", "modern"),
            stickers=stickers,
            panel_sizes=data.get("panel_sizes", {}),
            component_states=data.get("component_states", {}),
        )

    # 布局：自定义尺寸优先，否则继承 based_on
    @property
    def metrics_normal(self) -> PanelMetrics:
        base = self._base_metrics().metrics_normal
        sz = self._panel_sizes.get("normal")
        if sz:
            base.panel_width, base.panel_height = sz[0], sz[1]
        return base

    @property
    def metrics_compact(self) -> PanelCompactMetrics:
        base = self._base_metrics().metrics_compact
        sz = self._panel_sizes.get("compact")
        if sz:
            base.panel_width, base.panel_height = sz[0], sz[1]
        return base

    @property
    def metrics_mini(self) -> PanelMiniMetrics:
        base = self._base_metrics().metrics_mini
        sz = self._panel_sizes.get("mini")
        if sz:
            base.panel_width, base.panel_height = sz[0], sz[1]
        return base

    def _base_metrics(self) -> ThemeDefinition:
        from src.themes import _BUILTIN_THEMES
        base_cls = _BUILTIN_THEMES.get(self._based_on)
        if base_cls:
            return base_cls()
        from src.themes.modern_theme import ModernTheme
        return ModernTheme()

    @property
    def font_family(self) -> str:
        from src.themes import _BUILTIN_THEMES
        base_cls = _BUILTIN_THEMES.get(self._based_on)
        if base_cls:
            return base_cls().font_family
        return "Microsoft YaHei UI"

    def paint_panel(self, painter, panel):
        """委托给基础主题的绘制逻辑（缓存实例避免每帧创建）"""
        from src.themes import _BUILTIN_THEMES
        base_cls = _BUILTIN_THEMES.get(self._based_on)
        if base_cls:
            if not hasattr(self, '_cached_base_theme'):
                self._cached_base_theme = base_cls()
            # 注入颜色与贴纸到缓存的基础主题实例
            self._cached_base_theme._COLORS = self._colors  # type: ignore
            self._cached_base_theme._stickers = self._stickers  # type: ignore
            self._cached_base_theme.paint_panel(painter, panel)
        else:
            super().paint_panel(painter, panel)
