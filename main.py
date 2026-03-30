import sys
import os
import psutil
import ctypes
from PySide6.QtWidgets import QApplication, QSystemTrayIcon
from PySide6.QtCore import Qt, QTimer
from src.views.main_views.main_widget import MainWidget
from src.tray.system_tray import SystemTrayIcon
from src.utils.auto_start_manager import AutoStartManager

def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app = QApplication(sys.argv)
    widget = MainWidget()
    
    auto_start_manager = AutoStartManager()
    is_auto_start = auto_start_manager.is_auto_start_enabled()
    print(f"开机自启状态：{'已启用' if is_auto_start else '未启用'}")
    
    widget.show()
    
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray_icon = SystemTrayIcon(widget)
        tray_icon.show()
    else:
        print("系统托盘不可用")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()