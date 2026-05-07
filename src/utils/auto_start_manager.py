import winreg
import sys
import os
import shlex
import logging

logger = logging.getLogger(__name__)


class AutoStartManager:
    """Windows 开机自启管理器
    
    Nuitka 打包兼容说明：
    - Nuitka --onefile 模式下，sys.frozen 和 __compiled__ 均会被设置
    - sys.argv[0] 指向用户双击的原始 .exe 路径（即使改名后也是正确的新名字）
    - sys.executable 在 onefile 下也指向原始 .exe（与 argv[0] 一致）
    """
    
    def __init__(self):
        self.app_name = "SMT2"
        self.reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        # 计算并缓存当前 exe 的规范化绝对路径
        self.file_path = self._resolve_exe_path()
    
    @staticmethod
    def _is_packaged() -> bool:
        """检测是否为打包后的环境（兼容 Nuitka / PyInstaller）"""
        return getattr(sys, 'frozen', False) or getattr(sys, '_MEIPASS', False)
    
    def _resolve_exe_path(self) -> str:
        """获取要写入注册表的完整命令行。
        
        返回值应 Windows 可直接在 Run 键中执行的命令行：
        - 打包后：exe 路径本身（含空格时自动加引号）
        - 开发环境：pythonw.exe + 脚本路径，各自独立引号（避免弹出控制台窗口）
        """
        try:
            if self._is_packaged():
                # 打包后：argv[0] 就是用户启动的 exe 路径（即使改名也正确）
                candidate = sys.argv[0] if sys.argv and sys.argv[0] else sys.executable
                return self._quote_path(os.path.normcase(os.path.abspath(candidate)))
            else:
                # 开发环境：构造 pythonw.exe + 脚本路径的完整命令行
                script = sys.argv[0] if sys.argv and sys.argv[0] else ''
                script_abs = os.path.normcase(os.path.abspath(script))
                
                if sys.executable.lower().endswith('python.exe'):
                    pythonw = sys.executable[:-10] + 'pythonw.exe'
                    if os.path.isfile(pythonw):
                        pythonw_abs = os.path.normcase(os.path.abspath(pythonw))
                        # 分别对每个路径独立加引号
                        return self._quote_path(pythonw_abs) + ' ' + self._quote_path(script_abs)
                
                # 回退：直接返回脚本路径
                return self._quote_path(script_abs)
        except Exception:
            try:
                return self._quote_path(os.path.normcase(os.path.abspath(sys.executable)))
            except Exception:
                return self._quote_path(os.path.normcase(os.path.abspath(sys.argv[0] if sys.argv else '')))

    @staticmethod
    def _quote_path(path: str) -> str:
        """如果路径包含空格则用双引号包裹，否则原样返回"""
        if ' ' in path and not (path.startswith('"') and path.endswith('"')):
            return '"' + path + '"'
        return path
    
    @staticmethod
    def _extract_exe_path_from_registry(reg_value: str) -> str:
        r"""从注册表值中提取可执行文件路径。
        
        注册表中的值可能是：
        - "C:\Program Files\App\app.exe"          （带引号的纯路径）
        - "C:\Program Files\App\app.exe" --arg    （带引号的路径+参数）
        - C:\App\app.exe                          （无引号的纯路径）
        
        使用 shlex.split(posix=False) 在 Windows 上正确解析，避免路径中空格导致的截断，
        同时避免反斜杠被当作 POSIX 转义字符。
        返回规范化后的纯路径（不含参数和引号）。
        """
        if not isinstance(reg_value, str):
            return os.path.normcase(os.path.abspath(str(reg_value)))
        
        value = reg_value.strip()
        if not value:
            return ''
        
        try:
            # posix=False：Windows 模式下反斜杠不会被当作转义字符
            parts = shlex.split(value, posix=False)
        except ValueError:
            # shlex 解析失败时，手动处理：去掉外层引号
            if value.startswith('"'):
                end_quote = value.find('"', 1)
                if end_quote != -1:
                    return os.path.normcase(os.path.abspath(value[1:end_quote]))
            return os.path.normcase(os.path.abspath(value))
        
        if not parts:
            return ''
        
        # posix=False 时引号可能被保留，需要手动去掉
        exe = parts[0].strip('"')
        return os.path.normcase(os.path.abspath(exe))
    
    def is_auto_start_enabled(self) -> bool:
        """检查是否已启用开机自启"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.reg_path, 0, winreg.KEY_READ)
            try:
                value, _ = winreg.QueryValueEx(key, self.app_name)
            except OSError:
                return False
            finally:
                winreg.CloseKey(key)
            
            reg_exe_path = self._extract_exe_path_from_registry(value)
            my_exe_path = self._extract_exe_path_from_registry(self.file_path)

            result = reg_exe_path == my_exe_path
            if not result:
                logger.debug(f"开机自启路径不匹配: 注册表={reg_exe_path}, 当前={my_exe_path}")
            return result
        except OSError as e:
            logger.debug(f"检查开机自启失败: {e}")
            return False
    
    def enable_auto_start(self):
        r"""启用开机自启
        
        向 HKCU\Software\Microsoft\Windows\CurrentVersion\Run 写入当前 exe 路径。
        路径含空格时 _resolve_exe_path 已自动添加双引号包裹。
        """
        try:
            key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, self.reg_path, 0, winreg.KEY_SET_VALUE)
            # file_path 已由 _resolve_exe_path 正确格式化（含引号），直接写入
            winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, self.file_path)
            winreg.CloseKey(key)
            
            # 验证写入是否成功
            if self.is_auto_start_enabled():
                logger.info(f"开机自启已启用: {self.file_path}")
                return True
            else:
                logger.warning(f"开机自启写入后验证失败: {self.file_path}")
                return False
        except OSError as e:
            logger.error(f"启用自启失败：{e}")
            return False
    
    def disable_auto_start(self):
        """禁用开机自启"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.reg_path, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, self.app_name)
            winreg.CloseKey(key)
            logger.info("开机自启已禁用")
            return True
        except FileNotFoundError:
            return True
        except OSError as e:
            logger.error(f"禁用自启失败：{e}")
            return False
    
    def toggle_auto_start(self, enable: bool):
        """切换开机自启状态"""
        if enable:
            return self.enable_auto_start()
        else:
            return self.disable_auto_start()