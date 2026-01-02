from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QFrame, 
                               QListWidget, QListWidgetItem, QStackedWidget,
                               QApplication, QLabel, QPushButton, QSplitter,
                               QToolButton)
from PySide6.QtCore import Qt, QSize, Signal, QPoint, QPropertyAnimation, QEasingCurve, QRect, Property
from PySide6.QtGui import QIcon, QPalette, QColor, QPainter, QPen


class Switch(QWidget):
    """自定义开关组件"""
    # 添加toggled信号
    toggled = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 26) 
        self._slider_position = 4  # 初始位置
        self.is_checked = False
        
        # 创建一个可动画的属性来控制滑块位置
        self.anim = QPropertyAnimation(self, b"slider_position")
        self.anim.setDuration(200)  # 动画持续时间
        self.anim.setEasingCurve(QEasingCurve.InOutCubic)
        
    def get_slider_position(self):
        return self._slider_position
        
    def set_slider_position(self, pos):
        self._slider_position = pos
        self.update()  # 更新界面以反映新位置
        
    # 使用PySide6的Property，这样QPropertyAnimation才能识别
    slider_position = Property(float, get_slider_position, set_slider_position)
    
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
            
        # 使用动画控制的滑块位置
        painter.drawEllipse(self._slider_position, 3, 20, 20)
    
    def mousePressEvent(self, event):
        """处理鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            self.toggle()
            return super().mousePressEvent(event)
    
    def toggle(self):
        """切换开关状态"""
        self.is_checked = not self.is_checked
        
        # 根据开关状态设置动画目标值
        if self.is_checked:
            self.anim.setStartValue(4)  # 关闭状态位置
            self.anim.setEndValue(self.width() - 24)  # 开启状态位置
        else:
            self.anim.setStartValue(self.width() - 24)  # 开启状态位置
            self.anim.setEndValue(4)  # 关闭状态位置
        
        self.anim.start()  # 启动动画
        self.toggled.emit(self.is_checked)  # 发射信号
    
    def setChecked(self, checked):
        """设置开关状态"""
        if self.is_checked != checked:
            self.is_checked = checked
            
            # 根据开关状态设置动画目标值
            if self.is_checked:
                self.anim.setStartValue(self._slider_position)
                self.anim.setEndValue(self.width() - 24)  # 开启状态位置
            else:
                self.anim.setStartValue(self._slider_position)
                self.anim.setEndValue(4)  # 关闭状态位置
            
            self.anim.start()  # 启动动画
            self.toggled.emit(self.is_checked)  # 发射信号
    
    def isChecked(self) -> bool:
        """获取开关状态"""
        return self.is_checked