"""主题系统 - 主题管理器与注册机制

用法:
    from src.themes import theme_manager
    theme_manager.set_theme("modern")
    color = theme_manager.get_color("performance_panel_background")
"""
from __future__ import annotations
from typing import Optional, Callable
import json
import os
from src.themes.base_theme import (
    ThemeDefinition, PanelMetrics, PanelCompactMetrics, PanelMiniMetrics,
    StickerData, CustomTheme
)
from src.themes.classical_theme import ClassicalTheme
from src.themes.modern_theme import ModernTheme
from src.utils.app_paths import AppPaths


# ============================================================
# 主题注册表
# ============================================================
_BUILTIN_THEMES: dict[str, type[ThemeDefinition]] = {
    "classical": ClassicalTheme,
    "modern": ModernTheme,
}


class ThemeManager:
    """主题管理器（单例）
    
    职责:
      1. 管理当前激活的主题实例
      2. 提供统一的 get_color / get_stylesheet / get_metrics 入口
      3. 支持动态切换主题并通知监听器
      4. 支持用户自定义主题（持久化到 JSON）
    """

    def __init__(self):
        self._current_theme_name: str = "classical"
        self._current_theme: ThemeDefinition = ClassicalTheme()
        self._listeners: list[Callable] = []  # 主题切换回调
        self._custom_themes: dict[str, CustomTheme] = {}
        self._load_custom_themes()

    # ---- 属性 ----

    @property
    def current_theme(self) -> ThemeDefinition:
        return self._current_theme

    @property
    def current_theme_name(self) -> str:
        return self._current_theme_name

    @property
    def available_themes(self) -> list[dict]:
        """返回可用主题列表，供 UI 下拉框/菜单使用"""
        themes = []
        # 内置主题
        for name, cls in _BUILTIN_THEMES.items():
            themes.append({"name": name, "display": cls.display_name, "is_custom": False})
        # 自定义主题
        for name, ct in self._custom_themes.items():
            themes.append({"name": name, "display": ct.display_name, "is_custom": True})
        return themes

    # ---- 切换主题 ----

    def set_theme(self, name: str) -> bool:
        """切换到指定主题，返回是否成功"""
        if name == self._current_theme_name:
            return True

        # 1. 尝试内置主题
        cls = _BUILTIN_THEMES.get(name)
        if cls:
            self._current_theme_name = name
            self._current_theme = cls()
            self._notify_listeners()
            return True

        # 2. 尝试自定义主题
        ct = self._custom_themes.get(name)
        if ct:
            self._current_theme_name = name
            self._current_theme = ct
            self._notify_listeners()
            return True

        return False

    # ---- 自定义主题管理 ----

    def add_custom_theme(self, theme: CustomTheme) -> bool:
        """添加或更新一个自定义主题"""
        self._custom_themes[theme.name] = theme
        self._save_custom_themes()
        return True

    def remove_custom_theme(self, name: str) -> bool:
        """删除自定义主题"""
        if name not in self._custom_themes:
            return False
        del self._custom_themes[name]
        self._save_custom_themes()
        # 如果当前用的就是这个被删除的主题，切回 classical
        if self._current_theme_name == name:
            self.set_theme("classical")
        return True

    def get_custom_theme(self, name: str) -> CustomTheme | None:
        return self._custom_themes.get(name)

    def get_all_custom_themes(self) -> dict[str, CustomTheme]:
        return dict(self._custom_themes)

    # ---- 颜色查询（向后兼容 get_color） ----

    def get_color(self, token: str, default: Optional[list[int]] = None) -> list[int]:
        """获取当前主题的颜色令牌值"""
        try:
            return self._current_theme.get_color(token)
        except (KeyError, AttributeError):
            return default or [200, 200, 200]

    def get_all_colors(self) -> dict[str, list[int]]:
        """获取当前主题的所有已知颜色令牌（用于设置界面预览）"""
        known_tokens = [
            "performance_panel_background", "performance_panel_shadow",
            "performance_panel_time", "performance_panel_progress_ring_background",
            "performance_panel_progress_ring_foreground", "performance_panel_progress_title",
            "performance_panel_progress_text",
        ]
        return {t: self.get_color(t) for t in known_tokens}

    def get_qss_color(self, token: str, default: Optional[list[int]] = None) -> str:
        """将颜色令牌转换为 QSS rgb/rgba 字符串"""
        color = self.get_color(token, default)
        if len(color) == 3:
            return f"rgb({color[0]}, {color[1]}, {color[2]})"
        elif len(color) >= 4:
            return f"rgba({color[0]}, {color[1]}, {color[2]}, {color[3]})"
        return f"rgb({color[0]}, {color[1]}, {color[2]})"

    # ---- 面板尺寸 ----

    def get_panel_metrics(self, mode: str = "normal") -> PanelMetrics | PanelCompactMetrics | PanelMiniMetrics:
        """获取当前主题在指定模式下的面板尺寸"""
        m = self._current_theme
        if mode == "compact":
            return m.metrics_compact
        elif mode == "mini":
            return m.metrics_mini
        return m.metrics_normal

    # ---- 字体 ----

    @property
    def font_family(self) -> str:
        return self._current_theme.font_family

    # ---- 样式表 ----

    def get_stylesheet(self) -> str:
        return self._current_theme.get_stylesheet()

    # ---- 监听器机制 ----

    def add_listener(self, callback: Callable):
        """注册主题切换回调，参数: (theme_name: str)"""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self):
        for cb in self._listeners:
            try:
                cb(self._current_theme_name)
            except Exception as e:
                print(f"[ThemeManager] 通知监听器出错: {e}")

    # ---- 持久化 ----

    def _load_custom_themes(self):
        """从 JSON 文件加载自定义主题"""
        themes_file = AppPaths.get_custom_themes_file()
        if not os.path.exists(themes_file):
            return
        try:
            with open(themes_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for item in data:
                ct = CustomTheme.from_dict(item)
                self._custom_themes[ct.name] = ct
        except Exception as e:
            print(f"[ThemeManager] 加载自定义主题出错: {e}")

    def _save_custom_themes(self):
        """保存自定义主题到 JSON 文件"""
        try:
            data = [ct.to_dict() for ct in self._custom_themes.values()]
            themes_file = AppPaths.get_custom_themes_file()
            with open(themes_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ThemeManager] 保存自定义主题出错: {e}")


# ============================================================
# 全局单例 —— 整个应用共享同一个主题管理器
# ============================================================
theme_manager = ThemeManager()


# ============================================================
# 便利函数（向后兼容，供旧代码逐步迁移）
# ============================================================
def get_color(token: str, default: Optional[list[int]] = None) -> list[int]:
    return theme_manager.get_color(token, default)


def get_qss_color(token: str, default: Optional[list[int]] = None) -> str:
    return theme_manager.get_qss_color(token, default)
