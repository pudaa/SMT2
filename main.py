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
    widget = MainWidget()
    widget.show()
    
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray_icon = SystemTrayIcon(widget)
        tray_icon.show()
    else:
        print("系统托盘不可用")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()