"""默认配置加载器 —— 单一数据源为 resources/default_properties.json

不再在此文件中硬编码默认值，所有默认配置均从 JSON 文件加载。
default_properties.json 随应用分发（只读），用户自定义配置保存在 AppData 中。
"""
import json
from src.utils.app_paths import AppPaths


def load_default_properties() -> dict:
    """从内置只读资源加载默认配置（单一数据源）"""
    default_file = AppPaths.get_resource("default_properties.json")
    try:
        with open(default_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[defaul_config] 加载默认配置失败: {e}")
        return {
            "todo_file_name": AppPaths.get_todos_file(),
            "extractor_model": "jieba",
            "todo_poses": ["n", "eng"],
            "font": "Microsoft YaHei UI",
            "default_theme": "classical",
        }


class defaul_config:
    """向后兼容的类接口 —— 委托给 JSON 文件"""
    def __init__(self):
        self.default_properties = load_default_properties()

    def get_default_properties(self) -> dict:
        return self.default_properties
