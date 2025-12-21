# win_pin.py - 窗口置顶工具
import win32gui
import win32con
import win32api
import threading
import atexit
import time
from typing import Dict, List, Tuple, Callable

class WindowPinner:
    def __init__(self):
        self.topped: Dict[int, bool] = {}  # {hwnd: 是否已置顶}
        self.menu_callbacks: Dict[int, Dict[str, Callable]] = {}  # 缓存菜单回调函数
        self.last_window_list: List[int] = []  # 缓存上一次的窗口列表
        self.refresh_interval = 5  # 秒
        self.stop_event = threading.Event()
        self.refresh_thread = None
        self.callback = None

        # 注册退出时的清理函数
        atexit.register(self.cleanup_topped_windows)

    def cleanup_topped_windows(self):
        """程序退出时清理所有置顶窗口"""
        print("正在清理置顶窗口...")
        self.stop_auto_refresh()
        for hwnd in list(self.topped.keys()):
            if self.topped.get(hwnd, False) and win32gui.IsWindow(hwnd):
                try:
                    win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST,
                                        0, 0, 0, 0,
                                        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
                    print(f"已取消置顶窗口: {hwnd}")
                except Exception as e:
                    print(f"取消置顶窗口 {hwnd} 时出错: {e}")
        self.topped.clear()
        print("清理完成")

    def iter_visible_windows(self) -> List[Tuple[int, str]]:
        """返回 [(hwnd, title), ...] 只含实际可见窗口"""
        result = []
        def enum_cb(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return

            # 获取窗口标题
            title = win32gui.GetWindowText(hwnd).strip()
            if not title:
                return

            # 检查窗口样式
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            if not (style & win32con.WS_VISIBLE):
                return

            # 检查窗口是否最小化
            if win32gui.IsIconic(hwnd):
                return

            # 检查窗口矩形是否有效
            try:
                rect = win32gui.GetWindowRect(hwnd)
                if rect[0] >= rect[2] or rect[1] >= rect[3]:  # 无效矩形
                    return
                if rect[2] <= 0 or rect[3] <= 0:  # 完全在屏幕外
                    return
            except:
                return

            # 获取窗口类名，过滤系统窗口
            try:
                class_name = win32gui.GetClassName(hwnd)
                # 允许浏览器窗口类名，包括现代浏览器使用的类名
                allowed_browser_classes = [
                    'Chrome_WidgetWin_1',  # Chrome, Edge经典版等
                    'MozillaWindowClass',  # Firefox
                    'ApplicationFrameWindow'  # UWP应用，包括新版Edge等
                ]
                
                # 如果是允许的浏览器类名，则跳过后续的过滤
                if class_name in allowed_browser_classes:
                    result.append((int(hwnd), title))
                    return
                
                # 过滤其他系统窗口
                if class_name in [
                    'Shell_TrayWnd', 'Progman', 'WorkerW', 'Windows.UI.Core.CoreWindow',
                    'Windows.UI.Input.InputSite.WindowClass',
                    'TaskListThumbnailWnd', 'MSTaskListWClass', 'TrayNotifyWnd',
                    'SysPager', 'ToolbarWindow32', 'ReBarWindow32'
                ]:
                    return
            except:
                return

            # 过滤系统窗口标题
            if any(sys_name in title.lower() for sys_name in [
                'windows input experience', 'text input', 'program manager',
                'system tray', 'notification area', 'start menu', 'taskbar',
                'settings', 'action center', 'search', 'cortana', 'explorer'
            ]):
                return
            result.append((int(hwnd), title))

        win32gui.EnumWindows(enum_cb, None)
        return result

    def get_window_list(self) -> List[Tuple[int, str]]:
        """获取当前可见窗口列表"""
        return self.iter_visible_windows()

    def toggle_pin(self, hwnd: int) -> bool:
        """置顶/取消置顶窗口，返回新的状态"""
        if not isinstance(hwnd, int):
            return False

        if not win32gui.IsWindow(hwnd):
            if hwnd in self.topped:
                del self.topped[hwnd]
            if hwnd in self.menu_callbacks:
                del self.menu_callbacks[hwnd]
            return False

        old_state = self.topped.get(hwnd, False)
        try:
            if old_state:
                # 取消置顶
                win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST,
                                    0, 0, 0, 0,
                                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
                self.topped[hwnd] = False
            else:
                # 置顶
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST,
                                    0, 0, 0, 0,
                                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
                self.topped[hwnd] = True
        except Exception as e:
            print(f"设置窗口置顶状态时出错: {e}")
            return old_state

        return self.topped.get(hwnd, False)

    def is_pinned(self, hwnd: int) -> bool:
        """检查窗口是否已置顶"""
        return self.topped.get(hwnd, False)

    def cleanup_invalid_windows(self):
        """清理不存在的窗口记录"""
        current_windows = set(hwnd for hwnd, _ in self.iter_visible_windows())
        # 清理不存在的窗口的回调函数缓存
        for hwnd in list(self.menu_callbacks.keys()):
            if hwnd not in current_windows:
                del self.menu_callbacks[hwnd]
        # 清理不存在的窗口的置顶状态
        for hwnd in list(self.topped.keys()):
            if hwnd not in current_windows:
                del self.topped[hwnd]
        self.last_window_list = list(current_windows)

    def refresh_loop(self):
        while not self.stop_event.is_set():
            time.sleep(self.refresh_interval)
            if self.callback:
                self.cleanup_invalid_windows()
                self.callback()

    def start_auto_refresh(self, callback: Callable[[], None]):
        """启动自动刷新定时器"""
        self.callback = callback
        self.refresh_thread = threading.Thread(target=self.refresh_loop, daemon=True)
        self.refresh_thread.start()

    def stop_auto_refresh(self):
        """停止自动刷新"""
        self.stop_event.set()
        if self.refresh_thread:
            self.refresh_thread.join(timeout=1)