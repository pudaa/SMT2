from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QFrame, 
                               QListWidget, QListWidgetItem, QStackedWidget,
                               QApplication, QLabel, QPushButton, QSplitter,
                               QToolButton)
from PySide6.QtCore import Qt, QSize, Signal, QPoint, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QIcon, QPalette, QColor, QPainter, QPen


class Switch(QWidget):
    """自定义开关组件"""
    # 添加toggled信号
    toggled = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 26) 
        self.is_checked = False
        self.animation = QPropertyAnimation(self, b"geometry", self)
        self.animation.setDuration(200)  # 动画持续时间
        self.animation.setEasingCurve(QEasingCurve.InOutCubic)
        
    def paintEvent(self, event):
        """绘制开关"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 获取当前主题状态
        parent = self.parent()
        is_dark_theme = False
        while parent:
            if hasattr(parent, 'is_dark_theme'):
                is_dark_theme = parent.is_dark_theme
                break
            parent = parent.parent()
        
        # 绘制背景
        if self.is_checked:
            if is_dark_theme:
                painter.setBrush(QColor(100, 150, 255))  # 深色主题下开启状态的蓝色
            else:
                painter.setBrush(QColor(50, 120, 255))   # 浅色主题下开启状态的蓝色
        else:
            if is_dark_theme:
                painter.setBrush(QColor(80, 80, 80))  # 深色主题下关闭状态的灰色
            else:
                painter.setBrush(QColor(180, 180, 180))  # 浅色主题下关闭状态的灰色
        
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 13, 13)
        
        # 绘制滑块
        if is_dark_theme:
            painter.setBrush(QColor(240, 240, 240))  # 深色主题下的滑块颜色
        else:
            painter.setBrush(QColor(255, 255, 255))  # 浅色主题下的滑块颜色
            
        if self.is_checked:
            slider_x = self.width() - 24  # 开启状态下滑块位置
        else:
            slider_x = 4  # 关闭状态下滑块位置
            
        painter.drawEllipse(slider_x, 3, 20, 20)
    
    def mousePressEvent(self, event):
        """处理鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            self.toggle()
            return super().mousePressEvent(event)
    
    def toggle(self):
        """切换开关状态"""
        self.is_checked = not self.is_checked
        self.update()
        self.toggled.emit(self.is_checked)  # 发射信号
    
    def setChecked(self, checked):
        """设置开关状态"""
        if self.is_checked != checked:
            self.is_checked = checked
            self.update()
            self.toggled.emit(self.is_checked)  # 发射信号
    
    def isChecked(self):
        """获取开关状态"""
        return self.is_checked
