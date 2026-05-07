import json
import os
from src.configs.defaul_config import *
from src.themes import theme_manager

# 全局配置变量
_properties = {}
_properties_file = "resources/properties.json"
_properties_loaded = False

def _load_properties():
    global _properties, _properties_loaded
    if not _properties_loaded:
        try:
            with open(_properties_file, 'r', encoding='utf-8') as f:
                _properties = json.load(f)
            _properties_loaded = True
        except FileNotFoundError:
            _properties = {}
            _properties_loaded = True
            

def reload_properties():
    global _properties, _properties_loaded
    _properties_loaded = False
    _properties = {}
    _load_properties()

# 获取todo文件路径
def get_todo_file_name() -> str:
    _load_properties()
    return _properties.get("todo_file_name", "resources/todos.json")

# 获取标签筛选列表
def get_todo_poses() -> list[str]:
    _load_properties()
    return _properties.get("todo_poses", ('n', 'eng'))

# 获取文本抽取模型
def get_extractor_model() -> str:
    _load_properties()
    return _properties.get("extractor_model", 'jieba')


# 获取字体配置
def get_font() -> str:
    _load_properties()
    return _properties.get("font", "Microsoft YaHei UI")


# 获取默认主题
def get_default_theme() -> str:
    _load_properties()
    return _properties.get("default_theme", "classical")


# 保存默认主题
def set_default_theme(theme_name: str):
    _load_properties()
    _properties["default_theme"] = theme_name
    with open(_properties_file, 'w', encoding='utf-8') as f:
        json.dump(_properties, f, ensure_ascii=False, indent=4)


# 获取颜色配置
# 优先使用主题系统的颜色，若主题中没有则回退到 properties.json
def get_color(key: str, default: str|list[int]) -> str|list[int]:
    # 1. 尝试从主题管理器获取
    try:
        theme_color = theme_manager.get_color(key)
        if theme_color:
            return theme_color
    except Exception:
        pass
    # 2. 回退到 properties.json
    _load_properties()
    colors = _properties.get("colors", {})
    return colors.get(key, default)

# 将颜色配置转换为QSS格式的rgb或rgba字符串
def get_qss_color(key: str, default: str|list[int]) -> str:
    color_value = get_color(key, default)
    
    if isinstance(color_value, str):
        return color_value
    elif isinstance(color_value, list):
        if len(color_value) == 3:
            r, g, b = color_value
            return f"rgb({r}, {g}, {b})"
        elif len(color_value) == 4:
            r, g, b, a = color_value
            return f"rgba({r}, {g}, {b}, {a})"
        else:
            return str(default)
    else:
        # 返回默认值
        if isinstance(default, list):
            if len(default) == 3:
                r, g, b = default
                return f"rgb({r}, {g}, {b})"
            elif len(default) == 4:
                r, g, b, a = default
                return f"rgba({r}, {g}, {b}, {a})"
        return str(default)