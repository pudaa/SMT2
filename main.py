import sys
import os
import psutil
import ctypes
from PySide6.QtWidgets import QApplication, QSystemTrayIcon
from PySide6.QtCore import Qt, QTimer
from src.views.main_views.main_widget import MainWidget
from src.tray.system_tray import SystemTrayIcon
from src.utils.auto_start_manager import AutoStartManager
from src.utils.app_paths import AppPaths
from src.configs.base_config import get_default_theme
from src.themes import theme_manager

def main():
    # 当通过注册表 Run 键自启时，工作目录不是 exe 所在目录，
    # 导致所有相对路径（resources/*）解析失败，配置、主题、图标等全部回退到默认值
    exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    os.chdir(exe_dir)
    
    # 启动时确保用户配置文件与待办事项文件存在
    AppPaths.ensure_user_config_exists("default_properties.json")
    AppPaths.ensure_todos_exists()
    
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    # 应用默认主题（在创建窗口之前）
    default_theme = get_default_theme()
    theme_manager.set_theme(default_theme)
    print(f"默认主题: {default_theme}")
    
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
    
    # 延迟启动测试通知弹窗（验证通知系统是否正常）
    def _startup_test_notification():
        from src.views.components.notification_popup import notify
        notify(
            "SMT2 已启动",
            "通知系统运行正常，待办提醒功能已就绪",
            duration=6000,
        )
    QTimer.singleShot(2000, _startup_test_notification)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()