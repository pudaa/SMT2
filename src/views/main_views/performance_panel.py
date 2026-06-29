from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter
from PySide6.QtCore import Qt, QTimer, Signal
from src.utils.performance_monitor import PerformanceMonitor
from src.themes import theme_manager

class PerformancePanel(QWidget):
    """性能/时间进度面板
    
    支持三种显示模式:
      - normal  : 常规模式
      - compact : 紧凑模式
      - mini    : 极简模式，仅显示时间
    
    绘制逻辑完全委托给当前主题的 paint_panel()，
    使得不同主题可以实现完全不同的布局。
    """
    
    mode_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # ---- 面板模式 ----
        self._panel_mode: str = "normal"
        
        # 性能数据
        self.cpu_percent = 0
        self.memory_percent = 0
        self.disk_percent = 0
        self.battery_percent = 100
        
        # 时间进度数据
        self.day_progress = 0
        self.week_progress = 0
        self.month_progress = 0
        self.year_progress = 0
        
        # 显示模式 (性能 vs 时间进度)
        self.performance_mode = False
        
        # 首个待办事项文本（由 MainWidget 更新）
        self.first_todo_text: str = ""
        
        # 性能监控定时器
        self.performance_timer = QTimer(self)
        self.performance_timer.timeout.connect(self.update_performance_data)
        
        # 应用初始尺寸
        self._apply_metrics()
        
        # 监听主题切换
        theme_manager.add_listener(self._on_theme_changed)

    # ================================================================
    # 尺寸管理
    # ================================================================
    
    def _apply_metrics(self):
        m = theme_manager.get_panel_metrics(self._panel_mode)
        self.setFixedSize(m.panel_width, m.panel_height)
        self.update()

    def _resolve_metrics(self):
        """供主题 paint_panel 查询当前尺寸指标"""
        return theme_manager.get_panel_metrics(self._panel_mode)

    @property
    def panel_mode(self) -> str:
        return self._panel_mode

    def set_panel_mode(self, mode: str):
        if mode == self._panel_mode:
            return
        self._panel_mode = mode
        self._apply_metrics()
        self.mode_changed.emit(mode)

    def cycle_panel_mode(self):
        order = ["normal", "compact", "mini"]
        idx = order.index(self._panel_mode) if self._panel_mode in order else 0
        next_mode = order[(idx + 1) % len(order)]
        self.set_panel_mode(next_mode)

    # ================================================================
    # 待办事项接口
    # ================================================================
    
    def set_first_todo_text(self, text: str):
        """设置首个待办事项文本（用于现代主题的底部提醒）"""
        if text != self.first_todo_text:
            self.first_todo_text = text
            self.update()

    # ================================================================
    # 主题响应
    # ================================================================
    
    def _on_theme_changed(self, theme_name: str):
        self._apply_metrics()

    # ================================================================
    # 绘制 —— 完全委托给主题
    # ================================================================
    
    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            theme_manager.current_theme.paint_panel(painter, self)
        finally:
            painter.end()  # 确保 painter 正确关闭，防止 QBackingStore 报错

    # ================================================================
    # 模式切换
    # ================================================================
    
    def toggle_mode(self):
        self.performance_mode = not self.performance_mode
        if self.performance_mode:
            self.performance_timer.start(1000)
        else:
            self.performance_timer.stop()
        self.update()
        
    # ================================================================
    # 数据更新
    # ================================================================
    
    def update_performance_data(self):
        if self.performance_mode:
            self.cpu_percent = PerformanceMonitor.get_cpu_percent()
            self.memory_percent = PerformanceMonitor.get_memory_percent()
            self.disk_percent = PerformanceMonitor.get_disk_percent()[0]
            self.battery_percent = PerformanceMonitor.get_battery_percent()
            self.update()
            
    def update_time_data(self):
        self.day_progress = PerformanceMonitor.get_day_progress()
        self.week_progress = PerformanceMonitor.get_week_progress()
        self.month_progress = PerformanceMonitor.get_month_progress()
        self.year_progress = PerformanceMonitor.get_year_progress()