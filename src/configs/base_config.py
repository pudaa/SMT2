import json
import os

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

def get_todo_file_name() -> str:
    _load_properties()
    return _properties.get("todo_file_name", "resources/todos.json")

def get_todo_poses() -> list[str]:
    _load_properties()
    return _properties.get("todo_poses", ['NOUN', 'VERB', 'ADJ', 'PROPN'])

def get_extractor_model() -> str:
    _load_properties()
    return _properties.get("extractor_model", 'jieba')