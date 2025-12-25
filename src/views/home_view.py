from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class HomeView(QWidget):
    def __init__(self):
        super().__init__()
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(50, 80, 50, 50)
        
        # 添加标题
        title_label = QLabel("欢迎使用 SMT2 工具箱")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #333;
            padding: 20px;
        """)
        
        # 添加描述
        desc_label = QLabel("这是一个多功能工具箱，提供各种实用功能")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("""
            font-size: 16px;
            color: #666;
            padding: 10px;
        """)
        
        # 添加功能列表
        features_label = QLabel("""
        <ul style="text-align: left; margin-left: 50px;">
            <li>配置管理 - 轻松管理应用配置</li>
            <li>主题切换 - 支持明暗主题切换</li>
            <li>窗口置顶 - 快速置顶任意窗口</li>
            <li>性能监控 - 实时监控系统性能</li>
        </ul>
        """)
        features_label.setAlignment(Qt.AlignCenter)
        features_label.setStyleSheet("""
            font-size: 14px;
            color: #555;
            padding: 20px;
        """)
        
        # 添加占位符以居中内容
        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        layout.addWidget(features_label)
        layout.addStretch()  # 添加伸缩器以保持内容在顶部