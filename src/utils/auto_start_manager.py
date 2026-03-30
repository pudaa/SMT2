import winreg
import sys
import os


class AutoStartManager:
    """Windows 开机自启管理器"""
    
    def __init__(self):
        self.app_name = "SMT2"
        if sys.executable.endswith('python.exe'):
            self.file_path = sys.executable.replace('python.exe', 'pythonw.exe') + ' ' + os.path.abspath(sys.argv[0])
        else:
            self.file_path = os.path.abspath(sys.argv[0])
        self.reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    
    def is_auto_start_enabled(self) -> bool:
        """检查是否已启用开机自启"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.reg_path, 0, winreg.KEY_READ)
            try:
                value, _ = winreg.QueryValueEx(key, self.app_name)
                winreg.CloseKey(key)
                
                current_file_path = self._get_current_file_path()
                file_path_without_args = current_file_path.split(' ')[0] if ' ' in current_file_path else current_file_path
                value_path = value.split(' ')[0] if ' ' in value else value
                
                return file_path_without_args == value_path
            except WindowsError:
                winreg.CloseKey(key)
                return False
        except WindowsError:
            return False
    
    def _get_current_file_path(self):
        """获取当前的文件路径"""
        if sys.executable.endswith('python.exe'):
            return sys.executable.replace('python.exe', 'pythonw.exe') + ' ' + os.path.abspath(sys.argv[0])
        else:
            return os.path.abspath(sys.argv[0])
    
    def enable_auto_start(self):
        """启用开机自启"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.reg_path, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, self.file_path)
            winreg.CloseKey(key)
            
            import time
            time.sleep(0.1)
            
            return True
        except WindowsError as e:
            print(f"启用自启失败：{e}")
            return False
    
    def disable_auto_start(self):
        """禁用开机自启"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.reg_path, 0, winreg.KEY_WRITE)
            winreg.DeleteValue(key, self.app_name)
            winreg.CloseKey(key)
            return True
        except WindowsError as e:
            if e.winerror == 2:
                return True
            else:
                print(f"禁用自启失败：{e}")
                return False
    
    def toggle_auto_start(self, enable: bool):
        """切换开机自启状态"""
        if enable:
            return self.enable_auto_start()
        else:
            return self.disable_auto_start()