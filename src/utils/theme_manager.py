import os
from PySide6.QtCore import QObject


class ThemeManager(QObject):
    def __init__(self):
        super().__init__()
        self.is_dark_theme = False
        self.light_theme = self._load_theme("light")
        self.dark_theme = self._load_theme("dark")
    
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