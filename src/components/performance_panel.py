from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QFont, QPen
from PySide6.QtCore import Qt, QTimer
from datetime import datetime
from src.utils.performance_monitor import PerformanceMonitor

class PerformancePanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(250, 90)
        self.setAttribute(Qt.WA_TranslucentBackground) 
        
        # 性能数据
        self.cpu_percent = 0
        self.memory_percent = 0
        self.gpu_percent = 0
        self.battery_percent = 100
        
        # 时间进度数据
        self.day_progress = 0
        self.week_progress = 0
        self.month_progress = 0
        self.year_progress = 0
        
        # 模式切换
        self.performance_mode = False
        
        # 性能监控定时器（仅在性能模式下运行）
        self.performance_timer = QTimer(self)
        self.performance_timer.timeout.connect(self.update_performance_data)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        painter.setBrush(QColor(50, 50, 50, 200))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 15, 15)
        
        # 绘制阴影
        painter.setBrush(QColor(0, 0, 0, 80))
        painter.drawRoundedRect(3, 3, self.width()-6, self.height()-6, 15, 15)
        
        # 绘制时间
        painter.setPen(QColor(200, 200, 200))
        font = QFont("Microsoft YaHei UI", 9)
        painter.setFont(font)
        time_str = datetime.now().strftime("%H:%M:%S")
        painter.drawText(100, 15, time_str)
        
        if self.performance_mode:
            # 绘制性能指标
            self.draw_progress_ring(painter, 10, self.cpu_percent, "CPU", "CPU")
            self.draw_progress_ring(painter, 70, self.memory_percent, "内存", "内存")
            self.draw_progress_ring(painter, 130, self.gpu_percent, "GPU", "GPU")
            self.draw_progress_ring(painter, 190, self.battery_percent, "电池", "电池")
        else:
            # 绘制时间进度
            day_text = datetime.now().strftime("%d日")
            weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
            week_text = weekday_names[datetime.now().weekday()]
            month_text = datetime.now().strftime("%m月")
            year_text = datetime.now().strftime("%Y年")
            
            self.draw_progress_ring(painter, 10, self.day_progress, "Day", day_text)
            self.draw_progress_ring(painter, 70, self.week_progress, "Week", week_text)
            self.draw_progress_ring(painter, 130, self.month_progress, "Month", month_text)
            self.draw_progress_ring(painter, 190, self.year_progress, "Year", year_text)
            
    def draw_progress_ring(self, painter, x, progress, title, value):
        # 设置字体
        title_font = QFont("Microsoft YaHei UI", 8, QFont.Bold)
        value_font = QFont("Microsoft YaHei UI", 8, QFont.Bold)
        
        # 计算百分比文本
        percentage = f"{round(progress * 100)}%"
        
        # 圆环参数
        diameter = 50
        y = 20
        
        # 绘制背景环
        pen = QPen(QColor(70, 70, 70, 150))
        pen.setWidth(2.5)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawEllipse(x, y, diameter, diameter)
        
        # 绘制进度弧
        pen.setColor(QColor(200, 200, 200))
        painter.setPen(pen)
        span_angle = int(360 * progress * 16)
        painter.drawArc(x, y, diameter, diameter, 90 * 16, -span_angle)
        
        # 绘制标题文本
        painter.setFont(title_font)
        painter.setPen(QColor(200, 200, 200))
        metrics = painter.fontMetrics()
        title_width = metrics.horizontalAdvance(value)
        painter.drawText(x + (diameter - title_width) // 2, y + diameter + 14, value)
        
        # 绘制数值文本
        painter.setFont(value_font)
        painter.setPen(QColor(200, 200, 200))
        metrics = painter.fontMetrics()
        value_width = metrics.horizontalAdvance(percentage)
        painter.drawText(x + (diameter - value_width) // 2, y + diameter // 2 + 5, percentage)
        
    def toggle_mode(self):
        self.performance_mode = not self.performance_mode
        
        if self.performance_mode:
            self.performance_timer.start(1000)
        else:
            self.performance_timer.stop()
            
        self.update()
        
    def update_performance_data(self):
        """仅在性能模式下更新性能数据"""
        if self.performance_mode:
            self.cpu_percent = PerformanceMonitor.get_cpu_percent()
            self.memory_percent = PerformanceMonitor.get_memory_percent()
            self.gpu_percent = PerformanceMonitor.get_gpu_percent()
            self.battery_percent = PerformanceMonitor.get_battery_percent()
            self.update()
            
    def update_time_data(self):
        """更新时间数据（始终运行）"""
        self.day_progress = PerformanceMonitor.get_day_progress()
        self.week_progress = PerformanceMonitor.get_week_progress()
        self.month_progress = PerformanceMonitor.get_month_progress()
        self.year_progress = PerformanceMonitor.get_year_progress()