from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QAction, QIcon, QPixmap, QColor


class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(QIcon("tray.png"))
        self.setToolTip("时间进度追踪")
        
        # 创建上下文菜单
        self.menu = QMenu()
        
        self.performance_action = QAction("Performance monitoring mode", None)
        self.performance_action.setCheckable(True)
        self.performance_action.triggered.connect(self.toggle_performance_mode)
        self.menu.addAction(self.performance_action)
        
        self.menu.addSeparator()
        
        exit_action = QAction("退出", None)
        exit_action.triggered.connect(QApplication.quit)
        self.menu.addAction(exit_action)
        
        self.setContextMenu(self.menu)
        
    def toggle_performance_mode(self):
        # 获取父窗口并切换模式
        widget = self.parent()
        if hasattr(widget, 'toggle_mode'):
            widget.toggle_mode()
            if hasattr(widget, 'performance_panel'):
                self.performance_action.setChecked(widget.performance_panel.performance_mode)
            elif hasattr(widget, 'main_widget'):
                self.performance_action.setChecked(widget.main_widget.performance_panel.performance_mode)