from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QAction, QIcon, QPixmap, QColor
from PySide6.QtCore import QObject, Signal, Slot
from src.utils.win_pin import WindowPinner
from src.views.toolbox_views.toolbox_window import ToolBoxWindow


class MenuUpdater(QObject):
    """用于在线程安全环境下更新菜单的辅助类"""
    update_signal = Signal()
    
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.update_signal.connect(self._update_menu)
    
    @Slot()
    def _update_menu(self):
        self.callback()


class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(QIcon("resources/tray.png"))
        self.setToolTip("时间进度追踪")
        
        # 创建上下文菜单
        self.menu = QMenu()
        
        self.performance_action = QAction("性能监控模式", None)
        self.performance_action.setCheckable(True)
        self.performance_action.triggered.connect(self.toggle_performance_mode)
        self.menu.addAction(self.performance_action)
        
        self.menu.addSeparator()
        
        # 窗口置顶功能
        self.win_pin = WindowPinner()
        self.win_pin_action = QAction("窗口置顶", self.menu)
        self.win_pin_menu = QMenu()
        self.win_pin_action.setMenu(self.win_pin_menu)
        self.menu.addAction(self.win_pin_action)
        self.update_win_pin_menu()
        
        # 创建线程安全的菜单更新器
        self.menu_updater = MenuUpdater(self.update_win_pin_menu)
        self.win_pin.start_auto_refresh(self.menu_updater.update_signal.emit)
        
        self.menu.addSeparator()
        
        # ---- 主题切换 ----
        self.theme_menu = QMenu("切换主题")
        self._theme_actions = []
        self._build_theme_menu()
        self.menu.addMenu(self.theme_menu)
        
        self.menu.addSeparator()
        
        # 工具箱
        self.tools_action = QAction("工具箱", None)
        self.tools_action.triggered.connect(self.open_toolbox)
        self.menu.addAction(self.tools_action)
        
        self.exit_action = QAction("退出", None)
        self.exit_action.triggered.connect(QApplication.quit)
        self.menu.addAction(self.exit_action)
        
        self.setContextMenu(self.menu)
        
        self.pin_self_on_init()
        
        self.toolbox_window = None
    
    def pin_self_on_init(self):
        """在初始化后置顶本程序窗口"""
        windows = self.win_pin.get_window_list()
        
        for hwnd, title in windows:
            if title.strip() == "SMT2":
                self.win_pin.toggle_pin(hwnd)
                break
    
    def open_toolbox(self):
        """打开工具箱窗口"""
        if self.toolbox_window is None:
            self.toolbox_window = ToolBoxWindow()
        
        # 显示窗口并将其置于前台
        self.toolbox_window.show()
        self.toolbox_window.raise_()
        self.toolbox_window.activateWindow()
    
    def toggle_performance_mode(self):
        widget = self.parent()
        if hasattr(widget, 'toggle_mode'):
            widget.toggle_mode()
            if hasattr(widget, 'performance_panel'):
                self.performance_action.setChecked(widget.performance_panel.performance_mode)
            elif hasattr(widget, 'main_widget'):
                self.performance_action.setChecked(widget.main_widget.performance_panel.performance_mode)
    
    def _build_theme_menu(self):
        """动态构建主题切换菜单（含自定义主题）"""
        from src.themes import theme_manager
        
        self._theme_actions.clear()
        self.theme_menu.clear()
        
        for theme_info in theme_manager.available_themes:
            name = theme_info["name"]
            display = theme_info["display"]
            is_custom = theme_info.get("is_custom", False)
            label = f"{display} *" if is_custom else display
            action = QAction(label, self.theme_menu)
            action.setCheckable(True)
            action.setChecked(name == theme_manager.current_theme_name)
            action.triggered.connect(lambda checked, t=name: self._switch_theme(t))
            self.theme_menu.addAction(action)
            self._theme_actions.append(action)
    
    def _switch_theme(self, theme_name: str):
        """切换主题并刷新菜单勾选状态"""
        from src.themes import theme_manager
        if theme_manager.set_theme(theme_name):
            # 刷新菜单勾选
            for action, info in zip(self._theme_actions, theme_manager.available_themes):
                action.setChecked(info["name"] == theme_manager.current_theme_name)
            # 刷新整个应用样式
            app = QApplication.instance()
            if app:
                ss = theme_manager.get_stylesheet()
                if ss:
                    app.setStyleSheet(ss)
                else:
                    app.setStyleSheet("")
    
    def update_win_pin_menu(self):
        # 清除现有动作
        self.win_pin_menu.clear()
        
        windows = self.win_pin.get_window_list()
        
        if not windows:
            no_windows_action = QAction("暂无可用窗口", self.win_pin_menu)
            no_windows_action.setEnabled(False)
            self.win_pin_menu.addAction(no_windows_action)
        else:
            for hwnd, title in windows:
                display_title = title[:30] + "..." if len(title) > 30 else title
                action = QAction(display_title, self.win_pin_menu)
                action.setCheckable(True)
                action.setChecked(self.win_pin.is_pinned(hwnd))
                action.triggered.connect(lambda checked, h=hwnd: self.win_pin.toggle_pin(h))
                self.win_pin_menu.addAction(action)