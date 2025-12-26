from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QFrame, 
                               QListWidget, QListWidgetItem, QStackedWidget,
                               QApplication, QLabel, QPushButton, QSplitter,
                               QToolButton)
from PySide6.QtCore import Qt, QSize, Signal, QPoint, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QIcon, QPalette, QColor, QPainter, QPen
from .home_view import HomeView
from .setting_view import SettingView


class Switch(QWidget):
    """自定义开关组件"""
    # 添加toggled信号
    toggled = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 26) 
        self.is_checked = False
        self.animation = QPropertyAnimation(self, b"geometry", self)
        self.animation.setDuration(200)  # 动画持续时间
        self.animation.setEasingCurve(QEasingCurve.InOutCubic)
        
    def paintEvent(self, event):
        """绘制开关"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 获取当前主题状态
        parent = self.parent()
        is_dark_theme = False
        while parent:
            if hasattr(parent, 'is_dark_theme'):
                is_dark_theme = parent.is_dark_theme
                break
            parent = parent.parent()
        
        # 绘制背景
        if self.is_checked:
            if is_dark_theme:
                painter.setBrush(QColor(100, 150, 255))  # 深色主题下开启状态的蓝色
            else:
                painter.setBrush(QColor(50, 120, 255))   # 浅色主题下开启状态的蓝色
        else:
            if is_dark_theme:
                painter.setBrush(QColor(80, 80, 80))  # 深色主题下关闭状态的灰色
            else:
                painter.setBrush(QColor(180, 180, 180))  # 浅色主题下关闭状态的灰色
        
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 13, 13)
        
        # 绘制滑块
        if is_dark_theme:
            painter.setBrush(QColor(240, 240, 240))  # 深色主题下的滑块颜色
        else:
            painter.setBrush(QColor(255, 255, 255))  # 浅色主题下的滑块颜色
            
        if self.is_checked:
            slider_x = self.width() - 24  # 开启状态下滑块位置
        else:
            slider_x = 4  # 关闭状态下滑块位置
            
        painter.drawEllipse(slider_x, 3, 20, 20)
    
    def mousePressEvent(self, event):
        """处理鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            self.toggle()
            return super().mousePressEvent(event)
    
    def toggle(self):
        """切换开关状态"""
        self.is_checked = not self.is_checked
        self.update()
        self.toggled.emit(self.is_checked)  # 发射信号
    
    def setChecked(self, checked):
        """设置开关状态"""
        if self.is_checked != checked:
            self.is_checked = checked
            self.update()
            self.toggled.emit(self.is_checked)  # 发射信号
    
    def isChecked(self):
        """获取开关状态"""
        return self.is_checked


class ToolBoxWindow(QWidget):
    def __init__(self):
        super().__init__()
        # 设置为无边框窗口并添加圆角
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("SMT2 工具箱")
        self.resize(1000, 650)
        
        # 设置窗口图标
        self.setWindowIcon(QIcon("resources/tray.png"))
        
        # 初始化主题状态
        self.is_dark_theme = False
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10) 
        
        # 创建主内容框架（带圆角）
        self.main_frame = QFrame()
        self.main_frame.setObjectName("mainFrame")
        frame_layout = QVBoxLayout(self.main_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建自定义标题栏
        self.title_bar = self.create_title_bar()
        frame_layout.addWidget(self.title_bar)
        
        # 创建内容区域
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        content_layout.addWidget(splitter)
        
        # 左侧导航面板
        self.nav_panel = self.create_nav_panel()
        self.nav_panel.setMaximumWidth(200)
        self.nav_panel.setMinimumWidth(200)
        
        # 右侧面板
        self.content_panel = QFrame()
        self.content_panel.setObjectName("contentPanel")
        
        # 右侧布局
        right_layout = QVBoxLayout(self.content_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)
        
        # 右侧内容堆叠窗口
        self.stacked_widget = QStackedWidget()
        right_layout.addWidget(self.stacked_widget)
        
        # 添加应用按钮
        self.apply_button = QPushButton("应用")
        self.apply_button.setObjectName("applyButton")
        self.apply_button.setFixedSize(80, 30)
        self.apply_button.hide()
        self.apply_button.clicked.connect(self.apply_changes)
        
        # 创建一个定位应用按钮的透明布局
        self.apply_container = QWidget()
        self.apply_container.setObjectName("applyContainer")
        apply_container_layout = QHBoxLayout(self.apply_container)
        apply_container_layout.setContentsMargins(0, 0, 10, 10)
        apply_container_layout.addStretch()
        apply_container_layout.addWidget(self.apply_button)
        
        # 添加到右侧布局
        right_layout.addWidget(self.apply_container)
        
        # 添加到分割器
        splitter.addWidget(self.nav_panel)
        splitter.addWidget(self.content_panel)
        splitter.setSizes([200, 800])
        
        # 将内容区域添加到主布局
        frame_layout.addWidget(content_widget)
        
        main_layout.addWidget(self.main_frame)
        
        # 创建视图
        self.home_view = HomeView()
        self.setting_view = SettingView()
        
        # 设置应用按钮的回调
        self.setting_view.changes_made.connect(self.show_apply_button)
        
        # 添加到堆叠窗口
        self.stacked_widget.addWidget(self.home_view)
        self.stacked_widget.addWidget(self.setting_view)
        
        # 设置初始页面
        self.current_view = self.home_view
        self.nav_list.setCurrentRow(0)
        
        # 应用样式
        self.apply_stylesheet()
        
        # 连接导航信号
        self.nav_list.currentRowChanged.connect(self.switch_view)

    def create_title_bar(self):
        """创建自定义标题栏"""
        title_bar = QFrame()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(40)
        
        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)
        
        # 标题标签
        self.title_label = QLabel("SMT2 工具箱")
        self.title_label.setObjectName("titleLabel")
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        # 最小化按钮
        min_btn = QToolButton()
        min_btn.setText("−")
        min_btn.setObjectName("minimizeButton")
        min_btn.setFixedSize(30, 30)
        min_btn.clicked.connect(self.showMinimized)
        
        # 关闭按钮
        close_btn = QToolButton()
        close_btn.setText("×")
        close_btn.setObjectName("closeButton")
        close_btn.setFixedSize(30, 30)
        close_btn.clicked.connect(self.hide)  # 改为隐藏而不是关闭
        
        layout.addWidget(self.title_label)
        layout.addStretch()
        layout.addWidget(min_btn)
        layout.addWidget(close_btn)
        
        return title_bar

    def create_nav_panel(self):
        """创建导航面板"""
        panel = QFrame()
        panel.setObjectName("navPanel")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 标题
        title_label = QLabel("SMT2 工具箱")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setObjectName("titleLabel")
        title_label.setStyleSheet("padding: 20px 0px 20px 0px; font-size: 16px; font-weight: bold;")
        
        # 导航列表
        self.nav_list = QListWidget()
        self.nav_list.setSpacing(5)
        self.nav_list.setObjectName("navList")
        
        # 添加导航项
        nav_items = [
            {"name": "首页", "icon": None},
            {"name": "设置", "icon": None},
        ]
        
        for item in nav_items:
            list_item = QListWidgetItem(item["name"])
            list_item.setTextAlignment(Qt.AlignCenter)
            self.nav_list.addItem(list_item)
        
        # 主题切换容器
        theme_container = QWidget()
        theme_layout = QHBoxLayout(theme_container)
        theme_layout.setContentsMargins(15, 10, 15, 10)
        
        # 主题标签
        theme_label = QLabel("深色模式")
        theme_label.setObjectName("themeLabel")
        
        # 主题切换开关
        self.theme_switch = Switch()
        self.theme_switch.setChecked(False)  # 初始为浅色主题
        self.theme_switch.toggled.connect(self.toggle_theme)  # 连接切换主题函数
        
        theme_layout.addWidget(theme_label)
        theme_layout.addStretch()
        theme_layout.addWidget(self.theme_switch)
        
        layout.addWidget(title_label)
        layout.addWidget(self.nav_list)
        layout.addWidget(theme_container)
        
        return panel

    def switch_view(self, index):
        """切换视图"""
        self.stacked_widget.setCurrentIndex(index)
        if index == 0:
            self.current_view = self.home_view
        elif index == 1:
            self.current_view = self.setting_view

    def show_apply_button(self):
        """显示或隐藏应用按钮，根据配置是否被修改"""
        # 检查配置是否被修改
        if self.is_config_modified():
            self.apply_button.show()
        else:
            self.apply_button.hide()
    
    def is_config_modified(self):
        """检查配置是否被修改"""
        # 获取setting_view的当前配置和原始配置
        current_config = self.setting_view.config_data
        original_config = self.setting_view.original_config
        
        # 比较两个配置是否相同
        import json
        return json.dumps(current_config, sort_keys=True) != json.dumps(original_config, sort_keys=True)

    def apply_changes(self):
        """应用配置更改"""
        self.setting_view.apply_changes()
        # 隐藏应用按钮
        self.apply_button.hide()

    def mousePressEvent(self, event):
        """处理鼠标按下事件以实现窗口拖动"""
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """处理鼠标移动事件以实现窗口拖动"""
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_start_position)
            event.accept()

    def toggle_theme(self):
        """切换明暗主题"""
        if self.is_dark_theme:
            # 切换到亮色主题
            self.set_light_theme()
            self.is_dark_theme = False
        else:
            # 切换到暗色主题
            self.set_dark_theme()
            self.is_dark_theme = True
    
    def apply_stylesheet(self):
        """应用样式表"""
        if self.is_dark_theme:
            self.set_dark_theme()
        else:
            self.set_light_theme()
    
    def set_light_theme(self):
        """设置浅色主题"""
        self.is_dark_theme = False
        self.setStyleSheet("""
            /* 主窗口样式 */
            #mainFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 15px;
            }
            
            #titleBar {
                background-color: white;
                border-bottom: 1px solid #e0e0e0;
                border-top-left-radius: 15px;
                border-top-right-radius: 15px;
            }
            
            #navPanel {
                background-color: white;
                border-right: 1px solid #e0e0e0;
                border-bottom-left-radius: 15px;
            }
            
            #contentPanel {
                background-color: white;
                border-bottom-right-radius: 15px;
            }
            
            #themeButton {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 15px;
                padding: 15px;
                color: #333333;
            }
            
            #themeButton:hover {
                background-color: #f5f5f5;
            }
            
            
            /* 分割器样式 */
            QSplitter::handle {
                background-color: #e0e0e0;
            }
            
            QSplitter::handle:horizontal {
                width: 1px;
            }
            
            QSplitter::handle:vertical {
                height: 1px;
            }
            
            /* 导航列表项样式 */
            QListWidget#navList {
                background-color: white;
                border: none;
                outline: none;
                border-radius: 10px;
            }
            
            QListWidget#navList::item {
                background-color: white;
                border: none;
                padding: 8px 16px;
                margin: 2px 0;
                border-radius: 8px;
                color: #333333;
            }
            
            QListWidget#navList::item:selected {
                background-color: #e0e0e0;
                color: #333333;
            }
            
            QListWidget#navList::item:hover {
                background-color: #f5f5f5;
            }
            
            /* 首页视图样式 */
            #homeView {
                background-color: white;
                border-radius: 10px;
            }
            
            #scrollWidget {
                background-color: white;
                border-radius: 10px;
            }
            
            /* 设置视图样式 */
            #settingView {
                background-color: white;
                border-radius: 10px;
            }
            
            QGroupBox {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
                color: #333333;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #333333;
            }
            
            QLineEdit {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                padding: 5px;
                color: #333333;
            }
            
            QPushButton {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                padding: 5px 10px;
                color: #333333;
            }
            
            QPushButton:hover {
                background-color: #f5f5f5;
            }
            
            QToolButton {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                padding: 2px;
                color: #333333;
            }
            
            QToolButton:hover {
                background-color: #f5f5f5;
            }
            
            QLabel {
                background-color: transparent;
                color: #333333;
            }
        """)
    
    def set_dark_theme(self):
        """设置深色主题"""
        self.is_dark_theme = True
        self.setStyleSheet("""
            /* 主窗口样式 */
            #mainFrame {
                background-color: #2b2b2b;
                border: 1px solid #404040;
                border-radius: 15px;
            }
            
            #titleBar {
                background-color: #2b2b2b;
                border-bottom: 1px solid #404040;
                border-top-left-radius: 15px;
                border-top-right-radius: 15px;
            }
            
            #navPanel {
                background-color: #2b2b2b;
                border-right: 1px solid #404040;
                border-bottom-left-radius: 15px;
            }
            
            #contentPanel {
                background-color: #2b2b2b;
                border-bottom-right-radius: 15px;
            }
            
            #themeButton {
                background-color: #2b2b2b;
                border: 1px solid #404040;
                border-radius: 15px;
                padding: 15px;
                color: #ffffff;
            }
            
            #themeButton:hover {
                background-color: #404040;
            }
            
            /* 分割器样式 */
            QSplitter::handle {
                background-color: #404040;
            }
            
            QSplitter::handle:horizontal {
                width: 1px;
            }
            
            QSplitter::handle:vertical {
                height: 1px;
            }
            /* 导航列表项样式 */
            QListWidget#navList {
                background-color: #2b2b2b;
                border: none;
                outline: none;
                border-radius: 10px;
            }
            
            QListWidget#navList::item {
                background-color: #2b2b2b;
                border: none;
                padding: 8px 16px;
                margin: 2px 0;
                border-radius: 8px;
                color: #ffffff;
            }
            
            QListWidget#navList::item:selected {
                background-color: #404040;
                color: #ffffff;
            }
            
            QListWidget#navList::item:hover {
                background-color: #404040;
            }
            
            /* 首页视图样式 */
            #homeView {
                background-color: #2b2b2b;
                border-radius: 10px;
            }
            
            #scrollWidget {
                background-color: #2b2b2b;
                border-radius: 10px;
            }
            
            /* 设置视图样式 */
            #settingView {
                background-color: #2b2b2b;
                border-radius: 10px;
            }
            
            QGroupBox {
                background-color: #2b2b2b;
                border: 1px solid #404040;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
                color: #ffffff;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
            }
            
            QLineEdit {
                background-color: #2b2b2b;
                border: 1px solid #404040;
                border-radius: 5px;
                padding: 5px;
                color: #ffffff;
            }
            
            QPushButton {
                background-color: #2b2b2b;
                border: 1px solid #404040;
                border-radius: 5px;
                padding: 5px 10px;
                color: #ffffff;
            }
            
            QPushButton:hover {
                background-color: #404040;
            }
            
            QToolButton {
                background-color: #2b2b2b;
                border: 1px solid #404040;
                border-radius: 5px;
                padding: 2px;
                color: #ffffff;
            }
            
            QToolButton:hover {
                background-color: #404040;
            }
            
            QLabel {
                background-color: transparent;
                color: #ffffff;
            }
        """)