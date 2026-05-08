"""属性面板 — 右侧编辑选中组件的属性"""
from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpinBox,
    QDoubleSpinBox, QPushButton, QColorDialog, QFrame,
    QCheckBox, QSlider
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor


# 文字组件类型（字号替代宽高）
_TEXT_TYPES = {"time", "date", "month_info", "todo_line"}


class PropertyPanel(QWidget):
    """属性编辑面板

    信号:
        property_changed(str, str, value) — comp_id, key, value
        component_deleted(str)           — comp_id
    """

    property_changed = Signal(str, str, object)
    component_deleted = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("propertyPanel")
        self.setMaximumWidth(300)

        self._current_comp: dict | None = None
        self._widgets: dict = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 标题
        self.title_label = QLabel("属性")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(self.title_label)

        # 组件信息
        self.info_label = QLabel("未选中组件")
        self.info_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.info_label)

        # 分隔
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #555;")
        layout.addWidget(sep)

        # 属性编辑区域
        self._prop_layout = QVBoxLayout()
        layout.addLayout(self._prop_layout)

        layout.addStretch()

        # 删除按钮
        self.delete_btn = QPushButton("🗑️ 删除组件")
        self.delete_btn.setStyleSheet("color: #e55; font-weight: bold;")
        self.delete_btn.clicked.connect(self._on_delete)
        self.delete_btn.hide()
        layout.addWidget(self.delete_btn)

    def load_component(self, comp_data: dict | None):
        """加载组件数据显示其可编辑属性"""
        self._clear_props()
        self._current_comp = comp_data

        if not comp_data:
            self.info_label.setText("未选中组件")
            self.delete_btn.hide()
            return

        ct = comp_data.get("comp_type", "unknown")
        cid = comp_data.get("comp_id", "")
        name = comp_data.get("name", "未知")
        category = comp_data.get("category", "")
        locked = comp_data.get("locked", False)
        visible = comp_data.get("visible", True)

        self.info_label.setText(f"{name} ({category})\n类型: {ct}")
        is_background = ct == "background"
        is_deletable = not locked and comp_data.get("deletable", True)
        if is_background:
            self.delete_btn.setVisible(False)
        else:
            self.delete_btn.setVisible(is_deletable or locked)
            if locked:
                self.delete_btn.setText("👁️ 显示组件" if not visible else "👁️ 隐藏组件")
                self.delete_btn.setStyleSheet("color: #aaa; font-weight: bold;")
            else:
                self.delete_btn.setText("🗑️ 删除组件")
                self.delete_btn.setStyleSheet("color: #e55; font-weight: bold;")

        # ---- 通用属性 ----
        self._add_double_spin("x", "X 位置", comp_data.get("x", 0.5), 0.0, 1.0, 0.01, cid)
        self._add_double_spin("y", "Y 位置", comp_data.get("y", 0.5), 0.0, 1.0, 0.01, cid)

        # ---- 文字组件：字号；其他组件：宽高 ----
        if ct in _TEXT_TYPES:
            extra = comp_data.get("extra", {})
            fs = extra.get("font_size", 12)
            self._add_double_spin("font_size", "字号", fs, 6, 48, 1, cid)
        else:
            self._add_double_spin("width", "宽度", comp_data.get("width", 0.15), 0.02, 1.0, 0.01, cid)
            self._add_double_spin("height", "高度", comp_data.get("height", 0.10), 0.01, 0.8, 0.01, cid)

        # ---- 可见性（所有组件） ----
        self._add_checkbox("visible", "可见", visible, cid)

        # ---- 颜色（功能组件专属） ----
        color_key = COMPONENT_COLOR_MAP.get(ct, "")
        if color_key:
            extra = comp_data.get("extra", {})
            # 优先从画布当前颜色取值，否则默认白色
            active_colors = comp_data.get("_colors", {})
            current_rgba = extra.get("color_token") or active_colors.get(color_key, [255, 255, 255])
            self._add_color_picker("color_token", f"颜色 ({color_key.split('_')[-1]})", current_rgba, cid, color_key)

        # ---- 贴纸专属 ----
        if ct == "sticker":
            extra = comp_data.get("extra", {})
            self._add_double_spin("scale", "缩放", extra.get("scale", 1.0), 0.05, 5.0, 0.05, cid, "extra")
            self._add_double_spin("rotation", "旋转(°)", extra.get("rotation", 0.0), 0, 360, 1.0, cid, "extra")
            self._add_double_spin("opacity", "透明度", extra.get("opacity", 1.0), 0.0, 1.0, 0.05, cid, "extra")
            self._add_line_edit("name", "名称", extra.get("name", ""), cid, "extra")

    def clear(self):
        self.load_component(None)

    def _clear_props(self):
        """清除属性编辑控件"""
        while self._prop_layout.count():
            item = self._prop_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
            elif item.layout():
                self._clear_layout(item.layout())
        self._widgets.clear()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
            elif item.layout():
                self._clear_layout(item.layout())

    def _add_line_edit(self, key: str, label: str, value, comp_id: str, scope: str = ""):
        row = QVBoxLayout()
        row.addWidget(QLabel(label))
        edit = QLineEdit(str(value))
        full_key = f"{scope}.{key}" if scope else key
        self._widgets[full_key] = edit
        edit.textChanged.connect(
            lambda text, cid=comp_id, k=key: self.property_changed.emit(cid, k, text)
        )
        row.addWidget(edit)
        self._prop_layout.addLayout(row)

    def _add_checkbox(self, key: str, label: str, value: bool, comp_id: str):
        row = QVBoxLayout()
        cb = QCheckBox(label)
        cb.setChecked(bool(value))
        self._widgets[key] = cb
        cb.stateChanged.connect(
            lambda state, cid=comp_id, k=key: self.property_changed.emit(cid, k, state == Qt.Checked)
        )
        row.addWidget(cb)
        self._prop_layout.addLayout(row)

    def _add_double_spin(self, key: str, label: str, value: float,
                         min_v: float, max_v: float, step: float,
                         comp_id: str, scope: str = ""):
        row = QVBoxLayout()
        row.addWidget(QLabel(label))
        spin = QDoubleSpinBox()
        spin.setRange(min_v, max_v)
        spin.setSingleStep(step)
        spin.setDecimals(3)
        spin.setValue(float(value))
        full_key = f"{scope}.{key}" if scope else key
        self._widgets[full_key] = spin
        spin.valueChanged.connect(
            lambda v, cid=comp_id, k=key: self.property_changed.emit(cid, k, v)
        )
        row.addWidget(spin)
        self._prop_layout.addLayout(row)

    def _add_color_picker(self, key: str, label: str, rgba: list, comp_id: str, color_key: str):
        """添加颜色选择行"""
        row = QVBoxLayout()
        row.addWidget(QLabel(label))
        btn_row = QHBoxLayout()
        btn = QPushButton()
        btn.setFixedSize(36, 36)
        btn.setCursor(Qt.PointingHandCursor)
        qc = QColor(*rgba[:3], rgba[3] if len(rgba) >= 4 else 255)
        btn.setStyleSheet(
            f"background-color: {qc.name()}; border: 1px solid #666; border-radius: 6px;"
        )
        btn._qcolor = qc
        btn._comp_id = comp_id
        btn._color_key = color_key
        btn.clicked.connect(lambda _, b=btn: self._pick_color(b))
        btn_row.addWidget(btn)
        btn_row.addStretch()
        row.addLayout(btn_row)
        self._prop_layout.addLayout(row)

    def _pick_color(self, btn: QPushButton):
        color = QColorDialog.getColor(btn._qcolor, self, "选择颜色", QColorDialog.ShowAlphaChannel)
        if color.isValid():
            btn._qcolor = QColor(color.red(), color.green(), color.blue(), color.alpha())
            btn.setStyleSheet(
                f"background-color: {color.name()}; border: 1px solid #666; border-radius: 6px;"
            )
            rgba = [color.red(), color.green(), color.blue(), color.alpha()]
            c = self._current_comp
            if c:
                c["extra"] = c.get("extra", {})
                c["extra"]["color_token"] = rgba
                c["extra"]["color_key"] = btn._color_key
            self.property_changed.emit(btn._comp_id, "color_token", rgba)

    def _on_delete(self):
        if not self._current_comp:
            return
        cid = self._current_comp.get("comp_id", "")
        locked = self._current_comp.get("locked", False)
        if locked:
            # 功能组件：切换可见性
            current = self._current_comp.get("visible", True)
            new_val = not current
            self._current_comp["visible"] = new_val
            self.delete_btn.setText("👁️ 显示组件" if not new_val else "👁️ 隐藏组件")
            self.property_changed.emit(cid, "visible", new_val)
            # 刷新勾选框
            for k, w in self._widgets.items():
                if k == "visible" and isinstance(w, QCheckBox):
                    w.setChecked(new_val)
                    break
        else:
            self.component_deleted.emit(cid)


# 组件类型 → 颜色令牌映射
COMPONENT_COLOR_MAP = {
    "background":"performance_panel_background",
    "time":      "performance_panel_time",
    "date":      "performance_panel_date",
    "day_ring":  "performance_panel_progress_ring_foreground",
    "week_ring": "performance_panel_progress_ring_foreground",
    "month_ring":"performance_panel_progress_ring_foreground",
    "year_ring": "performance_panel_progress_ring_foreground",
    "month_info":"performance_panel_sub_info",
    "todo_line": "performance_panel_todo_text",
    "divider":   "performance_panel_divider",
}
