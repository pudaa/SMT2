from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QGroupBox, QFormLayout, 
    QLineEdit, QPushButton, QHBoxLayout, QLabel, QComboBox, 
    QCheckBox, QColorDialog, QFrame, QSizePolicy, QToolButton, QSpacerItem,
    QSpinBox, QDialog, QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
import json
import os
from src.configs.defaul_config import defaul_config
from src.utils.auto_start_manager import AutoStartManager
from src.themes import theme_manager
from src.themes.base_theme import CustomTheme
from src.configs.base_config import get_default_theme, set_default_theme

class SettingView(QScrollArea):
    # 信号，当配置更改时发出
    changes_made = Signal()
    
    def __init__(self):
        super().__init__()
        self.setObjectName("settingView")
        self.config_path = "resources/properties.json"
        self.config_data = self.load_config()
        self.original_config = self.config_data.copy()  # 保存原始配置用于恢复
        
        # 用于跟踪配置是否被修改
        self.config_modified = False
        self.default_config = defaul_config()
        
        # 初始化自启管理器
        self.auto_start_manager = AutoStartManager()
        
        # 主控件
        self.scrollWidget = QWidget()
        self.scrollWidget.setObjectName("scrollWidget")
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        
        # 主布局
        self.main_layout = QVBoxLayout(self.scrollWidget)
        self.main_layout.setAlignment(Qt.AlignTop)
        
        # 添加恢复默认按钮
        self.add_reset_button()
        
        # 创建配置卡片
        self.create_cards()
    
    def add_reset_button(self):
        """添加恢复默认按钮"""
        reset_layout = QHBoxLayout()
        reset_layout.addStretch()  # 添加弹性空间
        
        reset_btn = QPushButton("恢复默认")
        reset_btn.clicked.connect(self.reset_to_default)
        reset_btn.setMaximumWidth(100)
        reset_btn.setMinimumHeight(30)
        
        reset_layout.addWidget(reset_btn)
        self.main_layout.addLayout(reset_layout)
    
    def reset_to_default(self):
        """恢复到默认配置"""
        # 加载默认配置文件
        default_config_path = "resources/default_properties.json"
        if os.path.exists(default_config_path):
            # 从默认配置文件加载
            with open(default_config_path, 'r', encoding='utf-8') as f:
                default_config = json.load(f)
        else:
            # 如果没有默认配置文件，使用硬编码的默认值
            default_config = self.default_config.get_default_properties()
        
        # 更新当前配置
        self.config_data = default_config.copy()
        
        # 重新创建所有配置卡片
        self.recreate_all_cards()
        
        # 重置修改标志
        self.config_modified = False
        
        # 发出更改信号，通知应用按钮可以隐藏
        self.changes_made.emit()
    
    def recreate_all_cards(self):
        """重新创建所有配置卡片"""
        # 清除现有布局
        for i in reversed(range(self.main_layout.count())):
            item = self.main_layout.itemAt(i)
            if item.widget() and item.widget().objectName() not in ["scrollWidget"]:
                item.widget().setParent(None)
            elif item.layout():
                # 不删除恢复默认按钮的布局
                if not (item.layout().itemAt(0) and isinstance(item.layout().itemAt(0).widget(), QPushButton) and 
                        item.layout().itemAt(0).widget().text() == "恢复默认"):
                    self.clear_layout(item.layout())
        
        # 重新添加恢复默认按钮
        self.add_reset_button()
        
        # 重新创建配置卡片
        self.create_cards()
    
    def clear_layout(self, layout):
        """递归清理布局中的所有子项"""
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
            elif item.layout():
                self.clear_layout(item.layout())
    
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_config(self):
        """保存配置文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config_data, f, ensure_ascii=False, indent=4)
    
    def apply_changes(self):
        """应用更改到配置文件"""
        self.save_config()
        # 重置修改标志
        self.config_modified = False
    
    def create_cards(self):
        """创建配置卡片"""
        # ---- 主题配置（独立卡片，始终在最前） ----
        self.create_theme_group()
        
        group_names = {
            "colors": "颜色设置",
            "todo_file_name": "待办事项路径",
            "extractor_model": "标签提取模型",
            "todo_poses": "标签提取规则",
            "font": "字体设置",
            "auto_start": "开机自启"
        }
        for key, value in self.config_data.items():
            # default_theme 已在 create_theme_group 中处理
            if key == "default_theme":
                continue
            if key == "colors":
                self.create_colors_group(value)
            elif isinstance(value, bool) or str(value) in ['true', 'false']:
                self.create_is_active_group(group_names[key], key, value)
            elif isinstance(value, (str, int)):
                self.create_general_group(group_names[key], key, value)
            elif isinstance(value, list):
                self.create_list_group(group_names[key], key, value)
            elif isinstance(value, dict):
                self.create_dict_group(group_names[key], key, value)
    
    def create_general_group(self, group_name, key, value):
        """创建常规设置组"""
        group = QGroupBox(group_name)
        layout = QFormLayout(group)
        
        if isinstance(value, str):
            # 创建可编辑的行
            line_edit = QLineEdit(str(value))
            line_edit.setObjectName(f"edit_{key}")
            line_edit.textChanged.connect(lambda: self.on_config_changed(key, line_edit.text()))
            layout.addRow(key.replace('_', ' ').title() + ":", line_edit)
        elif isinstance(value, (int, bool)):
            # 对于非字符串值，也创建可编辑的行
            line_edit = QLineEdit(str(value))
            line_edit.setObjectName(f"edit_{key}")
            line_edit.textChanged.connect(lambda: self.on_config_changed(key, line_edit.text()))
            layout.addRow(key.replace('_', ' ').title() + ":", line_edit)
        
        self.main_layout.addWidget(group)
        
    def create_is_active_group(self, group_name, key, value):
        """创建是否激活设置组"""
        group = QGroupBox(group_name)
        layout = QVBoxLayout(group)
        
        checkbox = QCheckBox("启用开机自启")
        # 优先使用注册表实际状态；如果注册表中没有值，则使用配置文件中的值
        registry_status = False
        try:
            registry_status = self.auto_start_manager.is_auto_start_enabled()
        except Exception:
            registry_status = False

        config_value = self.config_data.get(key, False)
        if isinstance(config_value, str):
            config_value = config_value.lower() in ['true', '1', 'yes']

        final_state = registry_status if registry_status else bool(config_value)
        checkbox.setChecked(bool(final_state))
        checkbox.setObjectName(f"checkbox_{key}")
        checkbox.stateChanged.connect(lambda state, k=key: self.on_auto_start_changed(k, state))
        
        label = QLabel("启用后，程序将在系统启动时自动运行")
        label.setStyleSheet("color: #888; font-size: 12px;")
        
        layout.addWidget(checkbox)
        layout.addWidget(label)
        self.main_layout.addWidget(group)
    
    def create_list_group(self, group_name, key, value):
        """创建列表设置组"""
        group = QGroupBox(group_name)
        layout = QVBoxLayout(group)
        
        # 创建一个容器来显示列表项
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container.setObjectName(f"list_container_{key}")
        
        # 显示当前列表内容
        self.create_list_items(container_layout, key, value)
        
        layout.addWidget(container)
        
        # 添加按钮来添加新项
        add_btn = QPushButton("+ 添加项")
        add_btn.clicked.connect(lambda: self.add_list_item(container_layout, key))
        layout.addWidget(add_btn)
        
        self.main_layout.addWidget(group)
    
    def create_list_items(self, layout, key, values):
        """创建列表项"""
        # 清除现有项
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
            elif item.layout():
                # 如果是布局，需要递归清理
                self.clear_layout(item.layout())
        
        for i, value in enumerate(values):
            item_layout = QHBoxLayout()
            
            line_edit = QLineEdit(str(value))
            line_edit.setObjectName(f"list_item_{key}_{i}")
            line_edit.textChanged.connect(lambda: self.on_config_changed(key, self.get_list_values(key)))
            
            delete_btn = QToolButton()
            delete_btn.setText("×")
            delete_btn.clicked.connect(lambda i=i: self.remove_list_item(layout, key, i))
            
            item_layout.addWidget(line_edit)
            item_layout.addWidget(delete_btn)
            
            layout.addLayout(item_layout)
    
    def add_list_item(self, layout, key):
        """添加列表项"""
        item_layout = QHBoxLayout()
        
        line_edit = QLineEdit("")
        line_edit.setObjectName(f"list_item_{key}_{layout.count()}")
        line_edit.textChanged.connect(lambda: self.on_config_changed(key, self.get_list_values(key)))
        
        delete_btn = QToolButton()
        delete_btn.setText("×")
        delete_btn.clicked.connect(lambda: self.remove_list_item(layout, key, layout.count()-1))
        
        item_layout.addWidget(line_edit)
        item_layout.addWidget(delete_btn)
        
        layout.addLayout(item_layout)
        
        # 更新配置
        self.on_config_changed(key, self.get_list_values(key))
    
    def remove_list_item(self, layout, key, index):
        """移除列表项"""
        # 获取当前布局中的所有项
        items = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.layout():
                h_layout = item.layout()
                if h_layout.count() >= 2:
                    line_edit = h_layout.itemAt(0).widget()
                    items.append(line_edit.text())
        
        # 移除指定索引的项
        if 0 <= index < len(items):
            items.pop(index)
        
        # 重新创建所有项
        self.create_list_items(layout.parentWidget().layout(), key, items)
        self.on_config_changed(key, items)
    
    def get_list_values(self, key):
        """获取列表值"""
        container = self.findChild(QWidget, f"list_container_{key}")
        if container:
            values = []
            for i in range(container.layout().count()):
                item = container.layout().itemAt(i)
                if item.layout() and item.layout().count() >= 1:
                    line_edit = item.layout().itemAt(0).widget()
                    if isinstance(line_edit, QLineEdit):
                        values.append(line_edit.text())
            return values
        return []
    
    def create_dict_group(self, group_name, key, value):
        """创建字典设置组"""
        group = QGroupBox(group_name)
        layout = QVBoxLayout(group)
        
        form_layout = QFormLayout()
        
        for sub_key, sub_value in value.items():
            if isinstance(sub_value, (str, int, bool)):
                line_edit = QLineEdit(str(sub_value))
                line_edit.setObjectName(f"edit_{key}_{sub_key}")
                line_edit.textChanged.connect(
                    lambda text, k=key, sk=sub_key: self.on_config_changed_in_dict(k, sk, text)
                )
                
                form_layout.addRow(sub_key.replace('_', ' ').title() + ":", line_edit)
        
        layout.addLayout(form_layout)
        self.main_layout.addWidget(group)
    
    def create_colors_group(self, colors_dict):
        """创建颜色设置组"""
        group = QGroupBox("颜色设置")
        layout = QVBoxLayout(group)
        
        for color_key, color_value in colors_dict.items():
            color_layout = QHBoxLayout()
            
            # 颜色名称标签
            label = QLabel(color_key.replace('_', ' ').title() + ":")
            label.setMinimumWidth(150)
            color_layout.addWidget(label)
            
            # 添加弹簧以将按钮推到右侧
            color_layout.addStretch()
            
            # 颜色预览按钮
            color_btn = QPushButton("选择颜色")
            color_btn.setMaximumWidth(100)
            
            # 设置按钮样式为颜色预览
            qcolor = self.convert_to_qcolor(color_value)
            color_btn.setStyleSheet(f"background-color: {qcolor.name()}; color: {'white' if qcolor.lightness() < 128 else 'black'};")
            
            # 连接颜色选择事件
            color_btn.clicked.connect(
                lambda _, ck=color_key, cb=color_btn: self.select_color(ck, cb)
            )
            
            color_layout.addWidget(color_btn)
            
            # Alpha值编辑
            alpha_label = QLabel("a:")
            alpha_label.setMaximumWidth(40)
            color_layout.addWidget(alpha_label)
            
            # Alpha值显示和编辑
            alpha_spinbox = QSpinBox()
            alpha_spinbox.setRange(0, 255)
            alpha_spinbox.setValue(qcolor.alpha())
            alpha_spinbox.setMaximumWidth(70)
            alpha_spinbox.setMinimumWidth(60)
            alpha_spinbox.valueChanged.connect(
                lambda value, ck=color_key, cb=color_btn, sb=alpha_spinbox: self.update_alpha(ck, cb, sb, value)
            )
            
            color_layout.addWidget(alpha_spinbox)
            
            # 颜色值显示
            color_value_label = QLabel(f"{qcolor.name()}")
            color_value_label.setMinimumWidth(100)
            color_layout.addWidget(color_value_label)
            
            # 将颜色选择器存储起来，方便更新
            color_btn.color_value_label = color_value_label
            color_btn.qcolor = qcolor
            color_btn.color_key = color_key
            color_btn.alpha_spinbox = alpha_spinbox
            
            layout.addLayout(color_layout)
        
        self.main_layout.addWidget(group)

    # ================================================================
    # 主题配置卡片
    # ================================================================
    
    def create_theme_group(self):
        """创建主题选择与自定义编辑卡片"""
        group = QGroupBox("主题设置")
        layout = QVBoxLayout(group)
        
        # ---- 行1: 主题选择 + 操作按钮 ----
        row1 = QHBoxLayout()
        
        row1.addWidget(QLabel("当前主题:"))
        
        self.theme_combo = QComboBox()
        self._refresh_theme_combo()
        self.theme_combo.currentIndexChanged.connect(self._on_theme_combo_changed)
        row1.addWidget(self.theme_combo)
        
        # 新建自定义主题按钮
        new_btn = QPushButton("+ 新建自定义主题")
        new_btn.setMaximumWidth(140)
        new_btn.clicked.connect(self._create_custom_theme_dialog)
        row1.addWidget(new_btn)
        
        row1.addStretch()
        layout.addLayout(row1)
        
        # ---- 行2: 记住主题选择 ----
        self.remember_theme_cb = QCheckBox("记住主题选择（启动时自动恢复）")
        saved_theme = get_default_theme()
        self.remember_theme_cb.setChecked(saved_theme == theme_manager.current_theme_name)
        self.remember_theme_cb.stateChanged.connect(self._on_remember_theme_changed)
        layout.addWidget(self.remember_theme_cb)
        
        # ---- 自定义主题编辑区（初始隐藏） ----
        self.custom_editor_container = QWidget()
        self.custom_editor_container.setVisible(False)
        editor_layout = QVBoxLayout(self.custom_editor_container)
        editor_layout.setContentsMargins(8, 8, 8, 8)
        
        # 标签信息
        self.custom_theme_name_label = QLabel()
        self.custom_theme_name_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        editor_layout.addWidget(self.custom_theme_name_label)
        
        # 颜色编辑区域（滚动）
        self.custom_color_layout = QVBoxLayout()
        editor_layout.addLayout(self.custom_color_layout)
        
        # 操作按钮行
        btn_row = QHBoxLayout()
        save_btn = QPushButton("💾 保存主题")
        save_btn.clicked.connect(self._save_custom_theme)
        btn_row.addWidget(save_btn)
        
        delete_btn = QPushButton("🗑 删除主题")
        delete_btn.setStyleSheet("color: #e05555;")
        delete_btn.clicked.connect(self._delete_custom_theme)
        btn_row.addWidget(delete_btn)
        
        btn_row.addStretch()
        editor_layout.addLayout(btn_row)
        
        layout.addWidget(self.custom_editor_container)
        
        # 存储当前正在编辑的自定义主题引用
        self._editing_custom_theme: CustomTheme | None = None
        
        self.main_layout.addWidget(group)
    
    def _refresh_theme_combo(self):
        """刷新主题下拉框选项"""
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()
        for t in theme_manager.available_themes:
            label = f"{t['display']} {'(自定义)' if t['is_custom'] else '(内置)'}"
            self.theme_combo.addItem(label, t["name"])
        # 选中当前主题
        idx = self.theme_combo.findData(theme_manager.current_theme_name)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.blockSignals(False)
    
    def _on_theme_combo_changed(self, index: int):
        """主题下拉框选择变化"""
        theme_name = self.theme_combo.itemData(index)
        if not theme_name:
            return
        
        theme_manager.set_theme(theme_name)
        self.changes_made.emit()
        
        # ★ 如果"记住主题"已勾选，切换后自动保存为新默认
        if self.remember_theme_cb.isChecked():
            set_default_theme(theme_name)
        
        # 判断是否为自定义主题，显示/隐藏编辑器
        ct = theme_manager.get_custom_theme(theme_name)
        if ct:
            self._show_custom_editor(ct)
        else:
            self.custom_editor_container.setVisible(False)
            self._editing_custom_theme = None
    
    def _on_remember_theme_changed(self, state: int):
        """记住主题复选框变化"""
        if state == Qt.Checked:
            set_default_theme(theme_manager.current_theme_name)
        else:
            set_default_theme("classical")
    
    def _show_custom_editor(self, ct: CustomTheme):
        """显示自定义主题颜色编辑器"""
        self._editing_custom_theme = ct
        self.custom_editor_container.setVisible(True)
        self.custom_theme_name_label.setText(f"编辑: {ct.display_name}")
        
        # 清空并重建颜色行
        for i in reversed(range(self.custom_color_layout.count())):
            w = self.custom_color_layout.itemAt(i).widget()
            if w:
                w.deleteLater()
        
        for token, color_val in ct._colors.items():
            self._add_color_edit_row(token, color_val)
    
    def _add_color_edit_row(self, token: str, color_val: list[int]):
        """添加一行颜色编辑器"""
        row = QHBoxLayout()
        
        label = QLabel(token.replace('_', ' '))
        label.setMinimumWidth(180)
        row.addWidget(label)
        
        row.addStretch()
        
        color_btn = QPushButton()
        color_btn.setFixedSize(36, 36)
        color_btn.setCursor(Qt.PointingHandCursor)
        qc = self._list_to_qcolor(color_val)
        self._style_color_btn(color_btn, qc)
        
        # 存储附加数据
        color_btn._token = token
        color_btn._qcolor = qc
        color_btn._alpha_spin = None
        color_btn.clicked.connect(lambda _, cb=color_btn: self._pick_custom_color(cb))
        
        row.addWidget(color_btn)
        
        # Alpha 微调
        alpha_spin = QSpinBox()
        alpha_spin.setRange(0, 255)
        alpha_spin.setValue(qc.alpha())
        alpha_spin.setFixedWidth(56)
        alpha_spin.setPrefix("α ")
        alpha_spin.valueChanged.connect(lambda v, cb=color_btn: self._update_custom_alpha(cb, v))
        color_btn._alpha_spin = alpha_spin
        row.addWidget(alpha_spin)
        
        self.custom_color_layout.addLayout(row)
    
    def _pick_custom_color(self, color_btn: QPushButton):
        """打开颜色选择器"""
        qc = color_btn._qcolor
        color = QColorDialog.getColor(qc, self, "选择颜色", QColorDialog.ShowAlphaChannel)
        if color.isValid():
            color_btn._qcolor = QColor(color.red(), color.green(), color.blue(), color.alpha())
            self._style_color_btn(color_btn, color_btn._qcolor)
            if color_btn._alpha_spin:
                color_btn._alpha_spin.blockSignals(True)
                color_btn._alpha_spin.setValue(color.alpha())
                color_btn._alpha_spin.blockSignals(False)
            self._mark_custom_dirty()
    
    def _update_custom_alpha(self, color_btn: QPushButton, alpha: int):
        """更新自定义颜色alpha值"""
        qc = color_btn._qcolor
        color_btn._qcolor = QColor(qc.red(), qc.green(), qc.blue(), alpha)
        self._style_color_btn(color_btn, color_btn._qcolor)
        self._mark_custom_dirty()
    
    def _style_color_btn(self, btn: QPushButton, qc: QColor):
        """设置颜色按钮的样式"""
        hex_name = qc.name()
        text_color = 'white' if qc.lightness() < 128 else 'black'
        btn.setStyleSheet(
            f"background-color: {hex_name}; "
            f"border: 1px solid #888; border-radius: 6px; "
            f"min-width: 36px; min-height: 36px;"
        )
    
    def _mark_custom_dirty(self):
        """标记自定义主题已修改"""
        if self._editing_custom_theme and self.custom_editor_container.isVisible():
            self.changes_made.emit()
    
    def _save_custom_theme(self):
        """保存当前编辑的自定义主题"""
        ct = self._editing_custom_theme
        if not ct:
            return
        
        # 从 UI 控件收集颜色
        new_colors = {}
        for i in range(self.custom_color_layout.count()):
            item = self.custom_color_layout.itemAt(i)
            if item.layout():
                h_layout = item.layout()
                if h_layout.count() >= 3:
                    color_btn = h_layout.itemAt(1).widget()
                    if isinstance(color_btn, QPushButton) and hasattr(color_btn, '_token'):
                        qc = color_btn._qcolor
                        new_colors[color_btn._token] = [qc.red(), qc.green(), qc.blue(), qc.alpha()]
        
        ct._colors = new_colors
        theme_manager.add_custom_theme(ct)
        theme_manager.set_theme(ct.name)
        self._refresh_theme_combo()
    
    def _delete_custom_theme(self):
        """删除当前自定义主题"""
        ct = self._editing_custom_theme
        if not ct:
            return
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除自定义主题「{ct.display_name}」吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            theme_manager.remove_custom_theme(ct.name)
            self._editing_custom_theme = None
            self.custom_editor_container.setVisible(False)
            self._refresh_theme_combo()
    
    def _create_custom_theme_dialog(self):
        """弹出新建自定义主题对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("新建自定义主题")
        dialog.setMinimumWidth(360)
        layout = QVBoxLayout(dialog)
        
        # 名称
        layout.addWidget(QLabel("主题名称:"))
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("例如：我的暗夜主题")
        layout.addWidget(name_edit)
        
        # 基于哪个主题
        layout.addWidget(QLabel("基于哪个主题的布局:"))
        base_combo = QComboBox()
        for t in theme_manager.available_themes:
            if not t["is_custom"]:
                base_combo.addItem(t["display"], t["name"])
        layout.addWidget(base_combo)
        
        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.Accepted:
            name = name_edit.text().strip()
            if not name:
                return
            # 生成唯一 key
            import re
            key = re.sub(r'[^a-zA-Z\u4e00-\u9fff0-9_-]', '_', name).lower()
            if not key:
                key = f"custom_{len(theme_manager.get_all_custom_themes()) + 1}"
            
            # 基于选定主题复制颜色
            based_on = base_combo.currentData()
            source_colors = {}
            if based_on:
                theme_manager.set_theme(based_on)
                source_colors = theme_manager.get_all_colors()
            
            ct = CustomTheme(
                theme_name=key,
                display_name=name,
                colors=source_colors,
                based_on=based_on or "classical",
            )
            theme_manager.add_custom_theme(ct)
            theme_manager.set_theme(key)
            self._refresh_theme_combo()
            self._show_custom_editor(ct)
    
    @staticmethod
    def _list_to_qcolor(color_val: list[int]) -> QColor:
        if len(color_val) >= 4:
            return QColor(color_val[0], color_val[1], color_val[2], color_val[3])
        elif len(color_val) >= 3:
            return QColor(color_val[0], color_val[1], color_val[2])
        return QColor(200, 200, 200)

    # ================================================================
    # 原有颜色设置方法
    # ================================================================

    def update_alpha(self, color_key, color_btn, alpha_spinbox, value):
        """更新alpha值"""
        # 获取当前颜色
        current_color = color_btn.qcolor
        new_color = QColor(current_color.red(), current_color.green(), current_color.blue(), value)
        
        # 更新配置
        current_colors = self.config_data.get("colors", {})
        color_list = [current_color.red(), current_color.green(), current_color.blue(), value]
        current_colors[color_key] = color_list
        self.config_data["colors"] = current_colors
        self.save_config()
        
        # 更新按钮样式
        color_btn.setStyleSheet(f"background-color: {new_color.name()}; color: {'white' if new_color.lightness() < 128 else 'black'};")
        color_btn.qcolor = new_color
        color_btn.color_value_label.setText(f"{new_color.name()}")
        
        # 发出更改信号
        self.changes_made.emit()
    
    def convert_to_qcolor(self, color_value):
        """将配置中的颜色值转换为QColor对象"""
        if isinstance(color_value, list):
            if len(color_value) == 3:
                r, g, b = color_value
                return QColor(r, g, b)
            elif len(color_value) == 4:
                r, g, b, a = color_value
                return QColor(r, g, b, a)
        elif isinstance(color_value, str):
            if color_value.startswith('#'):
                return QColor(color_value)
        return QColor(255, 255, 255)  # 默认白色
    
    def select_color(self, color_key, color_btn):
        """选择颜色"""
        current_color = color_btn.qcolor
        color = QColorDialog.getColor(current_color, self, "选择颜色")
        
        if color.isValid():
            # 更新颜色值
            color_list = [color.red(), color.green(), color.blue()]
            if color.alpha() != 255:
                color_list.append(color.alpha())
            
            # 更新配置
            current_colors = self.config_data.get("colors", {})
            current_colors[color_key] = color_list
            self.config_data["colors"] = current_colors
            
            # 更新按钮样式
            color_btn.setStyleSheet(f"background-color: {color.name()}; color: {'white' if color.lightness() < 128 else 'black'};")
            color_btn.qcolor = color
            color_btn.color_value_label.setText(f"{color.name()}")
            
            # 发出更改信号
            self.changes_made.emit()
    
    def on_config_changed(self, key, value):
        """当配置更改时调用"""
        # 尝试转换值为适当的类型
        if isinstance(self.original_config.get(key), int):
            try:
                value = int(value)
            except ValueError:
                pass  # 保持字符串值
        elif isinstance(self.original_config.get(key), bool):
            if isinstance(value, str):
                if value.lower() in ['true', '1', 'yes', 'on']:
                    value = True
                elif value.lower() in ['false', '0', 'no', 'off']:
                    value = False
        
        self.config_data[key] = value
        self.config_modified = True
        self.changes_made.emit()
    
    def on_config_changed_in_dict(self, dict_key, sub_key, value):
        """当字典中的配置更改时调用"""
        # 获取当前字典
        current_dict = self.config_data.get(dict_key, {})
        
        # 尝试转换值为适当的类型
        original_value = self.original_config.get(dict_key, {}).get(sub_key)
        if isinstance(original_value, int):
            try:
                value = int(value)
            except ValueError:
                pass  # 保持字符串值
        elif isinstance(original_value, bool):
            if isinstance(value, str):
                if value.lower() in ['true', '1', 'yes', 'on']:
                    value = True
                elif value.lower() in ['false', '0', 'no', 'off']:
                    value = False
        
        # 更新字典
        current_dict[sub_key] = value
        self.config_data[dict_key] = current_dict
        self.config_modified = True
        self.changes_made.emit()
    
    def on_auto_start_changed(self, key, state):
        """当开机自启状态改变时调用"""
        enabled = int(state) == 2
        
        current_status = self.auto_start_manager.is_auto_start_enabled()
        
        # print(f"=== 开机自启状态变化 ===")
        # print(f"复选框状态值：{state}, 转换为整数：{int(state)}")
        # print(f"目标启用：{enabled}, 当前注册表状态：{current_status}")
        
        if enabled and not current_status:
            success = self.auto_start_manager.enable_auto_start()
            operation = "启用"
        elif not enabled and current_status:
            success = self.auto_start_manager.disable_auto_start()
            operation = "禁用"
        else:
            success = True
            operation = "状态未改变"
        
        new_status = self.auto_start_manager.is_auto_start_enabled()
        # print(f"操作类型：{operation}, 操作结果：{success}, 实际状态：{new_status}")
        # print(f"========================")
        
        if success:
            # 保存为布尔值（注册表的实际状态）
            self.config_data[key] = bool(new_status)
            self.config_modified = True
            
            self.save_config()
            
            self.changes_made.emit()
        else:
            print(f"操作失败")
            checkbox = self.sender()
            if checkbox:
                checkbox.blockSignals(True)
                checkbox.setChecked(not enabled)
                checkbox.blockSignals(False)