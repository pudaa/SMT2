import json
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QLineEdit,
    QScrollArea, QFrame, QSizePolicy, QTextEdit, QToolButton, QScrollBar
)
from PySide6.QtCore import Qt, QPoint, Signal, QThread, QObject
from PySide6.QtGui import QMouseEvent, QFontMetrics, QWheelEvent
from src.utils.todo_tag_extractor import TodoTagExtractor


class TagRefreshWorker(QObject):
    """异步刷新标签的worker"""
    finished = Signal(set)  # 完成信号，传递标签集合
    
    def __init__(self, todo_items):
        super().__init__()
        self.todo_items = todo_items
    
    def run(self):
        """在后台线程中执行标签提取"""
        all_tags = set()
        for item in self.todo_items:
            if hasattr(item, 'content_text') and item.content_text.strip():
                tags = TodoTagExtractor.extract_tags(item.content_text)
                all_tags.update(tags)
        self.finished.emit(all_tags)


class TodoItemWidget(QWidget): # 单个待办事项组件
    # 定义信号
    moveUpRequested = Signal(object)  # 请求向上移动
    moveDownRequested = Signal(object)  # 请求向下移动
    isDraggingOn = Signal(object)# 正在拖动信号
    isDraggingDown = Signal(object)# 停止拖动信号
    
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.content_text = text
        self.setFixedHeight(32)
        self.setStyleSheet("""
            QToolTip {
                color: #ccc;
                background-color: rgba(50, 50, 50, 100);
                border: none;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 12px;
                white-space: pre-wrap; 
            }  
            background-color: transparent;
            border: none;
        """)
        
        # 缓存字体度量，避免重复创建
        self._font_metrics = None
        self._cached_tooltip = None
        self._last_tooltip_text = None
        
        # 拖动相关属性
        self.drag_start_global_y = 0
        self.is_dragging = False
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(5)
        
        self.checkbox = QCheckBox()
        self.checkbox.setStyleSheet("""
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #888;
                border-radius: 3px;
                background-color: transparent;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #555;
                border-radius: 3px;
                background-color: #4a90e2;
            }
        """)
        
        self.text_field = QLineEdit(text)
        self.text_field.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: none;
                color: #ccc;
                font-size: 12px;
                padding: 4px;
            }
            QLineEdit:focus {
                border-bottom: 1px solid #4a90e2;
            }
        """)
        self.text_field.mouseDoubleClickEvent = self.handle_double_click
        self.handle_text_show()
        
        self.drag_label = QLabel("  ☰  ")
        self.drag_label.setStyleSheet("color: #888; font-size: 14px; font-weight: bold;")
        self.drag_label.setCursor(Qt.PointingHandCursor)
        
        layout.addWidget(self.checkbox)
        layout.addWidget(self.text_field)
        layout.addWidget(self.drag_label)
        
        self.auto_wrap_tip()
        
        self.text_field.editingFinished.connect(self.handle_return_pressed)
        self.text_field.textChanged.connect(self.on_text_changed)
        self.checkbox.clicked.connect(self.on_checkbox_clicked)
    
    def get_text(self):
        return self.text_field.text()
        
    def is_completed(self):
        return self.checkbox.isChecked()
    
    def auto_wrap_tip(self):
        text = self.content_text
        
        # 如果文本没变，使用缓存
        if self._last_tooltip_text == text and self._cached_tooltip is not None:
            self.setToolTip(self._cached_tooltip)
            return
            
        max_length = 25
        if len(text) > max_length:
            words = text.split()
            lines = []
            current_line = ""
            
            for word in words:
                if len(current_line + word) <= max_length:
                    current_line += word + " "
                else:
                    if current_line:
                        lines.append(current_line.strip())
                    current_line = word + " "
            
            if current_line:
                lines.append(current_line.strip())
                
            wrapped_text = '\n'.join(lines) if lines else text
            self._cached_tooltip = wrapped_text
        else:
            self._cached_tooltip = text
            
        self._last_tooltip_text = text
        self.setToolTip(self._cached_tooltip)
            
    def handle_text_show(self):
        """处理文本显示，带缓存优化"""
        text = self.content_text
        
        # 缓存字体度量对象
        if self._font_metrics is None:
            self._font_metrics = QFontMetrics(self.text_field.font())
            
        max_width = 130
        
        if self._font_metrics.horizontalAdvance(text) > max_width:
            elided_text = self._font_metrics.elidedText(text, Qt.ElideRight, max_width) # 缩略显示
            self.text_field.setText(elided_text)
        else:
            self.text_field.setText(text)

    def on_text_changed(self, event):
        if not self.text_field.isReadOnly():
            self.content_text = self.get_text()
            # 清除标签缓存，因为文本已改变
            self._cached_tags = None
        self.auto_wrap_tip()
        
    def handle_return_pressed(self):
        """处理回车键按下事件"""
        self.text_field.setReadOnly(True)
        self.content_text = self.get_text()
        self.handle_text_show()
        self.clearFocus()
        
    
    def handle_double_click(self, event):
        """处理文本字段的双击事件"""
        self.text_field.setReadOnly(False)
        self.text_field.setText(self.content_text)
        self.text_field.setFocus()
        self.text_field.selectAll()
        QLineEdit.mouseDoubleClickEvent(self.text_field, event)
        
    def on_checkbox_clicked(self):
        """复选框状态改变时的处理，优化样式更新"""
        if self.checkbox.isChecked():
            self.text_field.setStyleSheet("""
                QLineEdit {
                    background-color: transparent;
                    border: none;
                    color: #888;
                    font-size: 12px;
                    padding: 4px;
                    text-decoration: line-through;
                }
            """)
        else:
            self.text_field.setStyleSheet("""
                QLineEdit {
                    background-color: transparent;
                    border: none;
                    color: #ccc;
                    font-size: 12px;
                    padding: 4px;
                    text-decoration: none;
                }
            """)
        # 标记需要重新计算标签
        self._cached_tags = None
        
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            # 检查是否点击在拖动标签上
            if self.drag_label.underMouse():
                self.drag_start_global_y = event.globalPos().y()
                self.is_dragging = True
                self.isDraggingOn.emit(self)
                event.accept()
                return
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event: QMouseEvent):
        if not self.is_dragging:
            super().mouseMoveEvent(event)
            return
            
        if event.buttons() == Qt.LeftButton:
            # 计算移动距离
            delta_y = event.globalPos().y() - getattr(self, "drag_start_global_y", event.globalPos().y())
            if abs(delta_y) > 33: 
                if delta_y < 0:
                    self.moveUpRequested.emit(self)
                else:
                    self.moveDownRequested.emit(self)
                self.drag_start_global_y = event.globalPos().y()
                event.accept()
                return
                
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            if self.is_dragging:
                self.is_dragging = False
                self.isDraggingDown.emit(self)
                event.accept() 
                return
        super().mouseReleaseEvent(event)


class TagScrollArea(QScrollArea):
    """支持滚轮的横向滚动区域"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        
    def wheelEvent(self, event: QWheelEvent):
        # 支持鼠标滚轮横向滚动
        if event.angleDelta().y() != 0:
            # 将垂直滚轮转换为水平滚动
            delta = event.angleDelta().y()
            current_value = self.horizontalScrollBar().value()
            self.horizontalScrollBar().setValue(current_value - delta)
            event.accept()
        else:
            super().wheelEvent(event)


class TodoPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)
        self.todo_visible = False
        self.selected_tags = set()  # 存储选中的标签
        self.tag_refresh_in_progress = False  # 标签刷新进行中标志
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(0)
        
        # 标题
        title_label = QLabel("———— 待办事项 ————")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #ccc;
                background-color: rgba(50, 50, 50, 200);
                font-size: 15px;
                font-weight: bold;
                padding: 5px;
                border-top-left-radius: 20px;
                border-top-right-radius: 20px;
            }
        """)
        layout.addWidget(title_label)
        
        # 标签横向滚动区域
        self.tag_scroll_area = TagScrollArea()
        self.tag_scroll_area.setWidgetResizable(True)
        self.tag_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tag_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tag_scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: rgba(50, 50, 50, 200);
                padding-left: 5px;
                padding-right: 5px;
            }
            QScrollBar:horizontal {
                height: 0px;
                background-color: transparent;
            }
            QScrollBar::handle:horizontal {
                background-color: transparent;
                border-radius: 4px;
            }
        """)
        # 启用鼠标跟踪以支持拖拽
        self.tag_scroll_area.setMouseTracking(True)
        
        # 标签容器
        self.tag_container = QWidget()
        self.tag_container.setStyleSheet("background-color: transparent;")
        self.tag_layout = QHBoxLayout(self.tag_container)
        self.tag_layout.setContentsMargins(5, 0, 5, 0)
        self.tag_layout.setSpacing(5)
        self.tag_layout.addStretch()
        
        self.tag_scroll_area.setWidget(self.tag_container)
        layout.addWidget(self.tag_scroll_area)
        
        # 滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                padding-top: 0px;
                padding-right: 10px;
                padding-bottom: 10px;
                padding-left: 10px;
                background-color: rgba(50, 50, 50, 200);
                border-bottom-left-radius: 20px;
                border-bottom-right-radius: 20px;
            }
            QScrollBar:vertical {
                width: 5px;
                background-color: transparent;
            }
            QScrollBar::handle:vertical {
                background-color: #555;
                border-radius: 4px;
            }
        """)
        
        # 待办事项列表容器
        self.todo_container = QWidget()
        self.todo_container.setStyleSheet("background-color: transparent;")
        self.todo_layout = QVBoxLayout(self.todo_container)
        self.todo_layout.setContentsMargins(5, 5, 5, 5)
        self.todo_layout.setSpacing(2)
        self.todo_layout.addStretch()
        self.is_dragging = False
        
        self.scroll_area.setWidget(self.todo_container)
        layout.addWidget(self.scroll_area)
        
        self.mousePressEvent = self.handle_all_area_click
        self.scroll_area.mouseDoubleClickEvent = self.handle_scroll_area_double_click
        
        # 存储待办事项
        self.todo_items = []
        self.all_tags = set()  # 存储所有标签
        self.load_todos()
    
    def handle_all_area_click(self, event):
        """处理在空白处的点击事件"""
        self.save_todos()
        self.update_todo_list()
                
    def handle_scroll_area_double_click(self, event):
        """处理在滚动区域空白处的双击事件"""
        self.create_new_todo_item()
                
    def create_new_todo_item(self):
        """创建新的待办事项"""
        # 先清理现有的空项目
        self.update_todo_list()
        # 添加新项目
        new_item = self.add_todo_item("", is_new=True)
        new_item.text_field.textChanged.connect(self.on_text_changed)
        new_item.text_field.returnPressed.connect(lambda: self.on_return_pressed(new_item))
        # 当项目被标记为完成时，失去焦点后自动销毁
        new_item.checkbox.clicked.connect(lambda: self.on_checkbox_clicked(new_item))
        
    def add_todo_item(self, text="", is_new=False):
        todo_widget = TodoItemWidget(text)
        # 插入到倒数第二个位置（在Stretch之前）
        self.todo_layout.insertWidget(self.todo_layout.count() - 1, todo_widget)
        self.todo_items.append(todo_widget)
        
        if is_new:
            todo_widget.text_field.setReadOnly(False)
            todo_widget.text_field.setFocus()
            todo_widget.text_field.selectAll()
            
        # 连接拖动信号
        todo_widget.moveUpRequested.connect(self.move_item_up)
        todo_widget.moveDownRequested.connect(self.move_item_down)
        # 连接拖动信号，使用lambda函数修改self.is_dragging的值为True或False
        todo_widget.isDraggingOn.connect(lambda: setattr(self, 'is_dragging', True))
        todo_widget.isDraggingDown.connect(lambda: setattr(self, 'is_dragging', False))
        todo_widget.isDraggingOn.connect(lambda *args: setattr(self, 'is_dragging', True))
        todo_widget.isDraggingDown.connect(lambda *args: setattr(self, 'is_dragging', False))
            
        return todo_widget
        
    def move_item_up(self, item):
        """向上移动项目"""
        index = self.todo_layout.indexOf(item)
        if index > 0:
            self.todo_layout.removeWidget(item)
            self.todo_layout.insertWidget(index - 1, item)
            
    def move_item_down(self, item):
        """向下移动项目"""
        index = self.todo_layout.indexOf(item)
        # 确保不是最后一个有效项目（前面还有Stretch）
        if index < self.todo_layout.count() - 2:
            self.todo_layout.removeWidget(item)
            self.todo_layout.insertWidget(index + 1, item)
        
    def refresh_tags(self):
        """异步刷新标签按钮，优化性能"""
        # 如果正在刷新，跳过
        if self.tag_refresh_in_progress:
            return
            
        self.tag_refresh_in_progress = True
        
        # 收集待办事项列表（只收集有内容的项目）
        todo_items = []
        for i in range(self.todo_layout.count() - 1):  # 排除最后的Stretch
            widget = self.todo_layout.itemAt(i).widget()
            if isinstance(widget, TodoItemWidget) and widget.content_text.strip():
                todo_items.append(widget)
        
        # 如果没有待办事项，直接返回
        if not todo_items:
            self.all_tags = set()
            self.tag_refresh_in_progress = False
            # 清理所有标签按钮
            self._clear_all_tag_buttons()
            return
        
        # 创建worker和线程
        self.tag_worker = TagRefreshWorker(todo_items)
        self.tag_thread = QThread()
        self.tag_worker.moveToThread(self.tag_thread)
        
        # 连接信号
        self.tag_worker.finished.connect(self.on_tags_refreshed)
        self.tag_thread.started.connect(self.tag_worker.run)
        self.tag_worker.finished.connect(self.tag_thread.quit)
        self.tag_worker.finished.connect(self.tag_worker.deleteLater)
        self.tag_thread.finished.connect(self.tag_thread.deleteLater)
        
        # 启动线程
        self.tag_thread.start()
    
    def _clear_all_tag_buttons(self):
        """清理所有标签按钮"""
        for i in reversed(range(self.tag_layout.count() - 1)):
            widget = self.tag_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
    
    def on_tags_refreshed(self, all_tags):
        """标签刷新完成后的处理，优化按钮重用"""
        self.all_tags = all_tags
        self.tag_refresh_in_progress = False
        
        # 获取当前按钮列表
        current_buttons = {}
        for i in range(self.tag_layout.count()):
            widget = self.tag_layout.itemAt(i).widget()
            if isinstance(widget, QToolButton):
                current_buttons[widget.text()] = widget
        
        # 需要保留的标签
        tags_to_keep = set(self.all_tags)
        current_tags = set(current_buttons.keys())
        
        # 删除不需要的按钮
        tags_to_remove = current_tags - tags_to_keep
        for tag in tags_to_remove:
            if tag in current_buttons:
                button = current_buttons[tag]
                self.tag_layout.removeWidget(button)
                button.deleteLater()
        
        # 添加新按钮或重用现有按钮
        sorted_tags = sorted(list(self.all_tags))
        existing_buttons = {tag: current_buttons[tag] for tag in sorted_tags if tag in current_buttons}
        
        # 重新排列按钮
        for i, tag in enumerate(sorted_tags):
            if tag in existing_buttons:
                # 重用现有按钮
                button = existing_buttons[tag]
                button.setChecked(tag in self.selected_tags)
                # 确保按钮在正确位置
                current_index = self.tag_layout.indexOf(button)
                if current_index != i:
                    self.tag_layout.removeWidget(button)
                    self.tag_layout.insertWidget(i, button)
            else:
                # 创建新按钮
                button = self._create_tag_button(tag)
                self.tag_layout.insertWidget(i, button)
    
    def _create_tag_button(self, tag):
        """创建标签按钮，提取公共逻辑"""
        tag_button = QToolButton()
        tag_button.setText(tag)
        tag_button.setCheckable(True)
        tag_button.setChecked(tag in self.selected_tags)
        
        # 设置固定字体
        font = tag_button.font()
        font.setPointSize(11)
        font.setFamily("Microsoft YaHei UI")
        tag_button.setFont(font)
        
        # 使用预定义样式
        tag_button.setStyleSheet(self._get_tag_button_style())
        tag_button.clicked.connect(lambda checked, t=tag: self.toggle_tag_filter(t))
        
        return tag_button
    
    def _get_tag_button_style(self):
        """获取标签按钮样式字符串"""
        return """
            QToolButton {
                background-color: #666;
                color: #ccc;
                border: none;
                border-radius: 10px;
                padding: 3px 8px;
                font-size: 11px;
                font-family: "Microsoft YaHei";
            }
            QToolButton:checked {
                background-color: #4a90e2;
                color: white;
            }
            QToolButton:hover {
                background-color: #777;
            }
            QToolButton:checked:hover {
                background-color: #5aa0f0;
            }
        """
            
    def toggle_tag_filter(self, tag):
        """切换标签筛选状态"""
        if tag in self.selected_tags:
            self.selected_tags.remove(tag)
        else:
            self.selected_tags.add(tag)
            
        self.filter_todos_by_tags()
        
    def filter_todos_by_tags(self):
        """根据选中的标签过滤待办事项，优化性能"""
        # 如果没有选中的标签，显示所有事项
        if not self.selected_tags:
            for i in range(self.todo_layout.count() - 1):  # 排除最后的Stretch
                widget = self.todo_layout.itemAt(i).widget()
                if isinstance(widget, TodoItemWidget):
                    widget.setVisible(True)
            return
            
        # 否则只显示包含选中标签的事项
        for i in range(self.todo_layout.count() - 1):  # 排除最后的Stretch
            widget = self.todo_layout.itemAt(i).widget()
            if isinstance(widget, TodoItemWidget):
                # 使用缓存的标签或重新提取
                if not hasattr(widget, '_cached_tags') or widget._cached_tags is None:
                    widget._cached_tags = TodoTagExtractor.extract_tags(widget.content_text)
                
                tags = widget._cached_tags
                # 检查是否有任意一个选中的标签在该事项的标签中
                if any(tag in tags for tag in self.selected_tags):
                    widget.setVisible(True)
                else:
                    widget.setVisible(False)
                    
    def load_todos(self):
        try:
            if os.path.exists("resources/todos.json"):
                with open("resources/todos.json", "r", encoding="utf-8") as f:
                    todos = json.load(f)
                    for todo in todos:
                        self.add_todo_item(todo["text"])
        except Exception as e:
            print(f"加载待办事项出错: {e}")
        finally:
            # 加载完成后刷新标签
            self.refresh_tags()
            
    def save_todos(self):
        todos = []
        for i in range(self.todo_layout.count() - 1):  # 排除最后的Stretch
            widget = self.todo_layout.itemAt(i).widget()
            if isinstance(widget, TodoItemWidget):
                # print(widget.content_text)
                if widget.content_text.strip():  # 不保存空文本
                    todos.append({
                        "text": widget.content_text,
                        "completed": widget.is_completed()
                    })
        
        # 保存到文件
        with open("resources/todos.json", "w", encoding="utf-8") as f:
            json.dump(todos, f, ensure_ascii=False, indent=2)
            
    def update_todo_list(self):
        """更新待办事项列表，优化性能"""
        # 移除已完成或空的项目
        to_remove = []
        items_changed = False
        self.refresh_tags()
        
        for i in range(self.todo_layout.count() - 1):  # 排除最后的Stretch
            widget = self.todo_layout.itemAt(i).widget()
            if isinstance(widget, TodoItemWidget):
                if widget.is_completed() or not widget.content_text.strip():
                    to_remove.append(widget)
                    items_changed = True
        
        # 批量删除
        for widget in to_remove:
            self.todo_layout.removeWidget(widget)
            if widget in self.todo_items:
                self.todo_items.remove(widget)
            widget.deleteLater()
            
        if items_changed:
            self.save_todos()
            self.filter_todos_by_tags()
        
    def on_text_changed(self, text):
        if text.strip():
            self.save_todos()
            
    def on_return_pressed(self, item):
        if item.content_text.strip(): # 如果文本不为空
            self.save_todos()
            self.update_todo_list()
            self.setFocus()
        else:
            # 如果是空文本，移除该项目
            self.todo_layout.removeWidget(item)
            if item in self.todo_items:
                self.todo_items.remove(item)
            item.deleteLater()
            self.save_todos()
            
    def on_checkbox_clicked(self, item):
        """当复选框被点击时，如果被标记为完成，则在失去焦点后销毁"""
        if item.is_completed():
            # 连接失去焦点事件
            item.text_field.editingFinished.connect(lambda: self.remove_completed_item(item))
        # 复选框状态改变后刷新标签
        self.refresh_tags()
            
    def remove_completed_item(self, item):
        """移除已完成的项目"""
        if item.is_completed():
            self.todo_layout.removeWidget(item)
            if item in self.todo_items:
                self.todo_items.remove(item)
            item.deleteLater()
            self.save_todos()
            # 删除项目后刷新标签
            self.refresh_tags()