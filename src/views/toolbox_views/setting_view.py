from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QGroupBox, QFormLayout, 
    QLineEdit, QPushButton, QHBoxLayout, QLabel, QComboBox, 
    QCheckBox, QColorDialog, QFrame, QSizePolicy, QToolButton, QSpacerItem,
    QSpinBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
import json
import os
from src.configs.defaul_config import defaul_config


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
        for key, value in self.config_data.items():
            if key == "colors":
                self.create_colors_group(value)
            elif isinstance(value, (str, int, bool)):
                self.create_general_group(key, value)
            elif isinstance(value, list):
                self.create_list_group(key, value)
            elif isinstance(value, dict):
                self.create_dict_group(key, value)
    
    def create_general_group(self, key, value):
        """创建常规设置组"""
        group = QGroupBox(key.replace('_', ' ').title())
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
    
    def create_list_group(self, key, value):
        """创建列表设置组"""
        group = QGroupBox(key.replace('_', ' ').title())
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
    
    def create_dict_group(self, key, value):
        """创建字典设置组"""
        group = QGroupBox(key.replace('_', ' ').title())
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