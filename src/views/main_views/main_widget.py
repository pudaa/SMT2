from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication
from PySide6.QtGui import QMouseEvent, QShowEvent, QMoveEvent
from PySide6.QtCore import  QTimer, Qt, QPoint, QPropertyAnimation, QEasingCurve, Property, QRect
from src.views.main_views.performance_panel import PerformancePanel
from src.views.main_views.todo_panel import TodoPanel, TodoItemWidget
from src.utils.performance_monitor import PerformanceMonitor
import sys
import ctypes

class MainWidget(QWidget):
    '''主窗口，也是控制器'''
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
        
        # 吸附相关
        self.snap_margin = 8  # 吸附阈值（像素）- 减小阈值，只在很靠近边缘时吸附
        self.embed_offset = 1  # 嵌入偏移量（像素），防止遮挡
        self.is_snapped = False
        self.last_snap_region = None  # 记录最后吸附的区域
        self.snap_keep_pos = False  # 是否保持当前位置（用于上下边缘吸附时保持水平位置）
        self.saved_x = 0  # 保存拖动时的 x 坐标
        self.saved_y = 0  # 保存拖动时的 y 坐标
        
        # 位置动画
        self.pos_animation = QPropertyAnimation(self, b"pos")
        self.pos_animation.setDuration(200)
        self.pos_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        
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
        
    todo_height = Property(int, get_todo_height, set_todo_height) #  待办面板高度
        
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.break_snap()
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept() # 处理鼠标按下事件
        elif event.button() == Qt.RightButton:
            self.toggle_todo_panel()
            
    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton and self.performance_panel.geometry().contains(event.pos()):
            self.todo_panel.is_dragging = True
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
            
    def mouseReleaseEvent(self, event: QMouseEvent):
        QTimer.singleShot(100, self.check_snap)  # 延迟检查，避免拖动中频繁触发
        if event.button() == Qt.LeftButton: 
            QTimer.singleShot(100, self.reset_dragging) # 延迟重置拖动状态，避免拖动中频繁触发吸附检查
            event.accept()
                
    def reset_dragging(self):
        self.todo_panel.is_dragging = False
            
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
        
    
    def moveEvent(self, event: QMoveEvent):
        super().moveEvent(event)
        # 拖动结束后检查是否需要吸附
        if not self.is_snapped and not self.todo_panel.is_dragging: # 在没有吸附并且窗口不在拖拽时，才检查
            QTimer.singleShot(100, self.check_snap)  # 延迟检查，避免拖动中频繁触发
    
    def check_snap(self):
        """检查窗口是否应该吸附到屏幕边缘"""
        screen = QApplication.screenAt(self.geometry().center())
        if not screen:
            screen = QApplication.primaryScreen()
        
        screen_geo = screen.availableGeometry()
        window_geo = self.geometry() # 获取窗口的 geometry，包含窗口标题栏和边框
        
        snap_regions = []
        
        # 检测左边缘
        if abs(window_geo.left() - screen_geo.left()) <= self.snap_margin or window_geo.left() < screen_geo.left():
            snap_regions.append("left")
        # 检测右边缘
        if abs(window_geo.right() - screen_geo.right()) <= self.snap_margin or window_geo.right() > screen_geo.right():
            snap_regions.append("right")
        # 检测上边缘
        if abs(window_geo.top() - screen_geo.top()) <= self.snap_margin or window_geo.top() < screen_geo.top():
            snap_regions.append("top")
        # 检测下边缘
        if abs(window_geo.bottom() - screen_geo.bottom()) <= self.snap_margin or window_geo.bottom() > screen_geo.bottom():
            snap_regions.append("bottom")
        
        if snap_regions and snap_regions != self.last_snap_region:
            self.snap_to_edge(screen_geo, snap_regions)
            self.last_snap_region = snap_regions
        elif not snap_regions:
            self.last_snap_region = None
    
    def snap_to_edge(self, screen_geo: QRect, regions: list):
        """将窗口吸附到指定边缘并嵌入，支持多个边缘（拐角）"""
        current_pos = self.pos()
        target_x = current_pos.x()
        target_y = current_pos.y()
        
        # 水平方向吸附
        if "left" in regions:
            target_x = screen_geo.left() - self.embed_offset
            
        if "right" in regions:
            target_x = screen_geo.right() - self.width() + self.embed_offset
        
        # 垂直方向吸附
        if "top" in regions:
            target_y = screen_geo.top() - self.embed_offset
            
        if "bottom" in regions:
            target_y = screen_geo.bottom() - self.height() + self.embed_offset
        
        target_pos = QPoint(target_x, target_y)
        
        # 使用动画平滑移动到新位置
        self.pos_animation.stop()
        self.pos_animation.setStartValue(self.pos())
        self.pos_animation.setEndValue(target_pos)
        self.pos_animation.start()
        self.is_snapped = True
    
    def break_snap(self):
        """解除吸附状态"""
        self.is_snapped = False
        self.last_snap_region = None