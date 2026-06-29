"""
SVG 图标加载工具

统一封装图标加载逻辑：
- load_svg_pixmap(filename, size) → QPixmap（用于 QLabel、QPainter）
- load_svg_icon(filename, size)  → QIcon（用于 QPushButton、QAction）
"""

from __future__ import annotations
import os
from PySide6.QtGui import QPixmap, QPainter, QIcon
from PySide6.QtCore import Qt
from PySide6.QtSvg import QSvgRenderer
from src.utils.app_paths import AppPaths


def _get_svg_path(filename: str) -> str:
    """返回 SVG 文件的完整路径"""
    return AppPaths.get_resource(os.path.join("icons", filename))


def load_svg_pixmap(filename: str, size: int = 16) -> QPixmap:
    """加载 SVG 文件为 QPixmap，支持透明背景"""
    path = _get_svg_path(filename)
    if not os.path.exists(path):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        return pixmap

    renderer = QSvgRenderer(path)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


def load_svg_icon(filename: str, size: int = 16) -> QIcon:
    """加载 SVG 文件为 QIcon（SVG 是矢量的，size 仅作为提示）"""
    icon = QIcon(_get_svg_path(filename))
    return icon
