"""组件面板 — 左侧可添加的组件列表 + 贴纸导入"""
from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFrame, QFileDialog
)
from PySide6.QtCore import Qt, Signal
from src.utils.icon_utils import load_svg_icon


# 可用组件定义
BUILTIN_COMPONENTS = [
    {"type": "background", "name": "背景颜色",  "icon": "palette.svg",   "category": "functional"},
    {"type": "time",       "name": "时间",      "icon": "clock.svg",    "category": "functional"},
    {"type": "date",       "name": "日期",      "icon": "calendar.svg", "category": "functional"},
    {"type": "day_ring",   "name": "日进度环",  "icon": "chart.svg",    "category": "functional"},
    {"type": "week_ring",  "name": "周进度环",  "icon": "chart.svg",    "category": "functional"},
    {"type": "month_ring", "name": "月进度环",  "icon": "chart.svg",    "category": "functional"},
    {"type": "year_ring",  "name": "年进度环",  "icon": "chart.svg",    "category": "functional"},
    {"type": "month_info", "name": "月/年进度",  "icon": "trending.svg", "category": "functional"},
    {"type": "todo_line",  "name": "待办提醒",   "icon": "clipboard.svg","category": "functional"},
    {"type": "divider",    "name": "分隔线",     "icon": "divider.svg",  "category": "decorative"},
]


class ComponentPalette(QWidget):
    """组件面板

    信号:
        item_requested(str) — 用户请求添加组件类型
    """
    item_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("componentPalette")
        self.setMaximumWidth(200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 标题
        title = QLabel("组件")
        title.setObjectName("paletteTitle")
        title.setStyleSheet("font-weight: bold; font-size: 13px; padding: 4px 0;")
        layout.addWidget(title)

        # 功能组件
        func_label = QLabel("功能组件")
        func_label.setStyleSheet("color: #888; font-size: 11px; padding: 4px 0;")
        layout.addWidget(func_label)

        for comp in BUILTIN_COMPONENTS:
            if comp["category"] != "functional":
                continue
            btn = QPushButton(f"  {comp['name']}")
            btn.setObjectName(f"paletteBtn_{comp['type']}")
            btn.setStyleSheet("text-align: left; padding: 6px 10px;")
            icon = load_svg_icon(comp.get("icon", ""), 14)
            if not icon.isNull():
                btn.setIcon(icon)
            btn.clicked.connect(lambda checked, t=comp["type"]: self.item_requested.emit(t))
            layout.addWidget(btn)

        # 分隔
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #555; margin: 8px 0;")
        layout.addWidget(sep)

        # 美观组件
        deco_label = QLabel("美观组件")
        deco_label.setStyleSheet("color: #888; font-size: 11px; padding: 4px 0;")
        layout.addWidget(deco_label)

        # 导入贴纸按钮
        sticker_btn = QPushButton("  导入贴纸 PNG")
        sticker_btn.setObjectName("importStickerBtn")
        sticker_btn.setStyleSheet("text-align: left; padding: 8px 10px; font-weight: bold;")
        sticker_icon = load_svg_icon("image.svg", 14)
        if not sticker_icon.isNull():
            sticker_btn.setIcon(sticker_icon)
        sticker_btn.clicked.connect(self._import_sticker)
        layout.addWidget(sticker_btn)

        layout.addStretch()

    def _import_sticker(self):
        """打开文件对话框选择 PNG 导入"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择贴纸图片", "", "PNG 图片 (*.png)"
        )
        if path:
            from src.utils.app_paths import AppPaths
            dest = AppPaths.import_sticker(path)
            if dest:
                # 通知画布添加贴纸
                self.item_requested.emit(f"sticker:{dest}")
