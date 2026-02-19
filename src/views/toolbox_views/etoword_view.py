import sys
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QSplitter, QComboBox, QListWidget, QLineEdit,
                               QScrollArea, QPushButton, QApplication,
                               QMessageBox)
from PySide6.QtCore import Qt, QMimeData, QByteArray, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QDragMoveEvent, QDrag
import pandas as pd
from docx import Document
from typing import Optional
from collections import OrderedDict

class DraggableListWidget(QListWidget):
    """可拖拽的列表组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DragDropMode.DragOnly)
    
    def startDrag(self, supportedActions):
        """开始拖拽操作"""
        item = self.currentItem()
        if item:
            mimeData = QMimeData()
            # 获取当前选择的模式（如果存在mode_combo则使用它）
            mode = "列模式"
            parent = self.parent()
            if parent and hasattr(parent, 'mode_combo') and parent.mode_combo is not None:
                try:
                    mode = parent.mode_combo.currentText()
                except Exception:
                    mode = "列模式"
            # 将数据序列化为字节流
            data_str = f"{item.text()}|{mode}"
            mimeData.setData("application/x-etoword-item", QByteArray(data_str.encode()))
            
            drag = QDrag(self)
            drag.setMimeData(mimeData)
            drag.exec_(Qt.DropAction.CopyAction)

class DropAreaWidget(QWidget):
    """可接收拖拽的区域"""
    item_dropped = Signal(str, str)  # 发送标题和模式信号
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        self.label = QLabel("拖拽项目到这里添加到模板")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setObjectName("dropAreaLabel")
        layout.addWidget(self.label)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-etoword-item"):
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-etoword-item"):
            data = event.mimeData().data("application/x-etoword-item").data().decode()
            title, mode = data.split("|")
            self.item_dropped.emit(title, mode)
            event.acceptProposedAction()
        else:
            event.ignore()

        

class PreviewItemWidget(QWidget):
    """预览项小部件 - 同时支持显示和拖拽"""
    # 定义删除信号
    item_deleted = Signal(int)  # 发送要删除的索引
    
    def __init__(self, index, item, parent=None):
        super().__init__(parent)
        self.index = index
        self.item = item
        self.setAcceptDrops(True)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(5)
        
        # 显示标签（可点击编辑）
        self.label = QLabel(self.item["value"])
        self.label.setWordWrap(True)
        self.label.setObjectName("previewItemLabel")
        layout.addWidget(self.label)
        
        # 样式选择
        self.style_combo = QComboBox()
        self.style_combo.addItems(["默认", "二级标题", "无序列表", "有序列表"])
        self.style_combo.setCurrentText(self.item["style"])
        self.style_combo.currentTextChanged.connect(self.on_style_changed)
        self.style_combo.setFixedWidth(100)
        layout.addWidget(self.style_combo)
        
        # 删除按钮
        self.delete_btn = QPushButton("✕")
        self.delete_btn.setFixedSize(40, 25)
        self.delete_btn.clicked.connect(self.on_delete_clicked)
        layout.addWidget(self.delete_btn)
        
        # 拖拽支持
        self.setMouseTracking(True)
    
    def on_style_changed(self, style):
        self.item["style"] = style
        # 更新显示文本
        self.label.setText(self.item["value"])
    
    def on_delete_clicked(self):
        """删除按钮点击处理"""
        self.item_deleted.emit(self.index)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_drag()
        try:
            super().mousePressEvent(event)
        except RuntimeError:
            # 有时父组件在拖拽期间已删除该C++对象，捕获并忽略该错误以避免崩溃
            pass
    
    def start_drag(self):
        """开始拖拽操作"""
        mimeData = QMimeData()
        data_str = f"{self.item['title']}|preview_item"
        mimeData.setData("application/x-etoword-item", QByteArray(data_str.encode()))
        
        drag = QDrag(self)
        drag.setMimeData(mimeData)
        drag.exec_(Qt.DropAction.MoveAction)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-etoword-item"):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)
    
    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-etoword-item"):
            data = event.mimeData().data("application/x-etoword-item").data().decode()
            title, mode = data.split("|")
            
            # 如果是从左侧列表拖来的，添加新项目
            if mode in ["列模式", "行模式"]:
                parent = self.parent()
                if parent and hasattr(parent, 'add_item_to_template_at_position'):
                    parent.add_item_to_template_at_position(title, mode, self.index + 1)
            
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

class CompositePreviewItemWidget(QWidget):
    """组合预览项小部件 - 显示多个字段项，支持拖拽添加字段项"""
    class ColumnPreviewWidget(QWidget):
        """表示一个列容器：显示列标题以及该列中横向排列的字段项，支持拖拽向该列添加字段"""
        def __init__(self, column_title, items, parent=None):
            super().__init__(parent)
            self.column_title = column_title
            self.items = items  # 列内的字段项列表
            self.setMaximumHeight(88)
            self.setMinimumHeight(88)
            self.setAcceptDrops(True)
            self.setup_ui()

        def setup_ui(self):
            layout = QVBoxLayout(self)
            layout.setContentsMargins(4, 4, 4, 4)
            layout.setSpacing(4)

            self.title_label = QLabel(f"{self.column_title}")
            self.title_label.setObjectName("columnTitle")
            layout.addWidget(self.title_label)

            # 容纳列内字段的横向容器
            self.items_container = QWidget()
            self.items_container.setObjectName("columnItemsContainer")
            self.items_layout = QHBoxLayout(self.items_container)
            self.items_layout.setContentsMargins(0, 0, 0, 0)
            self.items_layout.setSpacing(6)
            layout.addWidget(self.items_container)

            # 用 objectName 标识列容器以便 QSS 控制样式
            self.setObjectName("columnWidget")

            self.refresh_items()

        def refresh_items(self):
            # 清除旧项
            while self.items_layout.count():
                it = self.items_layout.takeAt(0)
                if it and it.widget():
                    it.widget().setParent(None)

            # 添加每个字段为小标签（可删除、可拖拽的 PreviewItemWidget）
            for i, item in enumerate(self.items):
                w = PreviewItemWidget(i, item, self.items_container)
                # 连接删除到父控件的接口（父对象是 ExcelToWordView）
                w.item_deleted.connect(self.handle_item_deleted)
                self.items_layout.addWidget(w)

        def handle_item_deleted(self, index):
            # 删除列内项并请求父刷新
            if 0 <= index < len(self.items):
                self.items.pop(index)
                self.refresh_items()
                parent = self.parent()
                # 向上寻找 ExcelToWordView 并让其刷新整体预览
                while parent and not hasattr(parent, 'refresh_preview_area'):
                    parent = parent.parent()
                # 如果当前列已无项，则从父的 preview_columns 中移除该列
                if not self.items:
                    container = parent
                    while container and not hasattr(container, 'preview_columns'):
                        container = container.parent()
                    if container and self.column_title in container.preview_columns:
                        try:
                            del container.preview_columns[self.column_title]
                        except KeyError:
                            pass
                if parent:
                    parent.refresh_preview_area()

        def dragEnterEvent(self, event):
            if event.mimeData().hasFormat("application/x-etoword-item"):
                event.acceptProposedAction()
            else:
                super().dragEnterEvent(event)

        def dropEvent(self, event):
            if event.mimeData().hasFormat("application/x-etoword-item"):
                data = event.mimeData().data("application/x-etoword-item").data().decode()
                title, mode = data.split("|")
                # 调用父控件的方法把字段加入到该列
                parent = self.parent()
                while parent and not hasattr(parent, 'add_item_to_column'):
                    parent = parent.parent()
                if parent:
                    parent.add_item_to_column(self.column_title, title, mode)
                event.acceptProposedAction()
            else:
                super().dropEvent(event)

    """复合预览项小部件 - 支持在同一行显示多个字段"""
    def __init__(self, index, items, parent=None):
        super().__init__(parent)
        self.index = index
        self.items = items  # 包含多个item的列表
        self.setAcceptDrops(True)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(5)
        
        # 显示组合内容
        self.content_label = QLabel()
        self.update_display_text()
        self.content_label.setWordWrap(True)
        self.content_label.setObjectName("compositeContentLabel")
        layout.addWidget(self.content_label)
        
        # 样式选择
        self.style_combo = QComboBox()
        self.style_combo.addItems(["默认", "二级标题", "无序列表", "有序列表"])
        # 使用第一个项目的样式作为整体样式
        if self.items:
            self.style_combo.setCurrentText(self.items[0]["style"])
        self.style_combo.currentTextChanged.connect(self.on_style_changed)
        self.style_combo.setFixedWidth(100)
        layout.addWidget(self.style_combo)
        
        # 添加字段按钮
        # self.add_field_btn = QPushButton("+")
        # self.add_field_btn.setFixedSize(25, 25)
        # self.add_field_btn.clicked.connect(self.add_field_to_composite)
        # layout.addWidget(self.add_field_btn)
        
        # 删除按钮
        self.delete_btn = QPushButton("✕")
        self.delete_btn.setFixedSize(25, 25)
        self.delete_btn.clicked.connect(self.delete_item)
        layout.addWidget(self.delete_btn)
        
        # 拖拽支持
        self.setMouseTracking(True)
    
    def update_display_text(self):
        """更新显示文本"""
        if not self.items:
            self.content_label.setText("空组合项")
            return
            
        # 组合显示所有字段的值
        display_parts = []
        for i, item in enumerate(self.items):
            value = item.get("value", "")
            if value:
                display_parts.append(f"{value}")
            else:
                display_parts.append("(空)")
        
        display_text = " ".join(display_parts)
        self.content_label.setText(display_text)
    
    def on_style_changed(self, style):
        # 更新所有子项目样式
        for item in self.items:
            item["style"] = style
        self.update_display_text()
    
    def add_field_to_composite(self):
        """向组合项添加新字段"""
        # 这里可以通过弹窗或其他方式让用户选择要添加的字段
        # 暂时留空，后续实现具体的添加逻辑
        pass
    
    def delete_item(self):
        parent = self.parent()
        if parent and hasattr(parent, 'remove_composite_preview_item'):
            parent.remove_composite_preview_item(self.index)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_drag()
        try:
            super().mousePressEvent(event)
        except RuntimeError:
            # 忽略在拖拽期间C++对象被删除导致的错误
            pass
    
    def start_drag(self):
        """开始拖拽操作"""
        mimeData = QMimeData()
        # 将组合项标识为特殊类型
        titles = "|".join([item["title"] for item in self.items])
        data_str = f"{titles}|composite_item"
        mimeData.setData("application/x-etoword-item", QByteArray(data_str.encode()))
        
        drag = QDrag(self)
        drag.setMimeData(mimeData)
        drag.exec_(Qt.DropAction.MoveAction)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-etoword-item"):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)
    
    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-etoword-item"):
            data = event.mimeData().data("application/x-etoword-item").data().decode()
            title, mode = data.split("|", 1)
            
            # 如果是普通字段，添加到组合中
            if mode in ["列模式", "行模式"]:
                self.add_field_to_existing(title, mode)
            # 如果是另一个组合项，合并
            elif mode == "composite_item":
                self.merge_with_composite(title)
            
            event.acceptProposedAction()
        else:
            super().dropEvent(event)
    
    def add_field_to_existing(self, title, mode):
        """向现有组合添加字段"""
        parent = self.parent()
        if parent and hasattr(parent, 'excel_data'):
            excel_data = parent.excel_data
            if excel_data is not None:
                # 获取字段值
                if mode == "列模式" and title in excel_data.columns:
                    value = str(excel_data.iloc[0][title]) if len(excel_data) > 0 else ""
                elif mode == "行模式":
                    try:
                        if title.startswith("Row "):
                            row_index = int(title.split()[1])
                        else:
                            row_index = int(title)
                        if 0 <= row_index < len(excel_data):
                            value = str(excel_data.iloc[row_index].tolist())
                        else:
                            value = ""
                    except (ValueError, IndexError):
                        value = ""
                else:
                    value = ""
                
                # 添加到组合
                new_item = {"title": title, "value": value, "style": "默认"}
                self.items.append(new_item)
                self.update_display_text()
    
    def merge_with_composite(self, titles_string):
        """与其他组合项合并"""
        # 解析要合并的标题
        titles_to_merge = titles_string.split("|")
        
        parent = self.parent()
        if parent and hasattr(parent, 'excel_data'):
            excel_data = parent.excel_data
            if excel_data is not None:
                # 为每个标题创建项目并添加到当前组合
                for title in titles_to_merge:
                    if title in excel_data.columns:
                        value = str(excel_data.iloc[0][title]) if len(excel_data) > 0 else ""
                        new_item = {"title": title, "value": value, "style": "默认"}
                        self.items.append(new_item)
                
                self.update_display_text()

class ExcelToWordView(QWidget):
    def __init__(self):
        super().__init__()
        self.excel_data: Optional[pd.DataFrame] = None
        self.preview_items = []  # 单个字段的预览项
        self.preview_columns = OrderedDict()  # 列模式：每列包含多个横向字段
        self.composite_preview_items = []  # 复合字段的预览项
        self.setAcceptDrops(True)  # 启用拖拽功能
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)  # 减少外边距
        layout.setSpacing(5)  # 减少元素间距
        
        # 初始状态：居中QLabel提示
        self.initial_label = QLabel("拖入Excel文件...")
        self.initial_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.initial_label)
        
        # 主要功能区域（初始隐藏）
        self.main_widget = QWidget()
        self.main_layout = QHBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(5)
        
        # 左侧区域
        left_widget = QWidget()
        left_widget.setFixedWidth(120)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 5, 0)
        left_layout.setSpacing(5)
        
        # 恢复模式下拉（行/列），以便用户选择使用行索引还是列名
        mode_row = QWidget()
        mode_row_layout = QHBoxLayout(mode_row)
        mode_row_layout.setContentsMargins(0, 0, 0, 0)
        mode_row_layout.setSpacing(4)
        mode_row_layout.addWidget(QLabel("模式:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["列模式", "行模式"])
        self.mode_combo.setCurrentText("列模式")
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        mode_row_layout.addWidget(self.mode_combo)
        left_layout.addWidget(mode_row)

        self.title_list = DraggableListWidget()
        self.title_list.setParent(self)
        left_layout.addWidget(self.title_list)
        
        # 右侧区域
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 0, 5, 0)
        right_layout.setSpacing(5)
        
        self.primary_title = QLineEdit()
        self.primary_title.setPlaceholderText("一级标题")
        right_layout.addWidget(self.primary_title)
        
        # 布局方向控件已移除（用户要求删除）
        
        # 整合的预览和拖拽区域
        self.preview_area = QScrollArea()
        self.preview_widget = QWidget()
        self.preview_widget.setObjectName("previewWidget")
        self.preview_layout = QVBoxLayout(self.preview_widget)  # 默认纵向
        self.preview_layout.setContentsMargins(5, 5, 5, 5)
        self.preview_layout.setSpacing(3)
        self.preview_area.setWidget(self.preview_widget)
        self.preview_area.setWidgetResizable(True)
        self.preview_area.setAcceptDrops(True)
        self.preview_area.dragEnterEvent = self.preview_drag_enter
        self.preview_area.dropEvent = self.preview_drop_event
        right_layout.addWidget(self.preview_area)
        
        # 在预览区下方添加空白拖拽区以延伸底部 20px
        self.bottom_drop_zone = DropAreaWidget()
        self.bottom_drop_zone.setFixedHeight(20)
        # 连接到底部放下的处理器
        self.bottom_drop_zone.item_dropped.connect(self.handle_bottom_drop)
        # 设置透明背景以不影响视觉（通过QSS保持最小冲突）
        right_layout.addWidget(self.bottom_drop_zone)
        
        self.generate_btn = QPushButton("生成Word")
        self.generate_btn.clicked.connect(self.generate_word)
        right_layout.addWidget(self.generate_btn)
        
        # 分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([200, 400])  # 调整默认比例
        self.main_layout.addWidget(splitter)
        
        layout.addWidget(self.main_widget)
        self.main_widget.hide()
        
        self.setLayout(layout)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            # 检查是否为Excel文件
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if file_path.endswith(('.xlsx', '.xls')):
                    event.acceptProposedAction()
                else:
                    event.ignore()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.endswith(('.xlsx', '.xls')):
                self.load_excel(file_path)

    def load_excel(self, file_path):
        try:
            self.excel_data = pd.read_excel(file_path)
            self.initial_label.hide()
            self.main_widget.show()
            self.update_title_list()
            self.update_preview()
        except Exception as e:
            print(f"Error loading Excel file: {e}")

    def update_title_list(self):
        self.title_list.clear()
        if self.excel_data is not None:
            # 根据当前模式显示可拖拽的项（列名 或 行索引）
            mode = "列模式"
            if hasattr(self, 'mode_combo') and self.mode_combo is not None:
                mode = self.mode_combo.currentText()

            if mode == "列模式":
                columns = self.excel_data.columns.tolist()
                if not columns:
                    QMessageBox.warning(self, "警告", "当前Excel文件没有列标题！")
                    return
                self.title_list.addItems(columns)
            else:
                # 行模式：显示 Row 0, Row 1, ... 方便用户把整行拖入模板
                rows = [f"Row {i}" for i in range(len(self.excel_data))]
                if not rows:
                    QMessageBox.warning(self, "警告", "当前Excel没有数据行！")
                    return
                self.title_list.addItems(rows)
        else:
            QMessageBox.warning(self, "警告", "请先加载Excel文件！")

    def update_preview(self):
        # 清空预览区域
        self.preview_items = []
        self.preview_columns = OrderedDict()
        self.refresh_preview_area()
        
        if self.excel_data is None:
            return
            
        mode = "列模式"
        if hasattr(self, 'mode_combo') and self.mode_combo is not None:
            mode = self.mode_combo.currentText()
        selected_titles = [self.title_list.item(i).text() for i in range(self.title_list.count())]
        
        for title in selected_titles:
            if mode == "列模式":
                if title in self.excel_data.columns and len(self.excel_data) > 0:
                    value = str(self.excel_data.iloc[0][title])
                else:
                    value = "无数据"
                item = {"title": title, "value": value, "style": "默认"}
                # 每个选中列作为一个独立列，首项为该列首值
                self.preview_columns[title] = [item]
            else:  # 行模式
                try:
                    if title.startswith("Row "):
                        row_index = int(title.split()[1])
                    else:
                        row_index = int(title)
                    
                    if 0 <= row_index < len(self.excel_data):
                        value = str(self.excel_data.iloc[row_index].tolist())
                    else:
                        value = f"行索引 {row_index} 超出范围"
                except (ValueError, IndexError):
                    value = f"无法解析行标题: {title}"
                item = {"title": title, "value": value, "style": "默认"}
                self.preview_items.append(item)
        
        # 刷新显示
        self.refresh_preview_area()

    def update_item_style(self, index, style):
        self.preview_items[index]["style"] = style

    def on_mode_changed(self, mode):
        # 切换模式时需更新左侧可拖拽项以及预览
        self.update_title_list()
        self.refresh_preview_area()

    def add_item_to_template(self, title, mode):
        """将拖拽的项目添加到模板"""
        if self.excel_data is None:
            QMessageBox.warning(self, "警告", "请先加载Excel文件！")
            return

        # 列模式 -> 将字段放入列容器（如果在预览区直接放置则作为新列）
        if mode == "列模式":
            # 将该字段作为新的一列并在该列内添加此字段为首项
            self.add_column_with_item(title, mode)
            return

        # 行模式（沿用原有行为：追加到预览项列表）
        try:
            if title.startswith("Row "):
                row_index = int(title.split()[1])
            else:
                row_index = int(title)

            if 0 <= row_index < len(self.excel_data):
                value = str(self.excel_data.iloc[row_index].tolist())
            else:
                QMessageBox.warning(self, "警告", f"行索引 {row_index} 超出范围！")
                return
        except (ValueError, IndexError):
            QMessageBox.warning(self, "警告", f"无法解析行标题: {title}")
            return

        # 添加到预览项目
        item = {"title": title, "value": value, "style": "默认"}
        self.preview_items.append(item)
        self.add_preview_item_widget(len(self.preview_items)-1, item)

    def add_preview_item_widget(self, index, item):
        """添加单个预览项小部件"""
        preview_item = PreviewItemWidget(index, item, self.preview_widget)
        # 连接删除信号
        preview_item.item_deleted.connect(self.handle_item_deletion)
        self.preview_layout.addWidget(preview_item)
        preview_item.index = index  # 保存索引用于删除

    def add_column_with_item(self, title, mode):
        """在列模式下，新建一列并把字段作为该列的第一个元素"""
        if self.excel_data is None:
            QMessageBox.warning(self, "警告", "请先加载Excel文件！")
            return

        # 获取字段示例值
        if title in self.excel_data.columns:
            try:
                value = str(self.excel_data.iloc[0][title]) if len(self.excel_data) > 0 else "无数据"
            except Exception:
                value = "示例值"
        else:
            value = "示例值"

        item = {"title": title, "value": value, "style": "默认"}
        # 如果列不存在，则创建并加入项目
        if title not in self.preview_columns:
            self.preview_columns[title] = []
        self.preview_columns[title].append(item)
        self.refresh_preview_area()

    def add_item_to_column(self, column_title, title, mode):
        """向指定列添加字段（列内横向排列）"""
        if self.excel_data is None:
            QMessageBox.warning(self, "警告", "请先加载Excel文件！")
            return

        if title in self.excel_data.columns:
            try:
                value = str(self.excel_data.iloc[0][title]) if len(self.excel_data) > 0 else "无数据"
            except Exception:
                value = "示例值"
        else:
            value = "示例值"

        item = {"title": title, "value": value, "style": "默认"}
        if column_title not in self.preview_columns:
            self.preview_columns[column_title] = []
        self.preview_columns[column_title].append(item)
        self.refresh_preview_area()

    def handle_bottom_drop(self, title, mode):
        """处理底部 20px 拖拽区放下事件：列模式新建列，行模式作为普通项加入末尾"""
        if mode == "列模式":
            self.add_column_with_item(title, mode)
        else:
            self.add_item_to_template(title, mode)
    
    def handle_item_deletion(self, index):
        """处理项目删除请求"""
        if 0 <= index < len(self.preview_items):
            # 从数据列表中删除
            self.preview_items.pop(index)
            # 重新创建所有预览项以更新索引
            self.refresh_preview_area()
    
    def add_item_to_template_at_position(self, title, mode, position):
        """在指定位置添加项目到模板"""
        if self.excel_data is None:
            QMessageBox.warning(self, "警告", "请先加载Excel文件！")
            return
            
        # 获取数据值
        if mode == "列模式":
            if title in self.excel_data.columns:
                value = str(self.excel_data.iloc[0][title]) if len(self.excel_data) > 0 else ""
            else:
                QMessageBox.warning(self, "警告", f"列 '{title}' 不存在！")
                return
        else:  # 行模式
            try:
                if title.startswith("Row "):
                    row_index = int(title.split()[1])
                else:
                    row_index = int(title)
                
                if 0 <= row_index < len(self.excel_data):
                    value = str(self.excel_data.iloc[row_index].tolist())
                else:
                    QMessageBox.warning(self, "警告", f"行索引 {row_index} 超出范围！")
                    return
            except (ValueError, IndexError):
                QMessageBox.warning(self, "警告", f"无法解析行标题: {title}")
                return
        
        # 在指定位置插入项目
        item = {"title": title, "value": value, "style": "默认"}
        self.preview_items.insert(position, item)
        
        # 重新创建所有预览项以更新索引
        self.refresh_preview_area()
    
    def remove_preview_item(self, index):
        """删除预览项"""
        if 0 <= index < len(self.preview_items):
            self.preview_items.pop(index)
            # 重新创建所有预览项
            self.refresh_preview_area()
    
    def remove_preview_item_by_widget(self, widget):
        """通过widget实例删除预览项"""
        # 找到widget在布局中的索引
        for i in range(self.preview_layout.count()):
            item = self.preview_layout.itemAt(i)
            if item and item.widget() == widget:
                # 从数据列表中删除
                if 0 <= i < len(self.preview_items):
                    self.preview_items.pop(i)
                    # 重新创建所有预览项以更新索引
                    self.refresh_preview_area()
                break

    def refresh_preview_area(self):
        """刷新预览区域"""
        # 清空预览区域 - 修复布局清理逻辑
        while self.preview_layout.count():
            item = self.preview_layout.takeAt(0)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                # 也要清理布局本身
                layout = item.layout()
                if layout:
                    # 递归清理嵌套布局
                    while layout.count():
                        child_item = layout.takeAt(0)
                        if child_item and child_item.widget():
                            child_item.widget().setParent(None)
        
        # 根据模式重新添加所有项目
        mode = "列模式"
        if hasattr(self, 'mode_combo') and self.mode_combo is not None:
            mode = self.mode_combo.currentText()
        if mode == "列模式":
            # 每一列显示为 ColumnPreviewWidget（列标题 + 横向字段项）
            for col_title, items in self.preview_columns.items():
                col_widget = CompositePreviewItemWidget.ColumnPreviewWidget(col_title, items, self.preview_widget)
                self.preview_layout.addWidget(col_widget)
        else:
            for i, item in enumerate(self.preview_items):
                self.add_preview_item_widget(i, item)
    
    def refresh_composite_preview_area(self):
        """刷新复合预览区域"""
        # 这里可以根据需要实现复合预览区域的刷新逻辑
        pass
    
    def add_composite_item(self, items):
        """添加复合预览项"""
        composite_item = CompositePreviewItemWidget(len(self.composite_preview_items), items, self.preview_widget)
        self.composite_preview_items.append(composite_item)
        self.preview_layout.addWidget(composite_item)

    def generate_word(self):
        """生成Word文档 - 批量处理所有数据行"""
        if self.excel_data is None:
            QMessageBox.warning(self, "警告", "请先加载Excel文件！")
            return
            
        if not self.preview_columns:
            QMessageBox.warning(self, "警告", "请先添加模板项目！")
            return
            
        try:
            doc = Document()
            
            # 添加一级标题
            if self.primary_title.text().strip():
                doc.add_heading(self.primary_title.text().strip(), level=1)
            
            # 根据当前模式处理所有数据（列/行）
            mode = "列模式"
            if hasattr(self, 'mode_combo') and self.mode_combo is not None:
                mode = self.mode_combo.currentText()

            if mode == "列模式":
                self._generate_from_columns(doc)
            else:  # 行模式
                self._generate_from_rows(doc)
            
            # 保存文档
            output_path = "output.docx"
            doc.save(output_path)
            QMessageBox.information(self, "成功", f"Word文档已生成：{output_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成Word文档失败：{str(e)}")

    

    def _generate_from_columns(self, doc):
        """从列模式生成Word文档"""
        if self.excel_data is None or len(self.excel_data) == 0:
            return
        # 如果没有列配置，直接返回
        if not self.preview_columns:
            return

        # 遍历每一行数据
        for row_index in range(len(self.excel_data)):
            # 为每行添加分隔线（除了第一行）
            if row_index > 0:
                doc.add_paragraph("")
                doc.add_paragraph("-" * 30)
                doc.add_paragraph("")

            # 按列顺序输出，每个列可能包含多个字段（横向组合）
            for col_title, items in self.preview_columns.items():
                # 构建当前行每个字段的实际值副本
                items_with_values = []
                for item in items:
                    field = item.get("title")
                    if self.excel_data is None or field not in self.excel_data.columns:
                        value = "无数据"
                    else:
                        value = str(self.excel_data.iloc[row_index][field])
                        if not value or value.lower() == "nan":
                            value = "无数据"
                    items_with_values.append({"title": field, "value": value, "style": item.get("style", "默认")})

                # 使用复合格式将列内所有字段横向合并显示
                # 采用第一个子项的样式作为整列样式
                style = items_with_values[0].get("style", "默认") if items_with_values else "默认"
                self._add_composite_formatted_content(doc, items_with_values, style)

    def _generate_from_rows(self, doc):
        """从行模式生成Word文档"""
        if self.excel_data is None:
            return
            
        # 获取选中的行索引
        selected_rows = []
        for item in self.preview_items:
            try:
                if item["title"].startswith("Row "):
                    row_index = int(item["title"].split()[1])
                else:
                    row_index = int(item["title"])
                if 0 <= row_index < len(self.excel_data):
                    selected_rows.append((row_index, item))
            except (ValueError, IndexError):
                continue
        
        if not selected_rows:
            return
            
        # 遍历选中的每一行
        for i, (row_index, item) in enumerate(selected_rows):
            # 为每行添加分隔线（除了第一行）
            if i > 0:
                doc.add_paragraph("")
                doc.add_paragraph("-" * 30)
                doc.add_paragraph("")
            
            # 获取行数据
            row_data = self.excel_data.iloc[row_index]
            row_values = [str(val) if not pd.isna(val) else "无数据" for val in row_data]
            
            # 为当前行添加数据
            for j, (column_name, value) in enumerate(zip(self.excel_data.columns, row_values)):
                # 应用样式（使用模板中对应的样式）
                style = item["style"] if j < len(self.preview_items) else "默认"
                self._add_formatted_content(doc, column_name, value, style)

    def _add_formatted_content(self, doc, title, value, style):
        """添加格式化的内容到文档"""
        # 只显示值，不显示标题前缀
        display_text = value
        
        if style == "二级标题":
            doc.add_heading(display_text, level=2)
        elif style == "无序列表":
            p = doc.add_paragraph(style='List Bullet')
            p.add_run(display_text)
        elif style == "有序列表":
            p = doc.add_paragraph(style='List Number')
            p.add_run(display_text)
        else:  # 默认样式
            doc.add_paragraph(display_text)

    def _add_composite_formatted_content(self, doc, items, style):
        """添加复合格式化内容到文档"""
        # 组合显示所有字段
        display_parts = []
        for i, item in enumerate(items):
            value = item.get("value", "")
            if value:
                display_parts.append(f"{value}")
            else:
                display_parts.append("(空)")
        
        display_text = " ".join(display_parts)
        
        if style == "二级标题":
            doc.add_heading(display_text, level=2)
        elif style == "无序列表":
            p = doc.add_paragraph(style='List Bullet')
            p.add_run(display_text)
        elif style == "有序列表":
            p = doc.add_paragraph(style='List Number')
            p.add_run(display_text)
        else:  # 默认样式
            doc.add_paragraph(display_text)

    

    def preview_drag_enter(self, event):
        """预览区域拖拽进入事件"""
        if event.mimeData().hasFormat("application/x-etoword-item"):
            event.acceptProposedAction()

    def preview_drop_event(self, event):
        """预览区域拖拽放下事件"""
        if event.mimeData().hasFormat("application/x-etoword-item"):
            data = event.mimeData().data("application/x-etoword-item").data().decode()
            title, mode = data.split("|")
            
            # 如果是来自左侧的项目，添加到末尾
            if mode in ["列模式", "行模式"]:
                self.add_item_to_template(title, mode)
            
            event.acceptProposedAction()
    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    view = ExcelToWordView()
    view.show()
    sys.exit(app.exec())