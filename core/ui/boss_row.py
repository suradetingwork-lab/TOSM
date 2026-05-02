"""Boss row widget — single entry in the boss tracking table."""

from datetime import datetime
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from .widgets import StarRatingWidget
from .map_widgets import MapImagePopup
from .timeline_widget import (
    TimelineRowModel, 
    _try_parse_dt, 
    _status_to_current_phase, 
    _extract_phase_times_current_cycle,
    _norm_boss_name,
    _norm_channel,
    build_timeline_model
)
import json
import os

class BossRow(QFrame):
    """Single row displaying boss information."""

    delete_clicked = pyqtSignal(str, str)
    rating_changed = pyqtSignal(str, str, int)

    _ROW_DEFAULT = """
        QFrame {
            background: rgba(253, 250, 246, 0.85);
            border: 1px solid rgba(54, 104, 141, 0.12);
            border-radius: 8px;
        }
        QFrame:hover {
            background: rgba(54, 104, 141, 0.06);
            border: 1px solid rgba(54, 104, 141, 0.28);
        }
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._boss_name = ""
        self._channel = ""
        self._boss_key = ""
        self._current_status = "N"
        self._last_updated_dt: Optional[datetime] = None
        self._raw_boss_data = {}
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(self._ROW_DEFAULT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(4)

        # Boss Name
        self.name_label = QLabel("")
        self.name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.name_label.setStyleSheet("color: #1A2A38; background: transparent;")
        self.name_label.setFixedWidth(140)
        layout.addWidget(self.name_label)

        # Map label
        self.map_label = QLabel("")
        self.map_label.setFont(QFont("Segoe UI", 9))
        self.map_label.setStyleSheet("color: #64748B; background: transparent;")
        self.map_label.setFixedWidth(140)
        layout.addWidget(self.map_label)
        
        self._popup = MapImagePopup(self)
        self._popup.hide()

        # LV Badge
        self.lv_label = QLabel("")
        self.lv_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lv_label.setStyleSheet("""
            color: #8A7A68;
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
            color: #5A6A78;
            background: rgba(54, 104, 141, 0.08);
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid rgba(54, 104, 141, 0.20);
        """)
        self.channel_label.setFixedWidth(50)
        self.channel_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.channel_label)

        # Status Badge
        self.boss_status_label = QLabel("")
        self.boss_status_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.boss_status_label.setStyleSheet("""
            color: #8A7A68;
            background: rgba(54, 104, 141, 0.06);
            padding: 2px 8px;
            border-radius: 10px;
            border: 1px solid rgba(54, 104, 141, 0.15);
        """)
        self.boss_status_label.setFixedWidth(55)
        self.boss_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.boss_status_label)

        # Time
        self.time_label = QLabel("")
        self.time_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.time_label.setStyleSheet("color: #8A7A68; background: transparent;")
        self.time_label.setFixedWidth(55)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.time_label)

        # Update Date
        self.update_date_label = QLabel("")
        self.update_date_label.setFont(QFont("Segoe UI", 9))
        self.update_date_label.setStyleSheet("color: #A89880; background: transparent;")
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
                color: #BDA589;
                background: transparent;
                border: 1px solid rgba(189, 165, 137, 0.25);
                border-radius: 5px;
                padding: 0px;
            }
            QPushButton:hover {
                color: #F18904;
                background: rgba(241, 137, 4, 0.10);
                border: 1px solid rgba(241, 137, 4, 0.40);
            }
            QPushButton:pressed {
                background: rgba(241, 137, 4, 0.20);
            }
        """)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        layout.addWidget(self.delete_btn)

    def _on_rating_changed(self, boss_name: str, channel: str, rating: int):
        self.rating_changed.emit(boss_name, channel, rating)

    def _on_delete_clicked(self):
        self.delete_clicked.emit(self._boss_name, self._channel)

    def set_raw_boss(self, boss_data: dict):
        self._raw_boss_data = boss_data

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
        
        self._map_name = map_name if map_name and map_name != "--" else ""
        self._map_lv = map_lv
        self._boss_urgent = urgent
        
        self.map_label.setText(self._map_name[:30] if self._map_name else "")
        self.map_label.setToolTip(self._map_name if self._map_name else "")

        if map_lv:
            self.lv_label.setText(map_lv)
            self.lv_label.setStyleSheet("""
                color: #1A5A80;
                background: rgba(54, 104, 141, 0.14);
                padding: 2px 6px;
                border-radius: 4px;
                border: 1px solid rgba(54, 104, 141, 0.35);
                font-weight: 700;
            """)
        else:
            self.lv_label.setText("")
            self.lv_label.setStyleSheet("""
                color: #A89880;
                background: transparent;
                padding: 2px 6px;
                border-radius: 4px;
            """)

        self.channel_label.setText(channel)
        self.time_label.setText(time)

        if urgent and time != "--":
            self.time_label.setStyleSheet("""
                color: #B8860B;
                background: rgba(243, 205, 5, 0.18);
                padding: 2px 6px;
                border-radius: 5px;
                border: 1px solid rgba(243, 205, 5, 0.50);
                font-weight: 800;
            """)
        elif expired and time != "--":
            self.time_label.setStyleSheet("""
                color: #C0B0A0;
                background: transparent;
                font-weight: 500;
            """)
        else:
            self.time_label.setStyleSheet("""
                color: #D4860A;
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
                color: #1A5A80;
                background: rgba(54, 104, 141, 0.14);
                padding: 2px 10px;
                border-radius: 10px;
                border: 1px solid rgba(54, 104, 141, 0.35);
                font-weight: 700;
            """)
        elif status.startswith("LV"):
            self.boss_status_label.setStyleSheet("""
                color: #8B5E00;
                background: rgba(244, 159, 5, 0.15);
                padding: 2px 10px;
                border-radius: 10px;
                border: 1px solid rgba(244, 159, 5, 0.40);
                font-weight: 700;
            """)
        elif status == "Active":
            self.boss_status_label.setStyleSheet("""
                color: #16653A;
                background: rgba(16, 185, 129, 0.14);
                padding: 2px 10px;
                border-radius: 10px;
                border: 1px solid rgba(16, 185, 129, 0.35);
                font-weight: 700;
            """)
        else:
            self.boss_status_label.setStyleSheet("""
                color: #A89880;
                background: rgba(189, 165, 137, 0.10);
                padding: 2px 10px;
                border-radius: 10px;
                border: 1px solid rgba(189, 165, 137, 0.20);
                font-weight: 600;
            """)

    def set_update_date(self, update_date: str, minutes_elapsed: int = None, last_updated_dt: Optional[datetime] = None):
        self._last_updated_dt = last_updated_dt
        if last_updated_dt is not None:
            self.update_elapsed_display()
            return

        self.update_date_label.setText(update_date)

        if update_date in ("--", "", "-"):
            self.update_date_label.setStyleSheet("color: #D0C0B0; background: transparent;")
            return

        if minutes_elapsed is not None:
            if minutes_elapsed <= 5:
                color = "#1A5A80"
            elif minutes_elapsed <= 10:
                color = "#B8860B"
            elif minutes_elapsed <= 15:
                color = "#D4860A"
            elif minutes_elapsed <= 20:
                color = "#C07010"
            elif minutes_elapsed > 30:
                color = "#A89880"
            else:
                color = "#8A7A68"
        else:
            color = "#BDA589"

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
                color = "#1A5A80"
            elif mins <= 10:
                color = "#B8860B"
            elif mins <= 15:
                color = "#D4860A"
            elif mins <= 20:
                color = "#C07010"
            elif mins > 30:
                color = "#A89880"
            else:
                color = "#8A7A68"

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
            accent = QColor(22, 101, 58, 200)
        elif status.startswith('LV'):
            accent = QColor(212, 134, 10, 200)
        elif status == 'N':
            accent = QColor(54, 104, 141, 180)
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

    def enterEvent(self, event):
        super().enterEvent(event)
        if not hasattr(self, '_map_name') or not self._map_name:
            return

        self._popup.set_map_data(self._map_name, self._map_lv, self._boss_urgent, self._boss_name)

        # Build timeline model if we have raw data
        if self._raw_boss_data:
            name = self._boss_name
            channel = self._channel
            status = self._current_status
            boss_type = self._raw_boss_data.get("type", "")
            map_name = self._map_name
            spawn_time = _try_parse_dt(self._raw_boss_data.get("spawn_time"))
            current_phase = _status_to_current_phase(status)
            
            # Replicate TimelineView's robust lookup
            norm_name = _norm_boss_name(name)
            norm_ch = _norm_channel(channel)
            record = None
            try:
                root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                persistent_path = os.path.join(root_dir, "boss_data.json")
                if os.path.exists(persistent_path):
                    with open(persistent_path, "r", encoding="utf-8") as f:
                        persistent = json.load(f)
                        for r in persistent.values():
                            if _norm_boss_name(r.get("name", "")) == norm_name and \
                               _norm_channel(r.get("channel", "")) == norm_ch:
                                record = r
                                break
            except Exception:
                pass

            model = build_timeline_model(self._raw_boss_data, record, datetime.now())
            self._popup.set_timeline_model(model)
        else:
            self._popup.set_timeline_model(None)

        popup_pos = self.mapToGlobal(QPoint(0, 0))
        popup_pos.setY(popup_pos.y() - self._popup.height() - 8)
        self._popup.show_at(popup_pos)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._popup.hide()
