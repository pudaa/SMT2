"""
待办事项详情配置弹窗

紧凑、无边框、可拖拽，匹配 SMT2 深色主题风格。
由 TodoItemWidget 右键触发。
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDateTimeEdit, QComboBox
)
from PySide6.QtCore import Qt, QDateTime, QPoint, QRectF
from PySide6.QtGui import QMouseEvent, QPainter, QBrush, QColor, QPen
from src.configs.base_config import get_qss_color


_REPEAT_OPTIONS = [
    ("none", "不重复"),
    ("daily", "每天"),
    ("weekly", "每周"),
    ("monthly", "每月"),
]

_REMIND_OPTIONS = [
    (0, "不提醒"),
    (5, "5 分钟前"),
    (10, "10 分钟前"),
    (15, "15 分钟前"),
    (30, "30 分钟前"),
    (60, "1 小时前"),
    (120, "2 小时前"),
    (1440, "1 天前"),
]


class TodoDetailDialog(QDialog):
    """待办事项详情配置弹窗"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_pos: Optional[QPoint] = None

        # 颜色缓存（_apply_theme 填充）
        self._bg_color = QColor(40, 40, 55, 245)
        self._border_color = QColor(120, 120, 140, 100)

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(175, 170)

        self._setup_ui()
        self._apply_theme()

    # ================================================================
    #  UI
    # ================================================================
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        content = QVBoxLayout()
        content.setContentsMargins(16, 0, 14, 0)
        content.setSpacing(6)

        # 标题栏（可拖拽）
        title_bar = QHBoxLayout()
        title_bar.setSpacing(0)
        title = QLabel("待办配置")
        title.setObjectName("dlg_title")
        title_bar.addWidget(title)
        title_bar.addStretch()

        close_btn = QPushButton("×")
        close_btn.setObjectName("dlg_close")
        close_btn.setFixedSize(22, 22)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        title_bar.addWidget(close_btn)

        content.addLayout(title_bar)

        # ---- 截止时间 ----
        dl_layout = QHBoxLayout()
        dl_layout.setSpacing(8)

        dl_label = QLabel("截止")
        dl_label.setObjectName("dlg_label")
        dl_label.setFixedWidth(28)
        dl_layout.addWidget(dl_label)

        self.deadline_edit = QDateTimeEdit()
        self.deadline_edit.setObjectName("dlg_deadline")
        self.deadline_edit.setCalendarPopup(True)
        self.deadline_edit.setDisplayFormat("MM-dd HH:mm")
        self.deadline_edit.setMinimumDateTime(QDateTime.currentDateTime())
        self.deadline_edit.setDateTime(QDateTime.currentDateTime().addSecs(86400))
        dl_layout.addWidget(self.deadline_edit, 1)

        # self.clear_deadline_btn = QPushButton("✕")
        # self.clear_deadline_btn.setObjectName("dlg_clear")
        # self.clear_deadline_btn.setFixedSize(22, 22)
        # self.clear_deadline_btn.setCursor(Qt.PointingHandCursor)
        # self.clear_deadline_btn.clicked.connect(self._clear_deadline)
        # dl_layout.addWidget(self.clear_deadline_btn)

        content.addLayout(dl_layout)

        # ---- 提前提醒（下拉列表） ----
        remind_layout = QHBoxLayout()
        remind_layout.setSpacing(8)

        rm_label = QLabel("提醒")
        rm_label.setObjectName("dlg_label")
        rm_label.setFixedWidth(28)
        remind_layout.addWidget(rm_label)

        self.remind_combo = QComboBox()
        self.remind_combo.setObjectName("dlg_remind")
        for value, display in _REMIND_OPTIONS:
            self.remind_combo.addItem(display, value)
        remind_layout.addWidget(self.remind_combo, 1)

        content.addLayout(remind_layout)

        # ---- 重复 ----
        rp_layout = QHBoxLayout()
        rp_layout.setSpacing(8)

        rp_label = QLabel("重复")
        rp_label.setObjectName("dlg_label")
        rp_label.setFixedWidth(28)
        rp_layout.addWidget(rp_label)

        self.repeat_combo = QComboBox()
        self.repeat_combo.setObjectName("dlg_repeat")
        for value, display in _REPEAT_OPTIONS:
            self.repeat_combo.addItem(display, value)
        rp_layout.addWidget(self.repeat_combo, 1)

        content.addLayout(rp_layout)

        # ---- 按钮 ----
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("dlg_cancel")
        self.cancel_btn.setFixedHeight(28)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.ok_btn = QPushButton("确定")
        self.ok_btn.setObjectName("dlg_ok")
        self.ok_btn.setFixedHeight(28)
        self.ok_btn.setCursor(Qt.PointingHandCursor)
        self.ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.ok_btn)

        content.addLayout(btn_layout)
        layout.addLayout(content)

    # ================================================================
    #  主题样式
    # ================================================================
    def _apply_theme(self):
        # 使用主面板背景令牌，匹配当前主题的半透明圆角风格
        bg_raw = get_qss_color("performance_panel_background", [50, 50, 50, 200])
        border_raw = get_qss_color("todo_panel_tagbutton_background", [80, 80, 80])
        fg = get_qss_color("todo_panel_todoitem_lineedit_foreground", "#ccc")
        muted = get_qss_color("todo_panel_todoitem_draglabel", "#999")
        accent = get_qss_color("todo_panel_todoitem_checkbox_checked_background", "#4a90e2")

        def _to_color(val, dr, dg, db, da=255):
            if isinstance(val, list):
                return QColor(val[0], val[1], val[2], val[3] if len(val) > 3 else da)
            return QColor(dr, dg, db, da)

        self._bg_color = _to_color(bg_raw, 50, 50, 50, 220)
        self._border_color = _to_color(border_raw, 80, 80, 80, 60)

        bg_css = f"rgba({self._bg_color.red()},{self._bg_color.green()},{self._bg_color.blue()},{self._bg_color.alpha()})"
        border_css = f"rgba({self._border_color.red()},{self._border_color.green()},{self._border_color.blue()},{self._border_color.alpha()})"
        input_bg = "rgba(255,255,255,0.06)"
        if isinstance(muted, list):
            muted = f"rgba({muted[0]},{muted[1]},{muted[2]},{muted[3]})"

        # 仅设置子控件样式，背景由 paintEvent 绘制（不透明，防穿透）
        self.setStyleSheet(f"""
            #dlg_title {{
                color: {fg};
                font-size: 13px;
                font-weight: bold;
                background: transparent;
                border: none;
            }}
            #dlg_close {{
                color: {muted};
                background: transparent;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
            }}
            #dlg_close:hover {{
                color: #fff;
                background: rgba(255,80,80,0.25);
            }}
            #dlg_label {{
                color: {muted};
                font-size: 12px;
                background: transparent;
                border: none;
            }}
            #dlg_deadline, #dlg_remind, #dlg_repeat {{
                background: {input_bg};
                border: 1px solid {border_css};
                border-radius: 5px;
                color: {fg};
                padding: 3px 6px;
                font-size: 12px;
            }}
            #dlg_deadline:focus, #dlg_remind:focus, #dlg_repeat:focus {{
                border-color: {accent};
            }}
            #dlg_deadline::drop-down, #dlg_remind::drop-down, #dlg_repeat::drop-down {{
                border-color: {accent};
            }}
            #dlg_deadline::drop-down, #dlg_repeat::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 16px;
                border-left: 1px solid {border_css};
            }}
            #dlg_deadline QAbstractItemView, #dlg_remind QAbstractItemView, #dlg_repeat QAbstractItemView {{
                background: {bg_css};
                color: {fg};
                selection-background-color: {accent};
                border: 1px solid {border_css};
            }}
            #dlg_clear {{
                color: {muted};
                background: transparent;
                border: none;
                border-radius: 10px;
                font-size: 13px;
            }}
            #dlg_clear:hover {{
                color: #ff6b6b;
                background: rgba(255,80,80,0.15);
            }}
            #dlg_cancel {{
                color: {muted};
                background: rgba(255,255,255,0.05);
                border: none;
                border-radius: 5px;
                font-size: 12px;
            }}
            #dlg_cancel:hover {{
                color: {fg};
                background: rgba(255,255,255,0.12);
            }}
            #dlg_ok {{
                color: #fff;
                background: {accent};
                border: none;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
            }}
            #dlg_ok:hover {{
                background: #5aa0f0;
            }}
        """)

    # ================================================================
    #  自绘背景（WA_TranslucentBackground + drawRoundedRect，与主题一致）
    # ================================================================
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = 10
        w, h = self.width(), self.height()

        # 填充半透明背景（与主题 paint_panel 完全相同的绘制方式）
        p.setBrush(QBrush(self._bg_color))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, w, h, r, r)

        # 边框
        pen = QPen(self._border_color)
        pen.setWidthF(1.0)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(0.5, 0.5, w - 1.0, h - 1.0, r, r)

        p.end()

    # ================================================================
    #  拖拽（标题栏区域）
    # ================================================================
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            if event.position().y() < 40:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_pos is not None and event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    # ================================================================
    #  数据存取
    # ================================================================
    def set_data(
        self,
        deadline: Optional[str] = None,
        reminder_minutes: int = 10,
        repeat: Optional[str] = None,
    ):
        self._has_deadline = deadline is not None

        if deadline:
            try:
                dt = datetime.fromisoformat(deadline)
                qt_dt = QDateTime(dt.year, dt.month, dt.day, dt.hour, dt.minute)
                self.deadline_edit.setDateTime(qt_dt)
            except (ValueError, TypeError):
                self._clear_deadline()
        else:
            self._clear_deadline()

        self.remind_combo.setCurrentIndex(
            next((i for i in range(self.remind_combo.count())
                  if self.remind_combo.itemData(i) == reminder_minutes), 1)
        )

        idx = self.repeat_combo.findData(repeat or "none")
        if idx >= 0:
            self.repeat_combo.setCurrentIndex(idx)

    def get_data(self) -> dict:
        if getattr(self, "_has_deadline", True):
            qt_dt = self.deadline_edit.dateTime()
            py_dt = datetime(
                qt_dt.date().year(), qt_dt.date().month(), qt_dt.date().day(),
                qt_dt.time().hour(), qt_dt.time().minute(),
            )
            deadline_str = py_dt.isoformat()
        else:
            deadline_str = None

        repeat_value = self.repeat_combo.currentData()
        return {
            "deadline": deadline_str,
            "reminder_minutes": self.remind_combo.currentData(),
            "repeat": None if repeat_value == "none" else repeat_value,
        }

    def _clear_deadline(self):
        self._has_deadline = False
        # 不再禁用 deadline_edit，让用户可以随时重新配置截止时间

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            pc = self.parent().mapToGlobal(self.parent().rect().center())
            self.move(pc.x() - self.width() // 2, pc.y() - self.height() // 2)

