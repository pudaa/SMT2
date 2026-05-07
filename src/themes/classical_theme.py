"""经典主题 - 与当前深色风格一致"""
from __future__ import annotations
from src.themes.base_theme import ThemeDefinition, PanelMetrics


class ClassicalTheme(ThemeDefinition):
    """经典深色风格"""

    name = "classical"
    display_name = "Classical 经典"

    # ========== 颜色令牌 ==========
    _COLORS: dict[str, list[int]] = {
        # ---- PerformancePanel ----
        "performance_panel_background":              [50, 50, 50, 200],
        "performance_panel_shadow":                  [0, 0, 0, 80],
        "performance_panel_time":                    [255, 255, 255],
        "performance_panel_progress_ring_background": [70, 70, 70, 150],
        "performance_panel_progress_ring_foreground": [200, 200, 200],
        "performance_panel_progress_title":           [200, 200, 200],
        "performance_panel_progress_text":            [200, 200, 200],
        # ---- TodoPanel ----
        "todo_panel_todoitem_background":                     [50, 50, 50, 100],
        "todo_panel_todoitem_foreground":                     [204, 204, 204],
        "todo_panel_todoitem_checkbox_unchecked_border":      [136, 136, 136],
        "todo_panel_todoitem_checkbox_checked_border":        [85, 85, 85],
        "todo_panel_todoitem_checkbox_checked_background":    [74, 144, 226],
        "todo_panel_todoitem_lineedit_foreground":            [204, 204, 204],
        "todo_panel_todoitem_lineedit_focus":                 [74, 144, 226],
        "todo_panel_todoitem_lineedit_finished":              [136, 136, 136],
        "todo_panel_todoitem_draglabel":                      [136, 136, 136],
        "todo_panel_titlelabel_foreground":                   [204, 204, 204],
        "todo_panel_titlelabel_background":                   [50, 50, 50, 200],
        "todo_panel_tagscrollarea_background":                 [50, 50, 50, 200],
        "todo_panel_tagbutton_background":                     [102, 102, 102],
        "todo_panel_tagbutton_foreground":                     [204, 204, 204],
        "todo_panel_tagbutton_checked_background":             [74, 144, 226],
        "todo_panel_tagbutton_checked_foreground":             [255, 255, 255],
        "todo_panel_tagbutton_check_hover_background":         [119, 119, 119],
        "todo_panel_tagbutton_checked_hover_background":       [90, 160, 240],
        "todo_panel_scrollarea_background":                    [50, 50, 50, 200],
        "todo_panel_scrollbar_background":                     [85, 85, 85],
    }

    def get_color(self, token: str) -> list[int]:
        return list(self._COLORS.get(token, [200, 200, 200]))

    # ========== QSS ==========
    def get_stylesheet(self) -> str:
        return ""  # 经典主题使用内置 get_qss_color 即可

    # ========== 紧凑面板参数 ==========
    @property
    def metrics_normal(self) -> PanelMetrics:
        return PanelMetrics(
            panel_width=250,
            panel_height=90,
            ring_diameter=50,
            ring_spacing=60,
            ring_start_x=10,
            ring_y=20,
            ring_width=2,
            time_y=15,
            font_size_time=9,
            font_size_ring_title=8,
            font_size_ring_value=8,
        )

    @property
    def font_family(self) -> str:
        return "Microsoft YaHei UI"
