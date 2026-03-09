from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication
from PySide6.QtGui import QMouseEvent, QEvent, QShowEvent, QMoveEvent, QPainter, QColor, QFont
from PySide6.QtCore import QTimer, Qt, QSize, QPoint, QPropertyAnimation, QEasingCurve, Property, QRect, QParallelAnimationGroup, QSequentialAnimationGroup
from src.views.main_views.performance_panel import PerformancePanel
from src.views.main_views.todo_panel import TodoPanel, TodoItemWidget
from src.utils.performance_monitor import PerformanceMonitor
import sys
import ctypes

class EmbeddedPanel(QWidget):
    """嵌入模式下的简化面板，只显示时间"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(250, 45)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.time_str = ""
        
    def set_time(self, time_str):
        self.time_str = time_str
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景（圆角矩形）
        painter.setBrush(QColor(50, 50, 50, 200))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 10, 10)
        
        # 绘制阴影
        painter.setBrush(QColor(0, 0, 0, 80))
        painter.drawRoundedRect(2, 2, self.width()-4, self.height()-4, 10, 10)
        
        # 绘制时间（居中显示）
        painter.setPen(QColor(200, 200, 200))
        font = QFont("Microsoft YaHei UI", 14, QFont.Bold)
        painter.setFont(font)
        
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(self.time_str)
        x = (self.width() - text_width) // 2
        y = self.height() // 2 + metrics.height() // 3
        
        painter.drawText(x, y, self.time_str)

