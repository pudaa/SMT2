"""主题编辑器主视图 — 三栏布局：组件面板 | 画布预览 | 属性面板"""
from __future__ import annotations
import json
import os
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter, QPushButton,
    QLabel, QFileDialog, QMessageBox, QFrame, QComboBox, QSpinBox
)
from PySide6.QtCore import Qt, Signal, QTimer
from src.themes import theme_manager
from src.themes.base_theme import CustomTheme, StickerData, PanelMetrics, PanelCompactMetrics, PanelMiniMetrics
from src.utils.app_paths import AppPaths
from .component_palette import ComponentPalette
from .canvas_widget import ThemeCanvas
from .property_panel import PropertyPanel
from src.utils.icon_utils import load_svg_icon


class ThemeEditorView(QWidget):
    """主题可视化编辑器

    三栏布局:
      [组件面板]  [画布预览]  [属性面板]
      200px       400px       300px
    """

    theme_saved = Signal(str)  # 主题保存成功后发出 (theme_name)

    def __init__(self):
        super().__init__()
        self.setObjectName("themeEditorView")

        # ---- 状态 ----
        self._editing_theme: CustomTheme | None = None
        self._editing_theme_name: str = ""
        self._is_new_theme: bool = False
        self._is_template: bool = False  # 内置主题作为模板（只读）
        self._dirty: bool = False
        self._preview_mode: str = "normal"

        # ---- 主布局 ----
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 顶部工具栏
        self._create_toolbar(main_layout)

        # 三栏分割器
        splitter = QSplitter(Qt.Horizontal)

        # 左：组件面板
        self.component_palette = ComponentPalette()
        self.component_palette.item_requested.connect(self._on_component_requested)
        splitter.addWidget(self.component_palette)

        # 中：画布
        self.canvas = ThemeCanvas()
        self.canvas.component_selected.connect(self._on_canvas_selection)
        self.canvas.component_moved.connect(self._on_canvas_component_moved)
        self.canvas.component_added.connect(self._on_canvas_component_added)
        self.canvas.component_deleted.connect(self._on_canvas_component_deleted)
        splitter.addWidget(self.canvas)

        # 右：属性面板
        self.property_panel = PropertyPanel()
        self.property_panel.property_changed.connect(self._on_property_changed)
        self.property_panel.component_deleted.connect(self._on_property_delete)
        splitter.addWidget(self.property_panel)

        splitter.setSizes([200, 460, 300])
        main_layout.addWidget(splitter)

        # 底栏
        self._create_status_bar(main_layout)

        # 自动刷新定时器（预览实时时间）
        self._preview_timer = QTimer(self)
        self._preview_timer.timeout.connect(self.canvas.update)
        self._preview_timer.start(1000)

        # 默认加载当前使用中的主题
        self._load_theme_for_editing(theme_manager.current_theme_name)

    # ================================================================
    # 工具栏
    # ================================================================

    def _create_toolbar(self, parent_layout):
        bar = QFrame()
        bar.setObjectName("editorToolbar")
        bar.setMaximumHeight(44)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 4, 8, 4)

        # 主题选择
        layout.addWidget(QLabel("编辑:"))
        self.theme_combo = QComboBox()
        self.theme_combo.setMaximumWidth(160)
        self._refresh_theme_combo()
        self.theme_combo.currentIndexChanged.connect(self._on_theme_combo_changed)
        layout.addWidget(self.theme_combo)

        # 新建
        new_btn = QPushButton("+ 新建")
        new_btn.setMaximumWidth(60)
        new_btn.clicked.connect(self._new_theme_dialog)
        layout.addWidget(new_btn)

        # 模式 + 尺寸
        layout.addWidget(QLabel(" 模式:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["普通", "紧凑", "极简"])
        self.mode_combo.currentIndexChanged.connect(self._on_preview_mode_changed)
        layout.addWidget(self.mode_combo)

        layout.addWidget(QLabel(" W:"))
        self.panel_w_spin = QSpinBox()
        self.panel_w_spin.setRange(40, 600)
        self.panel_w_spin.setValue(180)
        self.panel_w_spin.setMaximumWidth(60)
        self.panel_w_spin.valueChanged.connect(self._on_panel_size_changed)
        layout.addWidget(self.panel_w_spin)

        layout.addWidget(QLabel(" H:"))
        self.panel_h_spin = QSpinBox()
        self.panel_h_spin.setRange(20, 400)
        self.panel_h_spin.setValue(80)
        self.panel_h_spin.setMaximumWidth(60)
        self.panel_h_spin.valueChanged.connect(self._on_panel_size_changed)
        layout.addWidget(self.panel_h_spin)

        layout.addStretch()

        save_btn = QPushButton("  保存")
        save_btn.setMaximumWidth(80)
        save_icon = load_svg_icon("save.svg", 14)
        if not save_icon.isNull():
            save_btn.setIcon(save_icon)
        save_btn.clicked.connect(self._save_theme)
        layout.addWidget(save_btn)

        save_as_btn = QPushButton("  另存为")
        save_as_btn.setMaximumWidth(80)
        folder_icon = load_svg_icon("folder.svg", 14)
        if not folder_icon.isNull():
            save_as_btn.setIcon(folder_icon)
        save_as_btn.clicked.connect(self._save_theme_as)
        layout.addWidget(save_as_btn)

        parent_layout.addWidget(bar)

    def _create_status_bar(self, parent_layout):
        bar = QFrame()
        bar.setObjectName("editorStatusBar")
        bar.setMaximumHeight(24)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 2, 8, 2)

        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)
        layout.addStretch()

        self.coord_label = QLabel("")
        self.coord_label.setObjectName("coordLabel")
        layout.addWidget(self.coord_label)

        parent_layout.addWidget(bar)

    # ================================================================
    # 主题加载 / 切换
    # ================================================================

    def _refresh_theme_combo(self):
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()
        for t in theme_manager.available_themes:
            tag = "[自定义]" if t["is_custom"] else "[内置]"
            self.theme_combo.addItem(f"{tag} {t['display']}", t["name"])
        self.theme_combo.blockSignals(False)

    def _on_theme_combo_changed(self, idx):
        if idx < 0:
            return
        name = self.theme_combo.currentData()
        self._load_theme_for_editing(name)

    def _load_theme_for_editing(self, theme_name: str):
        """加载主题到编辑器"""
        if self._dirty:
            reply = QMessageBox.question(
                self, "未保存", "当前主题有未保存的修改，是否放弃？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        ct = theme_manager.get_custom_theme(theme_name)
        if ct:
            self._editing_theme = ct
            self._is_new_theme = False
            self._is_template = False
            # 确保旧自定义主题有 panel_sizes
            if not hasattr(ct, '_panel_sizes') or not ct._panel_sizes:
                ct._panel_sizes = {}
        else:
            # 内置主题 → 作为模板加载（只读预览，必须另存为才能保存）
            theme_manager.set_theme(theme_name)
            builtin = theme_manager.current_theme
            colors = {}
            if hasattr(builtin, '_COLORS'):
                colors = builtin._COLORS.copy()
            # 获取内置主题的默认面板尺寸
            panel_sizes = {}
            for mode_key, metrics_getter in [
                ("normal", builtin.metrics_normal),
                ("compact", builtin.metrics_compact if hasattr(builtin, 'metrics_compact') else builtin.metrics_normal),
                ("mini", builtin.metrics_mini if hasattr(builtin, 'metrics_mini') else builtin.metrics_normal),
            ]:
                try:
                    m = metrics_getter
                    panel_sizes[mode_key] = [m.panel_width, m.panel_height]
                except Exception:
                    pass

            self._editing_theme = CustomTheme(
                theme_name="",
                display_name=f"{builtin.display_name} (模板)",
                colors=colors,
                based_on=theme_name,
                panel_sizes=panel_sizes,
            )
            self._is_new_theme = True
            self._is_template = True

        self._editing_theme_name = theme_name
        self._dirty = False
        self._sync_canvas_from_theme()
        self._refresh_panel_size_spins()
        self._update_title()

    def _sync_canvas_from_theme(self):
        """将编辑主题的数据同步到画布"""
        if not self._editing_theme:
            return
        theme = self._editing_theme
        self.canvas.set_theme(theme)
        self.canvas.colors = theme._colors.copy() if hasattr(theme, '_colors') else {}
        stickers = theme.get_stickers()
        self.canvas.set_stickers(stickers)

        # 根据 based_on 决定默认预建哪些组件
        based_on = getattr(theme, '_based_on', "modern")
        is_classical = based_on == "classical"
        if is_classical:
            # 经典主题布局：背景 + 时间 + 4 个进度环
            essential_types = ["background", "time", "day_ring", "week_ring", "month_ring", "year_ring"]
        else:
            # 现代主题布局：背景 + 时间 + 日期 + 日进度环 + 月年信息 + 待办 + 分隔线
            essential_types = ["background", "time", "date", "day_ring", "month_info", "todo_line", "divider"]

        # 合并持久化的组件状态（可能包含非默认组件）
        cs = getattr(theme, '_component_states', {})
        all_types = list(dict.fromkeys(essential_types + list(cs.keys())))

        # 批量重建，抑制中间信号避免属性面板反复刷新
        self.canvas.clear_all_functional_components()
        self.canvas._suppress_signals = True
        for ctype in all_types:
            self.canvas.add_component_by_type(ctype)
        self.canvas.apply_component_states(cs)
        self.canvas._suppress_signals = False
        self.canvas.update()

    def _refresh_panel_size_spins(self):
        """从编辑主题读取当前模式的尺寸并更新 spinbox"""
        if not self._editing_theme:
            return
        sz = self._editing_theme.get_panel_size(self._preview_mode)
        if sz:
            w, h = sz
        else:
            # 从 based_on 获取默认尺寸
            sizes = {"normal": (180, 80), "compact": (190, 66), "mini": (95, 40)}
            w, h = sizes.get(self._preview_mode, (180, 80))
        self.panel_w_spin.blockSignals(True)
        self.panel_h_spin.blockSignals(True)
        self.panel_w_spin.setValue(w)
        self.panel_h_spin.setValue(h)
        self.panel_w_spin.blockSignals(False)
        self.panel_h_spin.blockSignals(False)
        # 同步到画布
        self.canvas.set_panel_size(self._preview_mode, w, h)

    def _on_panel_size_changed(self):
        """面板尺寸 spinbox 变化 → 更新主题 + 画布"""
        if not self._editing_theme:
            return
        w, h = self.panel_w_spin.value(), self.panel_h_spin.value()
        self._editing_theme.set_panel_size(self._preview_mode, w, h)
        self.canvas.set_panel_size(self._preview_mode, w, h)
        self._dirty = True
        self._update_title()

    # ================================================================
    # 新建主题
    # ================================================================

    def _new_theme_dialog(self):
        """新建自定义主题 — 默认以 Modern 主题为模板"""
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self, "新建自定义主题", "主题名称:", text="我的主题"
        )
        if not ok or not name.strip():
            return

        # 默认以 modern 主题为模板
        if "modern" in theme_manager.available_themes:
            theme_manager.set_theme("modern")
        base_theme = theme_manager.current_theme
        colors = {}
        if hasattr(base_theme, '_COLORS'):
            colors = base_theme._COLORS.copy()
        # 获取面板尺寸
        panel_sizes = {
            "normal": [base_theme.metrics_normal.panel_width, base_theme.metrics_normal.panel_height],
        }
        if hasattr(base_theme, 'metrics_compact'):
            panel_sizes["compact"] = [base_theme.metrics_compact.panel_width, base_theme.metrics_compact.panel_height]
        if hasattr(base_theme, 'metrics_mini'):
            panel_sizes["mini"] = [base_theme.metrics_mini.panel_width, base_theme.metrics_mini.panel_height]

        self._editing_theme = CustomTheme(
            theme_name=name.strip(),
            display_name=name.strip(),
            colors=colors,
            based_on=base_theme.name,
            panel_sizes=panel_sizes,
        )
        self._is_new_theme = True
        self._is_template = False
        self._editing_theme_name = name.strip()
        self._dirty = True
        self._sync_canvas_from_theme()
        self._refresh_panel_size_spins()
        self._update_title()
        self.status_label.setText(f"新建主题: {name.strip()}")

    # ================================================================
    # 预览模式切换
    # ================================================================

    def _on_preview_mode_changed(self, idx):
        modes = ["normal", "compact", "mini"]
        self._preview_mode = modes[idx]
        self._refresh_panel_size_spins()
        self.canvas.set_preview_mode(self._preview_mode)

    # ================================================================
    # 组件交互事件
    # ================================================================

    def _on_component_requested(self, component_type: str):
        """组件面板请求添加组件"""
        self.canvas.add_component_by_type(component_type)

    def _on_canvas_selection(self, comp_data: dict | None):
        """画布选中状态改变 → 更新属性面板"""
        if comp_data:
            # 注入画布当前颜色供属性面板读取
            comp_data["_colors"] = self.canvas.colors
            self.property_panel.load_component(comp_data)
            x, y = comp_data.get("x", 0), comp_data.get("y", 0)
            self.coord_label.setText(f"X:{x:.3f}  Y:{y:.3f}")
        else:
            self.property_panel.clear()
            self.coord_label.setText("")

    def _on_canvas_component_moved(self, comp_data: dict):
        """画布组件移动 → 仅更新状态栏坐标，避免重建属性面板"""
        self._dirty = True
        x, y = comp_data.get("x", 0), comp_data.get("y", 0)
        self.coord_label.setText(f"X:{x:.3f}  Y:{y:.3f}")

    def _on_canvas_component_added(self, comp_data: dict):
        """画布新增组件 → 标记脏"""
        self._dirty = True
        if self._editing_theme:
            self._editing_theme._stickers = self.canvas.get_stickers()
            self._editing_theme._colors = self.canvas.colors.copy()

    def _on_canvas_component_deleted(self, comp_id: str):
        """画布删除组件 → 更新主题"""
        self._dirty = True
        if self._editing_theme:
            self._editing_theme._stickers = self.canvas.get_stickers()
            self._editing_theme._colors = self.canvas.colors.copy()

    def _on_property_changed(self, comp_id: str, key: str, value):
        """属性面板值变更 → 应用到画布组件"""
        self._dirty = True
        self.canvas.update_component_property(comp_id, key, value)
        self.canvas.update()
        # 颜色变更即时同步到编辑主题
        if key == "color_token" and self._editing_theme:
            self._editing_theme._colors = self.canvas.colors.copy()

    def _on_property_delete(self, comp_id: str):
        """属性面板删除请求 → 画布删除"""
        self._dirty = True
        self.canvas.delete_component(comp_id)

    # ================================================================
    # 保存
    # ================================================================

    def _save_theme(self):
        if not self._editing_theme:
            return
        if self._is_template:
            self._save_theme_as()
            return
        self._editing_theme._colors = self.canvas.colors.copy()
        self._editing_theme._stickers = self.canvas.get_stickers()
        self._editing_theme._component_states = self.canvas.get_component_states()
        theme_manager.add_custom_theme(self._editing_theme)
        self._dirty = False
        self._is_template = False
        self._refresh_theme_combo()
        self._update_title()
        self.status_label.setText(f"已保存: {self._editing_theme.display_name}")
        self.theme_saved.emit(self._editing_theme.name)

    def _save_theme_as(self):
        if not self._editing_theme:
            return
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self, "另存为", "主题名称:",
            text=self._editing_theme.display_name
        )
        if not ok or not name.strip():
            return

        self._editing_theme.name = name.strip()
        self._editing_theme.display_name = name.strip()
        self._editing_theme._colors = self.canvas.colors.copy()
        self._editing_theme._stickers = self.canvas.get_stickers()
        self._editing_theme._component_states = self.canvas.get_component_states()
        theme_manager.add_custom_theme(self._editing_theme)
        self._is_new_theme = False
        self._editing_theme_name = name.strip()
        self._dirty = False
        self._refresh_theme_combo()
        # 选中保存的主题
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == name.strip():
                self.theme_combo.setCurrentIndex(i)
                break
        self._update_title()
        self.status_label.setText(f"已另存为: {name.strip()}")
        self.theme_saved.emit(name.strip())

    # ================================================================
    # 辅助
    # ================================================================

    def _update_title(self):
        dirty = " *" if self._dirty else ""
        name = self._editing_theme.display_name if self._editing_theme else "无"
        self.status_label.setText(f"编辑: {name}{dirty}")
