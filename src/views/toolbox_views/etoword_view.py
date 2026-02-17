"""
Excel转Word处理器 - 负责处理Excel数据和生成Word文档
"""

import pandas as pd
from docx import Document
from typing import List, Dict, Optional

class ExcelToWordHandler:
    """Excel转Word处理引擎"""
    
    def __init__(self):
        self.df: Optional[pd.DataFrame] = None
        
    def load_excel(self, file_path: str) -> bool:
        """
        加载Excel文件
        
        Args:
            file_path: Excel文件路径
            
        Returns:
            bool: 是否成功加载
        """
        try:
            self.df = pd.read_excel(file_path)
            return True
        except Exception as e:
            print(f"Error loading Excel file: {e}")
            return False
            
    def get_columns(self) -> List[str]:
        """
        获取所有列名
        
        Returns:
            列名列表
        """
        if self.df is not None:
            return self.df.columns.tolist()
        return []
        
    def get_rows_count(self) -> int:
        """
        获取行数
        
        Returns:
            行数
        """
        if self.df is not None:
            return len(self.df)
        return 0
        
    def get_column_preview_data(self, column_name: str, row_index: int = 0) -> str:
        """
        获取列的预览数据（指定行）
        
        Args:
            column_name: 列名
            row_index: 行索引
            
        Returns:
            预览数据字符串
        """
        if self.df is not None and column_name in self.df.columns:
            if 0 <= row_index < len(self.df):
                value = self.df.iloc[row_index][column_name]
                return str(value) if not pd.isna(value) else ""
        return ""
        
    def get_row_preview_data(self, row_index: int) -> List[str]:
        """
        获取行的预览数据
        
        Args:
            row_index: 行索引
            
        Returns:
            行数据列表（字符串格式）
        """
        if self.df is not None and 0 <= row_index < len(self.df):
            row = self.df.iloc[row_index]
            return [str(value) if not pd.isna(value) else "" for value in row.tolist()]
        return []
        
    def generate_word_document(self, 
                            primary_title: str, 
                            preview_items: List[Dict[str, str]], 
                            footer_content: str,
                            output_path: str) -> bool:
        """
        生成Word文档
        
        Args:
            primary_title: 一级标题
            preview_items: 预览项列表
            footer_content: 页脚内容
            output_path: 输出路径
            
        Returns:
            bool: 是否成功生成
        """
        try:
            doc = Document()
            
            # 添加一级标题
            if primary_title.strip():
                doc.add_heading(primary_title, level=1)
                
            # 添加预览内容
            for item in preview_items:
                style = item.get("style", "默认")
                value = item.get("value", "")
                
                if not value.strip():
                    continue
                    
                if style == "二级标题":
                    doc.add_heading(value, level=2)
                elif style == "无序列表":
                    p = doc.add_paragraph(style='List Bullet')
                    p.add_run(value)
                elif style == "有序列表":
                    p = doc.add_paragraph(style='List Number')
                    p.add_run(value)
                else:  # 默认样式
                    doc.add_paragraph(value)
                    
            # 添加末尾内容
            if footer_content.strip():
                doc.add_paragraph("----------", style="Intense Quote")
                doc.add_paragraph(footer_content)
                
            # 保存文档
            doc.save(output_path)
            return True
            
        except Exception as e:
            print(f"Error generating Word document: {e}")
            return False
import sys
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QSplitter, QComboBox, QListWidget, QLineEdit,
                               QScrollArea, QTextEdit, QPushButton, QApplication,
                               QMessageBox)
from PySide6.QtCore import Qt, QMimeData, QByteArray, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QDragMoveEvent, QDrag
import pandas as pd
from docx import Document
from typing import Optional

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
            # 通过parent访问mode_combo
            parent_widget = self.parent()
            if parent_widget:
                combo_box = parent_widget.findChild(QComboBox)
                if combo_box:
                    mode = combo_box.currentText()
                else:
                    mode = "列模式"  # 默认值
            else:
                mode = "列模式"  # 默认值
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

class ExcelToWordView(QWidget):
    def __init__(self):
        super().__init__()
        self.excel_data: Optional[pd.DataFrame] = None
        self.preview_items = []
        self.setAcceptDrops(True)  # 启用拖拽功能
        self.init_ui()
        # 移除自定义样式，使用全局主题

    def apply_styles(self):
        """移除自定义样式，使用全局主题管理"""
        pass  # 不再应用本地样式表

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)  # 减少外边距
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
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_layout.setSpacing(5)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["列模式", "行模式"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        left_layout.addWidget(self.mode_combo)
        
        self.title_list = DraggableListWidget()
        self.title_list.setParent(self)  # 设置父级以便访问mode_combo
        left_layout.addWidget(self.title_list)
        
        # 右侧区域
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 5, 5, 5)
        right_layout.setSpacing(5)
        
        self.primary_title = QLineEdit()
        self.primary_title.setPlaceholderText("一级标题")
        right_layout.addWidget(self.primary_title)
        
        # 创建拖拽接收区域
        self.drop_area = DropAreaWidget()
        self.drop_area.item_dropped.connect(self.add_item_to_template)
        self.drop_area.setFixedHeight(80)  # 设置固定高度
        right_layout.addWidget(self.drop_area)
        
        self.preview_area = QScrollArea()
        self.preview_widget = QWidget()
        self.preview_layout = QVBoxLayout(self.preview_widget)
        self.preview_layout.setContentsMargins(5, 5, 5, 5)
        self.preview_layout.setSpacing(3)
        self.preview_area.setWidget(self.preview_widget)
        self.preview_area.setWidgetResizable(True)
        right_layout.addWidget(self.preview_area)
        
        self.footer = QTextEdit()
        self.footer.setPlaceholderText("末尾内容")
        self.footer.setMaximumHeight(100)  # 限制最大高度
        right_layout.addWidget(self.footer)
        
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
        if self.excel_data is not None:  # 添加类型检查
            mode = self.mode_combo.currentText()
            if mode == "列模式":
                columns = self.excel_data.columns.tolist()
                if not columns:
                    QMessageBox.warning(self, "警告", "当前Excel文件没有列标题！")
                    return
                self.title_list.addItems(columns)
            else:  # 行模式
                rows_count = len(self.excel_data)
                if rows_count == 0:
                    QMessageBox.warning(self, "警告", "当前Excel文件没有数据行！")
                    return
                items = [f"Row {i}" for i in range(rows_count)]
                self.title_list.addItems(items)
        else:
            QMessageBox.warning(self, "警告", "请先加载Excel文件！")

    def update_preview(self):
        # 清空预览区域
        self.preview_items = []
        self.refresh_preview_area()
        
        if self.excel_data is None:
            return
            
        mode = self.mode_combo.currentText()
        selected_titles = [self.title_list.item(i).text() for i in range(self.title_list.count())]
        
        for title in selected_titles:
            if mode == "列模式":
                if title in self.excel_data.columns and len(self.excel_data) > 0:
                    value = str(self.excel_data.iloc[0][title])
                else:
                    value = "无数据"
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
        """模式切换时更新标题列表"""
        self.update_title_list()
        self.update_preview()

    def add_item_to_template(self, title, mode):
        """将拖拽的项目添加到模板"""
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
        
        # 添加到预览项目
        item = {"title": title, "value": value, "style": "默认"}
        self.preview_items.append(item)
        self.add_preview_item_widget(len(self.preview_items)-1, item)

    def add_preview_item_widget(self, index, item):
        """添加单个预览项小部件"""
        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(2, 2, 2, 2)
        item_layout.setSpacing(5)
        
        label = QLabel(f"{item['title']}: {item['value']}")
        label.setWordWrap(True)
        item_layout.addWidget(label)
        
        style_combo = QComboBox()
        style_combo.addItems(["默认", "二级标题", "无序列表", "有序列表"])
        style_combo.setCurrentText(item['style'])
        style_combo.currentTextChanged.connect(
            lambda text, idx=index: self.update_item_style(idx, text)
        )
        style_combo.setFixedWidth(100)
        item_layout.addWidget(style_combo)
        
        # 添加删除按钮
        delete_btn = QPushButton("×")
        delete_btn.setFixedSize(25, 25)
        delete_btn.clicked.connect(
            lambda _, idx=index: self.remove_preview_item(idx)
        )
        item_layout.addWidget(delete_btn)
        
        self.preview_layout.addWidget(item_widget)
        item_widget.index = index  # 保存索引用于删除
    
    def remove_preview_item(self, index):
        """删除预览项"""
        if 0 <= index < len(self.preview_items):
            self.preview_items.pop(index)
            # 重新创建所有预览项
            self.refresh_preview_area()
    
    def refresh_preview_area(self):
        """刷新预览区域"""
        # 清空预览区域
        for i in reversed(range(self.preview_layout.count())): 
            widget = self.preview_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # 重新添加所有项目
        for i, item in enumerate(self.preview_items):
            self.add_preview_item_widget(i, item)

    def generate_word(self):
        """生成Word文档 - 批量处理所有数据行"""
        if self.excel_data is None:
            QMessageBox.warning(self, "警告", "请先加载Excel文件！")
            return
            
        if not self.preview_items:
            QMessageBox.warning(self, "警告", "请先添加模板项目！")
            return
            
        try:
            doc = Document()
            
            # 添加一级标题
            if self.primary_title.text().strip():
                doc.add_heading(self.primary_title.text().strip(), level=1)
            
            # 获取当前模式
            mode = self.mode_combo.currentText()
            
            # 根据模式处理所有数据
            if mode == "列模式":
                self._generate_from_columns(doc)
            else:  # 行模式
                self._generate_from_rows(doc)
            
            # 添加末尾内容
            if self.footer.toPlainText().strip():
                doc.add_paragraph("----------", style="Intense Quote")
                doc.add_paragraph(self.footer.toPlainText().strip())
            
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
            
        # 获取选中的列
        selected_columns = [item["title"] for item in self.preview_items 
                          if self.excel_data is not None and item["title"] in self.excel_data.columns]
        
        if not selected_columns:
            return
            
        # 遍历每一行数据
        for row_index in range(len(self.excel_data)):
            # 为每行添加分隔线（除了第一行）
            if row_index > 0:
                doc.add_paragraph("")
                doc.add_paragraph("-" * 30)
                doc.add_paragraph("")
            
            # 为当前行添加数据
            for item in self.preview_items:
                if self.excel_data is None or item["title"] not in self.excel_data.columns:
                    continue
                    
                # 获取当前行该列的值
                value = str(self.excel_data.iloc[row_index][item["title"]])
                if not value or value.lower() == "nan":
                    value = "无数据"
                
                # 应用样式
                self._add_formatted_content(doc, item["title"], value, item["style"])

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
        display_text = f"{title}: {value}"
        
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
if __name__ == "__main__":
    app = QApplication(sys.argv)
    view = ExcelToWordView()
    view.show()
    sys.exit(app.exec())