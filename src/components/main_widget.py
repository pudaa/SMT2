from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication
from PySide6.QtGui import QMouseEvent, QShowEvent
from PySide6.QtCore import  QTimer, Qt, QPoint, QPropertyAnimation, QEasingCurve, Property
from src.components.performance_panel import PerformancePanel
from src.components.todo_panel import TodoPanel, TodoItemWidget
from src.utils.performance_monitor import PerformanceMonitor
import sys
import ctypes

class MainWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SMT2") 
        self.setFixedSize(250, 90)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint  | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 性能面板
        self.performance_panel = PerformancePanel()
        main_layout.addWidget(self.performance_panel)
        
        # 待办面板
        self.todo_panel = TodoPanel()
        self.todo_panel.setFixedHeight(200)
        main_layout.addWidget(self.todo_panel)
        self.todo_panel.setVisible(False)
        
        # 鼠标拖动相关
        self.drag_position = QPoint()
        
        # 定时器更新时间数据
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time_data)
        self.timer.start(1000)  # 每秒更新一次
        
        # 动画
        self.animation = QPropertyAnimation(self, b"todo_height")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        
        # 更新初始数据
        self.update_time_data()
    
    def showEvent(self, event: QShowEvent):
        super().showEvent(event)
        self.raise_()
        self.activateWindow()
        self.force_foreground()
    
    def force_foreground(self):
        if sys.platform == "win32":
            try:
                hwnd = int(self.winId())
                ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception as e:
                print("无法强制窗口到前台:", e)
                
    def get_todo_height(self):
        return self.todo_panel.height() if self.todo_panel.isVisible() else 0
        
    def set_todo_height(self, height):
        self.todo_panel.setFixedHeight(height)
        self.setFixedHeight(90 + height)
        
    todo_height = Property(int, get_todo_height, set_todo_height)
        
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.RightButton:
            self.toggle_todo_panel()
            
    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton and self.performance_panel.geometry().contains(event.pos()):
            if self.todo_panel.is_dragging == False:
                self.move(event.globalPosition().toPoint() - self.drag_position)
                event.accept()
            
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            if self.performance_panel.geometry().contains(event.pos()):
                QApplication.quit()
            
    def toggle_todo_panel(self):
        self.todo_panel.todo_visible = not self.todo_panel.todo_visible
        
        if self.todo_panel.todo_visible:
            # 显示待办面板
            self.todo_panel.setVisible(True)
            self.animation.setStartValue(0)
            self.animation.setEndValue(200)
        else:
            # 隐藏待办面板
            self.animation.setStartValue(200)
            self.animation.setEndValue(0)
            self.animation.finished.connect(self.hide_todo_panel)
            
        self.animation.start()
        
        # 更新待办列表
        if self.todo_panel.todo_visible:
            self.todo_panel.update_todo_list()
            
    def hide_todo_panel(self):
        self.todo_panel.setVisible(False)
        try:
            self.animation.finished.disconnect(self.hide_todo_panel)
        except RuntimeError:
            pass

    def update_time_data(self):
        self.performance_panel.update_time_data()
        if not self.performance_panel.performance_mode:
            self.performance_panel.update()
        
    def toggle_mode(self):
        self.performance_panel.toggle_mode()