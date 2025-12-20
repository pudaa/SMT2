import sys
import os
import psutil
import ctypes
from PySide6.QtWidgets import QApplication, QSystemTrayIcon
from PySide6.QtCore import Qt, QTimer
from src.components.main_widget import MainWidget
from src.components.system_tray import SystemTrayIcon

def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app = QApplication(sys.argv)
    # 创建主窗口
    widget = MainWidget()
    widget.show()
    
    # Windows 专用：在 show 之后短延迟调用 Win32 强制置顶/置前（多次重试以应对打包后限制）
    if sys.platform == "win32":
        def _force_foreground():
            try:
                hwnd = int(widget.winId())
                SWP_NOSIZE = 0x0001
                SWP_NOMOVE = 0x0002
                SWP_SHOWWINDOW = 0x0040
                HWND_TOPMOST = -1
                ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                                  SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception as e:
                print("无法强制置顶窗口:", e)
        
        # 多次重试（总共5次，每次间隔200ms，从100ms开始）
        for i in range(5):
            QTimer.singleShot(100 + i * 200, _force_foreground)
    
    # 创建系统托盘图标
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray_icon = SystemTrayIcon(widget)
        tray_icon.show()
    else:
        print("系统托盘不可用")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()