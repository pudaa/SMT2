"""配置管理 —— 用户配置自动从默认配置生成，持久化到 AppData

职责:
  1. 首次运行时自动从 default_properties.json 生成用户配置到 AppData
  2. 提供类型安全的 getter/setter
  3. 颜色查询优先走主题系统，回退到用户配置中的 colors 字段

路径解析:
  开发环境:  用户配置在项目根目录 (保持兼容)
  打包环境:  用户配置在 %APPDATA%/SMT2/
  默认配置:  始终在 resources/default_properties.json (只读)
"""
from __future__ import annotations
import json
from src.utils.app_paths import AppPaths
from src.themes import theme_manager


# ---- 模块级缓存 ----
_properties: dict = {}
_properties_file: str = ""
_properties_loaded: bool = False


def _init_paths():
    """懒加载路径"""
    global _properties_file
    if not _properties_file:
        _properties_file = AppPaths.get_properties_file()


def _load_properties():
    """加载用户配置；首次运行自动从默认配置生成"""
    global _properties, _properties_loaded
    _init_paths()
    if _properties_loaded:
        return
    AppPaths.ensure_user_config_exists("default_properties.json")
    try:
        with open(_properties_file, 'r', encoding='utf-8') as f:
            _properties = json.load(f)
    except Exception as e:
        print(f"[base_config] 加载配置失败: {e}")
        _properties = {}
    _properties_loaded = True


def reload_properties():
    global _properties, _properties_loaded
    _properties_loaded = False
    _properties = {}
    _load_properties()


def save_properties():
    _init_paths()
    try:
        with open(_properties_file, 'w', encoding='utf-8') as f:
            json.dump(_properties, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[base_config] 保存配置失败: {e}")


# ================================================================
# 配置 getter
# ================================================================

def get_todo_file_name() -> str:
    """获取待办事项文件路径（始终指向 AppData 下的 todos.json）"""
    _load_properties()
    name = _properties.get("todo_file_name", "todos.json")
    if name and not any(sep in name for sep in ("/", "\\", ":")):
        return AppPaths.get_todos_file()
    if name != AppPaths.get_todos_file():
        print(f"[base_config] 旧版 todo_file_name='{name}'，已迁移")
        _properties["todo_file_name"] = "todos.json"
        save_properties()
        return AppPaths.get_todos_file()
    return name


def get_todo_poses() -> list[str]:
    _load_properties()
    return _properties.get("todo_poses", ["n", "eng"])


def get_extractor_model() -> str:
    _load_properties()
    return _properties.get("extractor_model", "jieba")


def get_font() -> str:
    _load_properties()
    return _properties.get("font", "Microsoft YaHei UI")


def get_default_theme() -> str:
    _load_properties()
    return _properties.get("default_theme", "classical")


def set_default_theme(theme_name: str):
    _load_properties()
    _properties["default_theme"] = theme_name
    save_properties()


# ================================================================
# 颜色查询（优先主题 → 回退用户配置）
# ================================================================

def get_color(key: str, default=None) -> list[int] | str:
    if default is None:
        default = [200, 200, 200]
    try:
        theme_color = theme_manager.get_color(key)
        if theme_color:
            return theme_color
    except Exception:
        pass
    _load_properties()
    colors = _properties.get("colors", {})
    return colors.get(key, default)


def get_qss_color(key: str, default=None) -> str:
    if default is None:
        default = [200, 200, 200]
    color_value = get_color(key, default)
    if isinstance(color_value, str):
        return color_value
    if isinstance(color_value, list):
        if len(color_value) == 3:
            return f"rgb({color_value[0]}, {color_value[1]}, {color_value[2]})"
        elif len(color_value) >= 4:
            return f"rgba({color_value[0]}, {color_value[1]}, {color_value[2]}, {color_value[3]})"
    if isinstance(default, list):
        if len(default) == 3:
            return f"rgb({default[0]}, {default[1]}, {default[2]})"
        elif len(default) >= 4:
            return f"rgba({default[0]}, {default[1]}, {default[2]}, {default[3]})"
    return str(default)


# ================================================================
# 暴露给 setting_view 使用的接口
# ================================================================

def get_config_path() -> str:
    _init_paths()
    return _properties_file


def get_properties() -> dict:
    _load_properties()
    return _properties