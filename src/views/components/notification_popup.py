"""
通用右下角静默通知弹窗

用法:
    from src.views.components.notification_popup import notify

    # 简单文本通知
    notify("操作成功", "待办事项已保存")

    # 带回调的通知
    notify("提醒", "会议还有10分钟", duration=8000, callback=lambda: open_calendar())

    # 高级用法：回调可携带参数
    notify("任务到期", f"「{task_name}」已过期", duration=0, callback=handle_expired)

功能:
    - 右下角弹出，不抢焦点
    - 自动消失（可配置时长，0=不自动消失）
    - 鼠标悬停暂停计时
    - 点击触发回调
    - 多通知自动堆叠
    - 淡入 + 滑入动画
"""

from __future__ import annotations
from typing import Optional, Callable
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QApplication, QGraphicsOpacityEffect
)
from PySide6.QtCore import (
    Qt, Signal, QTimer, QPoint, QPropertyAnimation,
    QEasingCurve, Property, QRect
)
from PySide6.QtGui import QMouseEvent, QFont
from src.utils.icon_utils import load_svg_pixmap


# ============================================================
#  颜色令牌 —— 后续可迁移到主题系统
# ============================================================
_NOTIF_BG = "rgba(40, 40, 45, 240)"        # 背景
_NOTIF_BORDER = "rgba(90, 90, 100, 180)"     # 边框
_NOTIF_TITLE = "#e0e0e0"                     # 标题色
_NOTIF_MSG = "#b0b0b0"                       # 消息色
_NOTIF_CLOSE_BG = "rgba(255,255,255,0.08)"   # 关闭按钮背景
_NOTIF_CLOSE_HOVER = "rgba(255,255,255,0.18)"


class NotificationPopup(QWidget):
    """单条通知弹窗"""

    # ---- 信号 ----
    clicked = Signal()       # 点击通知主体
    dismissed = Signal()     # 通知已关闭（动画结束后）

    def __init__(
        self,
        title: str = "",
        message: str = "",
        duration: int = 5000,       # 0 = 不自动消失
        callback: Optional[Callable] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._title = title
        self._message = message
        self._duration = duration
        self._callback = callback
        self._hovered = False
        self._dismissing = False

        # 窗口属性
        # Qt.Tool 无父窗口时可能不显示，由 NotificationManager 负责传入父窗口
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.NoFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        # 确保弹窗在任务栏不显示
        self.setAttribute(Qt.WA_QuitOnClose, False)

        self._opacity = 1.0

        self._setup_ui()
        self._setup_timers()
        self._setup_animations()

    # -------------------------------------------------------
    #  UI 构建
    # -------------------------------------------------------
    def _setup_ui(self):
        self.setFixedSize(320, 72)
        self.setStyleSheet(self._base_stylesheet())

        # 主布局
        root = QVBoxLayout(self)
        root.setContentsMargins(1, 1, 1, 1)
        root.setSpacing(0)

        # 内容容器（带圆角 + 边框）
        content = QWidget()
        content.setObjectName("notif_content")
        layout = QHBoxLayout(content)
        layout.setContentsMargins(14, 10, 8, 10)
        layout.setSpacing(8)

        # 左侧 SVG 图标
        icon_label = QLabel()
        icon_label.setFixedSize(22, 22)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("background:transparent; border:none;")
        pix = load_svg_pixmap("bell.svg", 16)
        icon_label.setPixmap(pix)
        layout.addWidget(icon_label)

        # 中间文本区域
        text_area = QVBoxLayout()
        text_area.setSpacing(2)

        self.title_label = QLabel(self._title)
        self.title_label.setObjectName("notif_title")
        f = self.title_label.font()
        f.setPointSize(10)
        f.setBold(True)
        self.title_label.setFont(f)
        text_area.addWidget(self.title_label)

        self.msg_label = QLabel(self._message)
        self.msg_label.setObjectName("notif_msg")
        self.msg_label.setWordWrap(True)
        f2 = self.msg_label.font()
        f2.setPointSize(9)
        self.msg_label.setFont(f2)
        text_area.addWidget(self.msg_label)

        layout.addLayout(text_area, 1)

        # 关闭按钮
        self.close_btn = QPushButton("×")
        self.close_btn.setObjectName("notif_close")
        self.close_btn.setFixedSize(22, 22)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.clicked.connect(self.dismiss)
        layout.addWidget(self.close_btn, alignment=Qt.AlignTop)

        root.addWidget(content)

        # 透明度效果
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity_effect)

    def _base_stylesheet(self) -> str:
        return f"""
            NotificationPopup {{
                background: transparent;
                border: none;
            }}
            #notif_content {{
                background: {_NOTIF_BG};
                border: 1px solid {_NOTIF_BORDER};
                border-radius: 10px;
            }}
            #notif_title {{
                color: {_NOTIF_TITLE};
                background: transparent;
                border: none;
            }}
            #notif_msg {{
                color: {_NOTIF_MSG};
                background: transparent;
                border: none;
            }}
            #notif_close {{
                color: {_NOTIF_MSG};
                background: {_NOTIF_CLOSE_BG};
                border: none;
                border-radius: 11px;
                font-size: 14px;
                font-weight: bold;
            }}
            #notif_close:hover {{
                background: {_NOTIF_CLOSE_HOVER};
                color: #fff;
            }}
        """

    # -------------------------------------------------------
    #  计时器
    # -------------------------------------------------------
    def _setup_timers(self):
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self.dismiss)

        if self._duration > 0:
            self._dismiss_timer.start(self._duration)

    # -------------------------------------------------------
    #  动画
    # -------------------------------------------------------
    def _setup_animations(self):
        # 透明度动画
        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(250)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)

        # 位置动画
        self._slide_anim = QPropertyAnimation(self, b"pos")
        self._slide_anim.setDuration(300)
        self._slide_anim.setEasingCurve(QEasingCurve.OutCubic)

    @property
    def opacity(self) -> float:
        return self._opacity

    @opacity.setter
    def opacity(self, v: float):
        self._opacity = v

    # -------------------------------------------------------
    #  显示 & 隐藏
    # -------------------------------------------------------
    def show_at(self, target_pos: QPoint):
        """从目标位置右侧滑入"""
        start_pos = QPoint(target_pos.x() + self.width() + 20, target_pos.y())
        self.move(start_pos)
        self.show()
        self.raise_()
        # 强制刷新确保窗口可见
        QApplication.processEvents()

        # 滑入动画
        self._slide_anim.setStartValue(start_pos)
        self._slide_anim.setEndValue(target_pos)
        self._slide_anim.start()

    def dismiss(self):
        """关闭通知（带动画）"""
        if self._dismissing:
            return
        self._dismissing = True
        self._dismiss_timer.stop()

        # 淡出
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self._on_dismissed)
        self._fade_anim.start()

    def _on_dismissed(self):
        self.hide()
        self.dismissed.emit()
        self.deleteLater()

    # -------------------------------------------------------
    #  事件
    # -------------------------------------------------------
    def enterEvent(self, event):
        self._hovered = True
        if self._duration > 0 and not self._dismissing:
            self._dismiss_timer.stop()

    def leaveEvent(self, event):
        self._hovered = False
        if self._duration > 0 and not self._dismissing:
            remaining = self._duration  # 重新开始完整倒计时
            self._dismiss_timer.start(remaining)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            # 避免点击关闭按钮时重复触发回调
            if self.close_btn.geometry().contains(event.pos()):
                super().mouseReleaseEvent(event)
                return
            self.clicked.emit()
            if self._callback:
                self._callback()
            self.dismiss()
        super().mouseReleaseEvent(event)


# ============================================================
#  NotificationManager —— 管理多通知堆叠
# ============================================================
class NotificationManager:
    """通知管理器（单例）

    职责:
      - 管理活跃通知列表
      - 自动计算堆叠位置
      - 最大同时显示数量控制
    """

    _instance: Optional["NotificationManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._active: list[NotificationPopup] = []
        self._max_visible = 5
        self._spacing = 8       # 通知之间的间距
        self._margin_right = 20
        self._margin_bottom = 20

    # ---- 公开 API ----

    @staticmethod
    def _find_main_window():
        """查找主窗口作为弹窗父窗口（确保 Qt.Tool 能正常显示）"""
        app = QApplication.instance()
        if app is None:
            return None
        for w in app.topLevelWidgets():
            if w.isVisible() and w.windowTitle() == "SMT2":
                return w
        return None

    def notify(
        self,
        title: str,
        message: str = "",
        duration: int = 5000,
        callback: Optional[Callable] = None,
    ) -> NotificationPopup:
        """推送一条通知"""
        parent = self._find_main_window()
        popup = NotificationPopup(title, message, duration, callback, parent=parent)
        popup.dismissed.connect(lambda: self._on_popup_dismissed(popup))

        # 限制最大数量
        if len(self._active) >= self._max_visible:
            oldest = self._active.pop(0)
            oldest.dismiss()

        self._active.append(popup)
        self._reposition_all()
        return popup

    def _on_popup_dismissed(self, popup: NotificationPopup):
        if popup in self._active:
            self._active.remove(popup)
            self._reposition_all()

    def _reposition_all(self):
        """重新计算所有活跃通知的位置"""
        if not self._active:
            return

        screen = QApplication.primaryScreen()
        if not screen:
            return
        screen_geo = screen.availableGeometry()

        total_height = (
            sum(p.height() for p in self._active)
            + self._spacing * (len(self._active) - 1)
        )

        base_y = screen_geo.bottom() - self._margin_bottom - total_height
        base_x = screen_geo.right() - self._margin_right

        y = base_y
        for popup in self._active:
            target = QPoint(base_x - popup.width(), y)
            if popup.isVisible():
                # 已可见的通知用动画移到新位置
                popup._slide_anim.stop()
                popup._slide_anim.setStartValue(popup.pos())
                popup._slide_anim.setEndValue(target)
                popup._slide_anim.start()
            else:
                popup.show_at(target)
            y += popup.height() + self._spacing


# ============================================================
#  全局便利函数
# ============================================================
_notification_manager: Optional[NotificationManager] = None


def _get_manager() -> NotificationManager:
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager


def notify(
    title: str,
    message: str = "",
    duration: int = 5000,
    callback: Optional[Callable] = None,
) -> NotificationPopup:
    """便捷函数：右下角弹出通知

    Args:
        title:   标题（粗体）
        message: 正文（支持自动换行）
        duration:自动消失毫秒数，0 = 不自动消失
        callback:点击通知时执行的回调

    Returns:
        NotificationPopup 实例，可进一步连接信号

    Example:
        >>> notify("保存成功", "配置已更新")
        >>> notify("任务到期", "「周报」还有10分钟", duration=8000,
        ...         callback=lambda: open_todo())
    """
    return _get_manager().notify(title, message, duration, callback)
