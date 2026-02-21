import os
from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QProgressDialog
import ctypes
from PySide6.QtGui import QColor
import functools
import platform

class ThemeManager(QObject):
    def __init__(self):
        super().__init__()
        self.is_dark_theme = False
        self.light_theme = self._load_theme("light")
        self.dark_theme = self._load_theme("dark")
        self._initialized = False
        self._patched_dialogs = set()  # 记录已处理的对话框类型
        
    def initialize(self):
        """初始化主题管理器"""
        if not self._initialized:
            self._patch_qt_dialogs()
            self._initialized = True
            
    def _patch_qt_dialogs(self):
        # 保存原始方法
        original_information = QMessageBox.information
        original_critical = QMessageBox.critical
        original_warning = QMessageBox.warning
        original_question = QMessageBox.question
        
        # 创建包装函数
        def themed_message_box(original_func, icon):
            @functools.wraps(original_func)
            def wrapper(*args, **kwargs):
                # 创建 QMessageBox 实例
                msg_box = QMessageBox(*args, **kwargs)
                msg_box.setIcon(icon)
                # 显示对话框并应用主题
                QTimer.singleShot(0, lambda: self.apply_theme_to_window(msg_box))
                return msg_box.exec()
            return wrapper
        
        # 替换原始方法
        QMessageBox.information = themed_message_box(original_information, QMessageBox.Information)
        QMessageBox.critical = themed_message_box(original_critical, QMessageBox.Critical)
        QMessageBox.warning = themed_message_box(original_warning, QMessageBox.Warning)
        QMessageBox.question = themed_message_box(original_question, QMessageBox.Question)
        
        # 处理QProgressDialog
        original_progress_dialog = QProgressDialog.__init__
        def themed_progress_dialog_init(self, *args, **kwargs):
            original_progress_dialog(self, *args, **kwargs)
            QTimer.singleShot(0, lambda: self.setProperty('_themed', True))
        QProgressDialog.__init__ = themed_progress_dialog_init
        
    
    def _load_theme(self, theme_name):
        """从文件加载主题样式"""
        theme_file = f"resources/themes/{theme_name}_theme.qss"
        
        # 尝试从当前工作目录加载
        if os.path.exists(theme_file):
            with open(theme_file, "r", encoding="utf-8") as f:
                return f.read()
        else:
            # 如果文件不存在，返回空字符串
            return ""
    
    def get_current_theme(self):
        """获取当前主题样式"""
        if self.is_dark_theme:
            return self.dark_theme
        else:
            return self.light_theme
    
    def toggle_theme(self):
        """切换主题"""
        self.is_dark_theme = not self.is_dark_theme
        return self.get_current_theme()
    
    def set_dark_theme(self):
        """设置深色主题"""
        self.is_dark_theme = True
        return self.dark_theme
    
    def set_light_theme(self):
        """设置浅色主题"""
        self.is_dark_theme = False
        return self.light_theme
            
    def apply_theme_to_window(self, window):
        """为窗口应用主题"""
        if not window or not hasattr(window, 'winId'):
            return
            
        try:
            hwnd = window.winId()
            if hwnd is None:
                return
                
            # 设置深色模式
            dark_mode_value = 1 if self.is_dark_theme else 0
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                20,  # DWMWA_USE_IMMERSIVE_DARK_MODE
                ctypes.byref(ctypes.c_int(dark_mode_value)),
                ctypes.sizeof(ctypes.c_int)
            )
            
            # 仅在 Windows 11 及以上版本设置标题栏颜色
            if platform.release() >= '10.0.22000':  # Windows 11 版本号
                if self.is_dark_theme:
                    color = QColor("#1a1a1a")  # 深灰色
                else:
                    color = QColor("#ffffff")  # 白色
                    
                color_ref = (color.red() << 0) | (color.green() << 8) | (color.blue() << 16)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    35,  # DWMWA_CAPTION_COLOR
                    ctypes.byref(ctypes.c_uint(color_ref)),
                    ctypes.sizeof(ctypes.c_uint)
                )
            
        except Exception as e:
            print(f"应用主题到窗口失败: {e}")
            
    def apply_theme_to_all_windows(self):
        """为所有可见窗口应用主题"""
        app = QApplication.instance()
        if app:
            for window in app.topLevelWidgets():
                if window.isVisible():
                    self.apply_theme_to_window(window)