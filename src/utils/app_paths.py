"""统一路径管理器 —— 兼容开发环境与 Nuitka 打包后的运行环境

问题背景：
  - Nuitka --onefile 打包后，exe 运行时会解压文件到临时目录 sys._MEIPASS
  - 该临时目录只读，且每次启动路径可能变化
  - 所有需要持久化的用户数据必须写入 %APPDATA%/SMT2/ 等可写目录

目录结构（开发与打包一致）:
    %APPDATA%/SMT2/                          ← 用户可写
      ├── properties.json                    ← 用户配置（首次自动生成）
      ├── custom_themes.json                 ← 自定义主题
      ├── todos.json                         ← 待办事项
      └── stickers/                          ← 贴纸图片 (Phase 2)
    {资源目录}/resources/                    ← 只读
      ├── default_properties.json
      ├── themes/
      └── tray.png

用法:
    from src.utils.app_paths import AppPaths
    user_config = AppPaths.get_properties_file()  # 可写
    default_config = AppPaths.get_resource("default_properties.json")  # 只读
"""
from __future__ import annotations
import os
import sys


class AppPaths:
    """单例式静态工具类，统一解析所有文件路径"""

    # ---- 检测当前运行模式 ----

    @staticmethod
    def _is_packaged() -> bool:
        """是否为打包后的运行环境（兼容 Nuitka / PyInstaller）"""
        # Nuitka 同时设置 frozen 和 __compiled__
        # PyInstaller 设置 frozen 和 _MEIPASS
        return (
            getattr(sys, 'frozen', False)
            or hasattr(sys, '_MEIPASS')
        )

    # ---- 用户可写目录（持久化数据） ----

    @staticmethod
    def get_user_data_dir() -> str:
        """用户数据根目录，保证存在且可写

        统一使用 %APPDATA%/SMT2/（开发与打包环境行为一致）
        """
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        path = os.path.join(base, "SMT2")
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def get_properties_file() -> str:
        """用户配置文件路径（可写）"""
        return os.path.join(AppPaths.get_user_data_dir(), "properties.json")

    @staticmethod
    def get_custom_themes_file() -> str:
        """自定义主题持久化文件路径（可写）"""
        return os.path.join(AppPaths.get_user_data_dir(), "custom_themes.json")

    @staticmethod
    def get_todos_file() -> str:
        """待办事项持久化文件路径（可写）"""
        return os.path.join(AppPaths.get_user_data_dir(), "todos.json")

    @staticmethod
    def get_stickers_dir() -> str:
        """贴纸图片目录（可写）"""
        path = os.path.join(AppPaths.get_user_data_dir(), "stickers")
        os.makedirs(path, exist_ok=True)
        return path

    # ---- 只读资源目录 ----

    @staticmethod
    def get_resource_dir() -> str:
        """内置资源目录（只读）

        开发环境: {项目根}/resources/
        打包环境: {临时解压目录}/resources/
        """
        if AppPaths._is_packaged():
            return os.path.join(sys._MEIPASS, "resources")  # type: ignore[attr-defined]
        return os.path.join(os.getcwd(), "resources")

    @staticmethod
    def get_resource(filename: str) -> str:
        """获取只读资源文件的完整路径

        示例:
            AppPaths.get_resource("default_properties.json")
            AppPaths.get_resource("themes/light_theme.qss")
            AppPaths.get_resource("tray.png")
        """
        return os.path.join(AppPaths.get_resource_dir(), filename)

    # ---- 初始化辅助 ----

    @staticmethod
    def ensure_user_config_exists(resource_filename: str = "default_properties.json") -> str:
        """首次运行时，将默认配置从只读资源目录拷贝到用户可写目录

        只在用户配置不存在时才拷贝，不会覆盖已有的用户配置。

        返回用户配置文件的绝对路径。
        """
        user_file = AppPaths.get_properties_file()
        if not os.path.exists(user_file):
            default_file = AppPaths.get_resource(resource_filename)
            try:
                import shutil
                shutil.copy2(default_file, user_file)
                print(f"[AppPaths] 已从 {default_file} 生成用户配置 {user_file}")
            except Exception as e:
                print(f"[AppPaths] 生成用户配置失败: {e}")
        return user_file

    @staticmethod
    def ensure_todos_exists() -> str:
        """确保待办事项文件存在（如不存在则创建空数组）"""
        todos_file = AppPaths.get_todos_file()
        if not os.path.exists(todos_file):
            try:
                import json
                with open(todos_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
                print(f"[AppPaths] 已创建空待办事项文件 {todos_file}")
            except Exception as e:
                print(f"[AppPaths] 创建待办事项文件失败: {e}")
        return todos_file

    @staticmethod
    def import_sticker(source_path: str) -> str:
        """将外部 PNG 图片复制到贴纸目录，返回目标路径

        参数:
            source_path: 用户选择的 PNG 文件路径
        返回:
            贴纸在 stickers/ 目录下的绝对路径，失败返回空字符串
        """
        import shutil
        import uuid
        if not source_path.lower().endswith('.png'):
            return ""
        try:
            sticker_dir = AppPaths.get_stickers_dir()
            dest_name = f"{uuid.uuid4().hex[:12]}.png"
            dest_path = os.path.join(sticker_dir, dest_name)
            shutil.copy2(source_path, dest_path)
            print(f"[AppPaths] 贴纸已导入: {dest_path}")
            return dest_path
        except Exception as e:
            print(f"[AppPaths] 导入贴纸失败: {e}")
            return ""
