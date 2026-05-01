"""Boss row widget — single entry in the boss tracking table."""

from datetime import datetime
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from .widgets import StarRatingWidget
from .map_widgets import MapIconLabel


class BossRow(QFrame):
    """Single row displaying boss information."""

    delete_clicked = pyqtSignal(str, str)
    rating_changed = pyqtSignal(str, str, int)

    _ROW_DEFAULT = """
        QFrame {
            background: rgba(255, 255, 255, 0.025);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 8px;
        }
        QFrame:hover {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(99, 102, 241, 0.3);
        }
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._boss_name = ""
        self._channel = ""
        self._boss_key = ""
        self._current_status = "N"
        self._last_updated_dt: Optional[datetime] = None
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(self._ROW_DEFAULT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(4)

        # Boss Name
        self.name_label = QLabel("")
        self.name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.name_label.setStyleSheet("color: #E2E8F0; background: transparent;")
        self.name_label.setFixedWidth(140)
        layout.addWidget(self.name_label)

        # Map with icon popup
        self.map_icon_label = MapIconLabel()
        layout.addWidget(self.map_icon_label)

        # LV Badge
        self.lv_label = QLabel("")
        self.lv_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lv_label.setStyleSheet("""
            color: #475569;
            background: transparent;
            padding: 2px 6px;
            border-radius: 4px;
        """)
        self.lv_label.setFixedWidth(45)
        self.lv_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lv_label)

        # Channel
        self.channel_label = QLabel("")
        self.channel_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.channel_label.setStyleSheet("""
            color: #475569;
            background: rgba(255, 255, 255, 0.04);
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid rgba(255, 255, 255, 0.06);
        """)
        self.channel_label.setFixedWidth(50)
        self.channel_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.channel_label)

        # Status Badge
        self.boss_status_label = QLabel("")
        self.boss_status_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.boss_status_label.setStyleSheet("""
            color: #475569;
            background: rgba(255, 255, 255, 0.04);
            padding: 2px 8px;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.06);
        """)
        self.boss_status_label.setFixedWidth(55)
        self.boss_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.boss_status_label)

        # Time
        self.time_label = QLabel("")
        self.time_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.time_label.setStyleSheet("color: #475569; background: transparent;")
        self.time_label.setFixedWidth(55)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.time_label)

        # Update Date
        self.update_date_label = QLabel("")
        self.update_date_label.setFont(QFont("Segoe UI", 9))
        self.update_date_label.setStyleSheet("color: #334155; background: transparent;")
        self.update_date_label.setFixedWidth(65)
        self.update_date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.update_date_label)

        # Star Rating
        self.rating_widget = StarRatingWidget()
        self.rating_widget.rating_changed.connect(self._on_rating_changed)
        layout.addWidget(self.rating_widget)

        # Delete button
        self.delete_btn = QPushButton("✕")
        self.delete_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.delete_btn.setFixedSize(24, 24)
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                color: #475569;
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 5px;
                padding: 0px;
            }
            QPushButton:hover {
                color: #FDA4AF;
                background: rgba(244, 63, 94, 0.15);
                border: 1px solid rgba(244, 63, 94, 0.3);
            }
            QPushButton:pressed {
                background: rgba(244, 63, 94, 0.25);
            }
        """)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        layout.addWidget(self.delete_btn)

    def _on_rating_changed(self, boss_name: str, channel: str, rating: int):
        self.rating_changed.emit(boss_name, channel, rating)

    def _on_delete_clicked(self):
        self.delete_clicked.emit(self._boss_name, self._channel)

    def set_data(self, name: str, map_name: str, channel: str, status: str, boss_type: str = "", time: str = "--", map_lv: str = "", urgent: bool = False, update_date: str = "--", expired: bool = False, note: str = "--"):
        self._boss_name = name
        self._channel = channel
        self._boss_key = f"{name.lower()}_{channel}"

        if boss_type and boss_type != "--":
            display_name = f"{name} ({boss_type})"
            full_name = f"{name} ({boss_type})"
        else:
            display_name = name
            full_name = name
        self.name_label.setText(display_name[:20])
        self.name_label.setToolTip(full_name)
        self.map_icon_label.set_map_data(map_name if map_name and map_name != "" and map_name != "--" else "", map_lv, urgent, name)

        if map_lv:
            self.lv_label.setText(map_lv)
            self.lv_label.setStyleSheet("""
                color: #A5B4FC;
                background: rgba(99, 102, 241, 0.18);
                padding: 2px 6px;
                border-radius: 4px;
                border: 1px solid rgba(99, 102, 241, 0.35);
                font-weight: 700;
            """)
        else:
            self.lv_label.setText("")
            self.lv_label.setStyleSheet("""
                color: #475569;
                background: transparent;
                padding: 2px 6px;
                border-radius: 4px;
            """)

        self.channel_label.setText(channel)
        self.time_label.setText(time)

        if urgent and time != "--":
            self.time_label.setStyleSheet("""
                color: #6EE7B7;
                background: rgba(16, 185, 129, 0.15);
                padding: 2px 6px;
                border-radius: 5px;
                border: 1px solid rgba(16, 185, 129, 0.35);
                font-weight: 800;
            """)
        elif expired and time != "--":
            self.time_label.setStyleSheet("""
                color: #334155;
                background: transparent;
                font-weight: 500;
            """)
        else:
            self.time_label.setStyleSheet("""
                color: #22D3EE;
                background: transparent;
                font-weight: 700;
            """)

        self.set_update_date(update_date)
        self.rating_widget.set_boss_info(name, channel)

        if note is not None and note != "" and note != "--":
            try:
                rating = int(note)
                rating = max(0, min(5, rating))
            except ValueError:
                rating = 0
        else:
            if status == "N":
                rating = 0
            else:
                rating = self.rating_widget.get_rating()
        self.rating_widget.set_rating(rating)

        if boss_type and boss_type != "--":
            self.boss_status_label.setToolTip(f"Type: {boss_type}")

        self.boss_status_label.setText(status)
        self.set_status_accent(status)

        if status == "N":
            self.boss_status_label.setStyleSheet("""
                color: #A5B4FC;
                background: rgba(99, 102, 241, 0.18);
                padding: 2px 10px;
                border-radius: 10px;
                border: 1px solid rgba(99, 102, 241, 0.35);
                font-weight: 700;
            """)
        elif status.startswith("LV"):
            self.boss_status_label.setStyleSheet("""
                color: #93C5FD;
                background: rgba(59, 130, 246, 0.18);
                padding: 2px 10px;
                border-radius: 10px;
                border: 1px solid rgba(59, 130, 246, 0.35);
                font-weight: 700;
            """)
        elif status == "Active":
            self.boss_status_label.setStyleSheet("""
                color: #6EE7B7;
                background: rgba(16, 185, 129, 0.18);
                padding: 2px 10px;
                border-radius: 10px;
                border: 1px solid rgba(16, 185, 129, 0.35);
                font-weight: 700;
            """)
        else:
            self.boss_status_label.setStyleSheet("""
                color: #475569;
                background: rgba(255, 255, 255, 0.03);
                padding: 2px 10px;
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.06);
                font-weight: 600;
            """)

    def set_update_date(self, update_date: str, minutes_elapsed: int = None, last_updated_dt: Optional[datetime] = None):
        if last_updated_dt is not None:
            self._last_updated_dt = last_updated_dt
            self.update_elapsed_display()
            return

        self.update_date_label.setText(update_date)

        if update_date == "--" or update_date == "":
            self.update_date_label.setStyleSheet("color: #1E293B; background: transparent;")
            return

        if minutes_elapsed is not None:
            if minutes_elapsed <= 5:
                color = "#22D3EE"
            elif minutes_elapsed <= 10:
                color = "#818CF8"
            elif minutes_elapsed <= 15:
                color = "#FCD34D"
            elif minutes_elapsed <= 20:
                color = "#FB923C"
            elif minutes_elapsed > 30:
                color = "#F87171"
            else:
                color = "#475569"
        else:
            color = "#334155"

        self.update_date_label.setStyleSheet(f"color: {color}; background: transparent; font-weight: 600;")

    def update_elapsed_display(self) -> None:
        """Recalculate and refresh elapsed time label from stored last-updated datetime."""
        if self._last_updated_dt is None:
            return
        try:
            now = datetime.now()
            dt = self._last_updated_dt
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            elapsed_secs = max(0, int((now - dt).total_seconds()))

            if elapsed_secs < 60:
                text = "< 1m"
            elif elapsed_secs < 3600:
                text = f"{elapsed_secs // 60}m ago"
            elif elapsed_secs < 86400:
                h = elapsed_secs // 3600
                m = (elapsed_secs % 3600) // 60
                text = f"{h}h {m}m" if m else f"{h}h ago"
            else:
                text = "1d+"

            mins = elapsed_secs // 60
            if mins <= 5:
                color = "#22D3EE"
            elif mins <= 10:
                color = "#818CF8"
            elif mins <= 15:
                color = "#FCD34D"
            elif mins <= 20:
                color = "#FB923C"
            elif mins > 30:
                color = "#F87171"
            else:
                color = "#475569"

            self.update_date_label.setText(text)
            self.update_date_label.setStyleSheet(
                f"color: {color}; background: transparent; font-weight: 600;"
            )
        except Exception:
            pass

    def update_time(self, time_display: str) -> None:
        self.time_label.setText(time_display)

    def set_status_accent(self, status: str) -> None:
        self._current_status = status
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        status = self._current_status
        if status == 'Active':
            accent = QColor(34, 197, 94, 220)
        elif status.startswith('LV'):
            accent = QColor(251, 191, 36, 200)
        elif status == 'N':
            accent = QColor(99, 102, 241, 180)
        else:
            return
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(accent)
            painter.drawRoundedRect(2, 2, 3, self.height() - 4, 2, 2)
        finally:
            painter.end()
