"""UI module for the transparent always-on-top overlay."""

import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint, QEvent, QRect, QPropertyAnimation, QEasingCurve, QAbstractAnimation
from PyQt6.QtGui import QColor, QFont, QMouseEvent, QIcon, QCursor, QPainter, QPixmap, QImage, QFontMetrics
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QPushButton,
    QSizeGrip,
    QLineEdit,
    QSlider,
    QGraphicsDropShadowEffect
)
import winsound  # For Windows sound notifications
from .map_level import get_map_level, get_boss_info, get_map_coordinates


class SortableHeaderButton(QPushButton):
    """Clickable header button with sort indicator."""

    clicked = pyqtSignal(str)

    def __init__(self, text: str, width: int, align_right: bool = False, parent=None):
        super().__init__(text, parent)
        self._column = text.lower()
        self._sort_direction = None
        self._width = width
        self._align_right = align_right

        self.setFixedWidth(width)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self._update_style()

    def _update_style(self):
        arrow = ""
        if self._sort_direction == 'asc':
            arrow = " ▲"
        elif self._sort_direction == 'desc':
            arrow = " ▼"

        self.setText(self._column.upper() + arrow)
        text_align = "right" if self._align_right else "center"

        if self._sort_direction is not None:
            self.setStyleSheet(f"""
                QPushButton {{
                    color: #C7D2FE;
                    background: rgba(99, 102, 241, 0.2);
                    border: 1px solid rgba(99, 102, 241, 0.45);
                    border-radius: 5px;
                    padding: 3px 8px;
                    font-weight: 700;
                    letter-spacing: 0.5px;
                    text-align: {text_align};
                }}
                QPushButton:hover {{
                    background: rgba(99, 102, 241, 0.35);
                    border: 1px solid rgba(99, 102, 241, 0.65);
                    color: #E0E7FF;
                }}
                QPushButton:pressed {{
                    background: rgba(99, 102, 241, 0.5);
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    color: #64748B;
                    background: transparent;
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 5px;
                    padding: 3px 8px;
                    font-weight: 600;
                    letter-spacing: 0.5px;
                    text-align: {text_align};
                }}
                QPushButton:hover {{
                    color: #94A3B8;
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.12);
                }}
                QPushButton:pressed {{
                    background: rgba(255, 255, 255, 0.08);
                }}
            """)

    def set_sort_direction(self, direction: str):
        self._sort_direction = direction
        self._update_style()

    def clear_sort(self):
        self._sort_direction = None
        self._update_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._column)
        super().mousePressEvent(event)


class StarRatingWidget(QWidget):
    """Custom 1-5 star rating widget with radio button behavior."""

    rating_changed = pyqtSignal(str, str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rating = 0
        self._boss_name = ""
        self._channel = ""
        self._star_buttons = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        for i in range(1, 6):
            star_btn = QPushButton("☆")
            star_btn.setFixedSize(18, 18)
            star_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            star_btn.setFont(QFont("Segoe UI", 10))
            star_btn.setProperty("star_value", i)
            star_btn.setStyleSheet("""
                QPushButton {
                    color: #334155;
                    background: transparent;
                    border: none;
                    padding: 0px;
                }
                QPushButton:hover {
                    color: #FCD34D;
                }
            """)
            star_btn.clicked.connect(self._on_star_clicked)
            self._star_buttons.append(star_btn)
            layout.addWidget(star_btn)

        self.setFixedWidth(100)
        self._update_display()

    def _on_star_clicked(self):
        sender = self.sender()
        if sender:
            new_rating = sender.property("star_value")
            self._rating = 0 if self._rating == new_rating else new_rating
            self._update_display()
            if self._boss_name:
                self.rating_changed.emit(self._boss_name, self._channel, self._rating)

    def _update_display(self):
        for i, btn in enumerate(self._star_buttons, 1):
            if i <= self._rating:
                btn.setText("★")
                btn.setStyleSheet("""
                    QPushButton {
                        color: #FCD34D;
                        background: transparent;
                        border: none;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        color: #FDE68A;
                    }
                """)
            else:
                btn.setText("☆")
                btn.setStyleSheet("""
                    QPushButton {
                        color: #334155;
                        background: transparent;
                        border: none;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        color: #FCD34D;
                    }
                """)

    def set_rating(self, rating: int):
        self._rating = max(0, min(5, rating))
        self._update_display()

    def get_rating(self) -> int:
        return self._rating

    def set_boss_info(self, boss_name: str, channel: str):
        self._boss_name = boss_name
        self._channel = channel

    def clear_rating(self):
        self.set_rating(0)


class MapImageWidget(QWidget):
    """Widget displaying a boss image."""

    def __init__(self, map_name: str, boss_name: str = "", parent=None):
        super().__init__(parent)
        self._map_name = map_name
        self._boss_name = boss_name
        self._pixmap: Optional[QPixmap] = None
        self._boss_spawn_color = QColor("#64748B")  # Default gray
        self._max_width = 600
        self._max_height = 300

        self._load_image()
        self._update_size()

    def _load_image(self):
        """Load boss image from data/pics/boss/{boss_name}.png"""
        if self._boss_name:
            image_path = os.path.join("data", "pics", "boss", f"{self._boss_name}.png")
            if os.path.exists(image_path):
                self._pixmap = QPixmap(image_path)
                return

        # Fallback to map image if boss image not found
        if self._map_name:
            image_path = os.path.join("data", "pics", "map", f"{self._map_name}.png")
            if os.path.exists(image_path):
                self._pixmap = QPixmap(image_path)
                return

        self._pixmap = None

    def _update_size(self):
        """Set widget size based on scaled image dimensions."""
        if self._pixmap and not self._pixmap.isNull():
            # Calculate scaled size maintaining aspect ratio
            img_width = self._pixmap.width()
            img_height = self._pixmap.height()

            scale = min(self._max_width / img_width, self._max_height / img_height, 1.0)

            self._scaled_width = int(img_width * scale)
            self._scaled_height = int(img_height * scale)
        else:
            # Default size when no image
            self._scaled_width = 220
            self._scaled_height = 220

        self.setFixedSize(self._scaled_width, self._scaled_height)
        self.update()  # Force repaint

    def set_map_name(self, map_name: str, boss_name: str = ""):
        """Set map name and reload image."""
        self._map_name = map_name
        self._boss_name = boss_name
        self._load_image()
        self._update_size()

    def set_boss_spawn_color(self, color: QColor):
        """Set the color for boss spawn marker (green/red/gray)."""
        self._boss_spawn_color = color
        self.update()

    def paintEvent(self, event):
        """Paint the map image and overlay markers."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Get coordinates
        coords = get_map_coordinates(self._map_name)
        if not coords:
            # Draw "Map unavailable" text
            painter.setPen(QColor("#94A3B8"))
            painter.setFont(QFont("Segoe UI", 10))
            text = "Map unavailable"
            fm = QFontMetrics(painter.font())
            text_width = fm.horizontalAdvance(text)
            x = (self.width() - text_width) // 2
            y = self.height() // 2
            painter.drawText(x, y, text)
            return

        # Draw image if available
        if self._pixmap and not self._pixmap.isNull():
            scaled_pixmap = self._pixmap.scaled(
                self._scaled_width,
                self._scaled_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            # Center the image
            x_offset = (self.width() - scaled_pixmap.width()) // 2
            y_offset = (self.height() - scaled_pixmap.height()) // 2
            painter.drawPixmap(x_offset, y_offset, scaled_pixmap)

            # Calculate actual image rect for positioning
            img_rect = scaled_pixmap.rect()
            img_rect.moveCenter(self.rect().center())
        else:
            # Draw placeholder background
            painter.fillRect(self.rect(), QColor("#1E293B"))


class MapImagePopup(QWidget):
    """Popup window showing map image with markers."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._map_name = ""
        self._map_lv = ""
        self._boss_name = ""

        # Main layout
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(8)

        # Container frame with styling
        self._container = QFrame(self)
        self._container.setStyleSheet("""
            QFrame {
                background: rgba(15, 23, 42, 0.98);
                border: 1px solid rgba(99, 102, 241, 0.4);
                border-radius: 10px;
            }
        """)
        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(12, 12, 12, 12)
        container_layout.setSpacing(8)

        # Header: icon + map name + level
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)

        self._icon_label = QLabel("🗺")
        self._icon_label.setFont(QFont("Segoe UI", 11))
        header_layout.addWidget(self._icon_label)

        self._name_label = QLabel("")
        self._name_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self._name_label.setStyleSheet("color: #E2E8F0;")
        header_layout.addWidget(self._name_label)

        self._level_label = QLabel("")
        self._level_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self._level_label.setStyleSheet("""
            color: #A5B4FC;
            background: rgba(99, 102, 241, 0.18);
            padding: 2px 8px;
            border-radius: 4px;
            border: 1px solid rgba(99, 102, 241, 0.35);
        """)
        header_layout.addWidget(self._level_label)
        header_layout.addStretch()
        container_layout.addLayout(header_layout)

        # Images layout - Boss and Map side by side
        images_layout = QHBoxLayout()
        images_layout.setSpacing(12)

        # Boss image section
        self._boss_section = QVBoxLayout()
        self._boss_section.setSpacing(4)
        boss_label = QLabel("👹 Boss")
        boss_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        boss_label.setStyleSheet("color: #94A3B8;")
        boss_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._boss_section.addWidget(boss_label)

        self._boss_image_widget = QLabel("No image")
        self._boss_image_widget.setFixedSize(220, 220)
        self._boss_image_widget.setStyleSheet("""
            QLabel {
                background: #1E293B;
                border: 1px solid rgba(99, 102, 241, 0.3);
                border-radius: 6px;
                color: #64748B;
            }
        """)
        self._boss_image_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._boss_section.addWidget(self._boss_image_widget)
        images_layout.addLayout(self._boss_section)

        # Map image section
        self._map_section = QVBoxLayout()
        self._map_section.setSpacing(4)
        map_label = QLabel("🗺 Map")
        map_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        map_label.setStyleSheet("color: #94A3B8;")
        map_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._map_section.addWidget(map_label)

        self._map_image_widget = MapImageWidget("", "", self._container)
        self._map_image_widget.setFixedSize(220, 220)
        self._map_section.addWidget(self._map_image_widget)
        images_layout.addLayout(self._map_section)

        container_layout.addLayout(images_layout)

        self._layout.addWidget(self._container)

    def set_map_data(self, map_name: str, map_lv: str, boss_urgent: bool = False, boss_name: str = ""):
        """Set map data and update display."""
        self._map_name = map_name
        self._map_lv = map_lv
        self._boss_name = boss_name

        self._name_label.setText(map_name if map_name else "Unknown")
        self._level_label.setText(f"LV {map_lv}" if map_lv else "")
        self._level_label.setVisible(bool(map_lv))

        # Load boss image
        if boss_name:
            boss_image_path = os.path.join("data", "pics", "boss", f"{boss_name}.png")
            if os.path.exists(boss_image_path):
                pixmap = QPixmap(boss_image_path)
                scaled = pixmap.scaled(220, 220, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self._boss_image_widget.setPixmap(scaled)
                self._boss_image_widget.setText("")
            else:
                self._boss_image_widget.setPixmap(QPixmap())
                self._boss_image_widget.setText("No image")
        else:
            self._boss_image_widget.setPixmap(QPixmap())
            self._boss_image_widget.setText("No image")

        # Update map widget using set_map_name to reload image
        self._map_image_widget.set_map_name(map_name, "")
        self._map_image_widget.setFixedSize(220, 220)

        # Set boss spawn color based on status
        if boss_urgent:
            color = QColor("#22C55E")  # Green - respawning soon
        else:
            color = QColor("#EF4444")  # Red - available

        # Check if we have spawn data
        coords = get_map_coordinates(map_name)
        if not coords:
            color = QColor("#64748B")  # Gray - no data

        self._map_image_widget.set_boss_spawn_color(color)

        self.adjustSize()

    def show_at(self, pos: QPoint):
        """Show popup at specified position."""
        self.move(pos)
        self.show()


class MapIconLabel(QWidget):
    """Label with map icon that shows map popup on hover."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._map_name = ""
        self._map_lv = ""
        self._boss_name = ""
        self._boss_urgent = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Map icon (hidden by default, shown when map available)
        self._icon_label = QLabel("🗺")
        self._icon_label.setFont(QFont("Segoe UI", 9))
        self._icon_label.setStyleSheet("color: #64748B;")
        self._icon_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self._icon_label.hide()
        layout.addWidget(self._icon_label)

        # Text label
        self._text_label = QLabel("")
        self._text_label.setFont(QFont("Segoe UI", 9))
        self._text_label.setStyleSheet("color: #64748B; background: transparent;")
        self._text_label.setFixedWidth(140)
        layout.addWidget(self._text_label)

        # Popup
        self._popup = MapImagePopup(self)
        self._popup.hide()

        # Track mouse for popup positioning
        self.setMouseTracking(True)

    def set_map_data(self, map_name: str, map_lv: str, boss_urgent: bool = False, boss_name: str = ""):
        """Set map data and update display."""
        self._map_name = map_name
        self._map_lv = map_lv
        self._boss_name = boss_name
        self._boss_urgent = boss_urgent

        # Show icon for any valid map name
        has_map = map_name and map_name != "--"

        self._text_label.setText(map_name[:30] if has_map else "")
        self._text_label.setToolTip(map_name if has_map else "")

        if has_map:
            self._icon_label.show()
        else:
            self._icon_label.hide()

    def enterEvent(self, event):
        """Show popup on hover."""
        if not self._map_name or self._map_name == "--":
            return

        # Update popup data
        self._popup.set_map_data(self._map_name, self._map_lv, self._boss_urgent, self._boss_name)

        # Calculate position above the label
        popup_pos = self.mapToGlobal(QPoint(0, 0))
        popup_pos.setY(popup_pos.y() - self._popup.height() - 8)
        popup_pos.setX(popup_pos.x())

        self._popup.show_at(popup_pos)

    def leaveEvent(self, event):
        """Hide popup when leaving."""
        self._popup.hide()


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
                text = f"{elapsed_secs // 60}m"
            elif elapsed_secs < 86400:
                h = elapsed_secs // 3600
                m = (elapsed_secs % 3600) // 60
                text = f"{h}h{m:02d}m"
            else:
                d = elapsed_secs // 86400
                text = f"{d}d"

            self.update_date_label.setText(text)

            minutes = elapsed_secs // 60
            if minutes <= 5:
                color = "#22D3EE"
            elif minutes <= 10:
                color = "#818CF8"
            elif minutes <= 15:
                color = "#FCD34D"
            elif minutes <= 20:
                color = "#FB923C"
            elif minutes > 30:
                color = "#F87171"
            else:
                color = "#475569"

            self.update_date_label.setStyleSheet(f"color: {color}; background: transparent; font-weight: 600;")
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


class SummaryStatsBar(QWidget):
    """Three metric cards shown above the boss table: Active | Upcoming ≤5m | Total Tracked."""

    def __init__(self, data_path: str, parent=None):
        super().__init__(parent)
        self._data_path = data_path

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        self._cards: Dict[str, QLabel] = {}
        for key, label, color in [
            ("coming",   "Coming",   "#22C55E"),
            ("upcoming", "Upcoming", "#FCD34D"),
        ]:
            frame = QFrame()
            frame.setStyleSheet(f"""
                QFrame {{
                    background: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-left: 3px solid {color};
                    border-radius: 6px;
                }}
            """)
            fl = QHBoxLayout(frame)
            fl.setContentsMargins(10, 4, 10, 4)
            fl.setSpacing(6)

            val_lbl = QLabel("0")
            val_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            val_lbl.setStyleSheet(f"color: {color}; background: transparent; border: none;")

            txt_lbl = QLabel(label)
            txt_lbl.setFont(QFont("Segoe UI", 8))
            txt_lbl.setStyleSheet("color: #475569; background: transparent; border: none;")

            fl.addWidget(val_lbl)
            fl.addWidget(txt_lbl)
            fl.addStretch()

            self._cards[key] = val_lbl
            layout.addWidget(frame)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(60000)
        self.refresh()

    def refresh(self):
        try:
            with open(self._data_path, 'r', encoding='utf-8') as f:
                raw = json.load(f)
        except Exception:
            return

        now = datetime.now()
        coming = 0
        upcoming = 0

        for key, entry in raw.items():
            for loc in entry.get('locations', {}).values():
                history = loc.get('spawn_history', [])
                if not history:
                    continue
                spawn_str = history[-1].get('spawn_time')
                if not spawn_str:
                    continue
                try:
                    spawn_dt = datetime.fromisoformat(spawn_str)
                    if spawn_dt > now:
                        coming += 1
                    elif spawn_dt < now:
                        upcoming += 1
                except (ValueError, TypeError):
                    pass

        self._cards['coming'].setText(str(coming))
        self._cards['upcoming'].setText(str(upcoming))


class OverlayWindow(QMainWindow):
    """Transparent, always-on-top, click-through overlay window."""

    data_updated = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._close_callback: Optional[Callable[[], None]] = None
        self._drag_pos: Optional[QPoint] = None
        self._alt_pressed = False

        self._is_locked = False
        self._base_opacity = 0.95

        self._edge_size = 8
        self._resize_edges = 0
        self._resizing = False
        self._window_dragging = False

        self.scroll_area = None

        self._sort_column = "status"
        self._sort_direction = "asc"
        self._header_buttons = {}

        self._active_tabs: set = {"all"}
        self._tab_buttons: Dict[str, QPushButton] = {}
        self._search_filter = ""

        self._is_expanded = False
        self._collapsed_height = 350
        self._expanded_height = 700
        self._expand_timer = QTimer()
        self._expand_timer.timeout.connect(self._expand_window)
        self._expand_timer.setSingleShot(True)
        self._collapse_timer = QTimer()
        self._collapse_timer.timeout.connect(self._collapse_window)
        self._collapse_timer.setSingleShot(True)
        self._expand_delay = 200
        self._collapse_delay = 200

        self._geom_anim = QPropertyAnimation(self, b"geometry")
        self._geom_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._geom_anim.setDuration(150)
        self._geom_anim.stateChanged.connect(self._on_geom_anim_state_changed)

        self._opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._opacity_anim.setDuration(200)

        self._stats_window = None
        self._boss_data_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'boss_data.json'
        )

        self._init_ui()
        self._setup_window_properties()
        self.data_updated.connect(self._on_data_updated)

        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._refresh_countdowns)
        self._update_timer.start(1000)

        self._auto_sort_timer = QTimer()
        self._auto_sort_timer.timeout.connect(self._auto_sort_bosses)
        self._auto_sort_timer.start(60000)

        self._elapsed_timer = QTimer()
        self._elapsed_timer.timeout.connect(self._refresh_elapsed_times)
        self._elapsed_timer.start(1000)

        self._search_debounce = QTimer()
        self._search_debounce.setSingleShot(True)
        self._search_debounce.setInterval(300)
        self._search_debounce.timeout.connect(self._apply_search_filter)

        self._boss_data: List[Dict[str, Any]] = []
        self._reset_boss_data()
        self.resize(820, self._collapsed_height)
        self._urgent_notified = set()

    def _on_geom_anim_state_changed(self, new_state, old_state):
        effect = self.central_widget.graphicsEffect()
        if effect:
            if new_state == QAbstractAnimation.State.Running:
                effect.setEnabled(False)
            elif new_state == QAbstractAnimation.State.Stopped:
                effect.setEnabled(True)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, 'size_grip') and self.size_grip:
            self.size_grip.move(self.width() - 16, self.height() - 16)

    def _play_notification_sound(self) -> None:
        try:
            winsound.Beep(800, 200)
        except Exception as e:
            print(f"[UI] Could not play notification sound: {e}")

    def _on_header_clicked(self, column: str) -> None:
        if column not in ["lv", "ch", "status", "spawn", "scanned"]:
            return

        if self._sort_column == column:
            self._sort_direction = "desc" if self._sort_direction == "asc" else "asc"
        else:
            self._sort_column = column
            self._sort_direction = "asc"

        for col_name, button in self._header_buttons.items():
            if col_name == column:
                button.set_sort_direction(self._sort_direction)
            else:
                button.clear_sort()

        sorted_bosses = self._sort_bosses(self._boss_data)
        self._update_display(sorted_bosses)

    def _on_tab_clicked(self, tab_key: str) -> None:
        if tab_key == "all":
            self._active_tabs = {"all"}
        else:
            if "all" in self._active_tabs:
                self._active_tabs.discard("all")
            if tab_key in self._active_tabs:
                self._active_tabs.discard(tab_key)
            else:
                self._active_tabs.add(tab_key)
            if not self._active_tabs:
                self._active_tabs = {"all"}
        self._update_tab_styles()
        sorted_bosses = self._sort_bosses(self._boss_data)
        self._update_display(sorted_bosses)

    def _update_tab_styles(self) -> None:
        active_style = """
            QPushButton {
                color: #C7D2FE;
                background: rgba(99, 102, 241, 0.25);
                border: 1px solid rgba(99, 102, 241, 0.45);
                border-radius: 12px;
                padding: 3px 14px;
                font-weight: 700;
            }
        """
        inactive_style = """
            QPushButton {
                color: #475569;
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 12px;
                padding: 3px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                color: #94A3B8;
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.12);
            }
        """
        for key, btn in self._tab_buttons.items():
            if key in self._active_tabs:
                btn.setStyleSheet(active_style)
            else:
                btn.setStyleSheet(inactive_style)

    def _filter_by_tab(self, bosses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if "all" in self._active_tabs:
            return bosses

        tab_ranges = {
            "#2": (12, 19),
            "#3": (22, 28),
            "#4": (32, 38),
            "#5": (44, 48),
            "#6": (52, 59),
            "#7": (62, 68),
            "#8": (70, 74),
            "#9": (75, 79),
            "#10": (80, 83),
            "#11": (85, 89),
            "#12": (90, 93),
            "#13": (95, 103),
            "#14": (105, 113),
            "#15": (115, 123),
        }

        selected_ranges = [tab_ranges[k] for k in self._active_tabs if k in tab_ranges]
        if not selected_ranges:
            return bosses

        filtered = []
        for b in bosses:
            map_lv = b.get('map_lv', '')
            if not map_lv:
                _, lookup_lv, _ = get_boss_info(b.get('name', ''))
                map_lv = lookup_lv
            try:
                lv = int(map_lv)
                if any(lv_min <= lv <= lv_max for lv_min, lv_max in selected_ranges):
                    filtered.append(b)
            except (ValueError, TypeError):
                pass
        return filtered

    def _on_search_changed(self, text: str) -> None:
        """Handle search text changes with debounce."""
        self._search_filter = text.strip().lower()
        self._search_debounce.stop()
        self._search_debounce.start()

    def _apply_search_filter(self) -> None:
        """Apply search filter and refresh display."""
        sorted_bosses = self._sort_bosses(self._boss_data)
        self._update_display(sorted_bosses)

    def _filter_by_name(self, bosses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter bosses by fuzzy name search."""
        if not self._search_filter:
            return bosses
        q = self._search_filter
        filtered = []
        for b in bosses:
            name = b.get('name', '').lower()
            # Fuzzy match: any part of search query appears in name
            if q in name:
                filtered.append(b)
                continue
            # Also try matching each word in search query
            words = q.split()
            if all(word in name for word in words):
                filtered.append(b)
        return filtered

    def _load_initial_data(self) -> None:
        return

    def _load_ui_state(self) -> bool:
        try:
            state_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui_state.json")
            if os.path.exists(state_file):
                with open(state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                last_updated_str = state_data.get('last_updated', '')
                if last_updated_str:
                    try:
                        last_updated = datetime.fromisoformat(last_updated_str)
                        if datetime.now() - last_updated > timedelta(hours=24):
                            return False
                    except ValueError:
                        return False
                saved_bosses = state_data.get('bosses', [])
                self._boss_data = saved_bosses.copy()
                sorted_bosses = self._sort_bosses(self._boss_data)
                self._update_display(sorted_bosses)
                return True
            return False
        except Exception:
            return False

    def _save_ui_state(self) -> None:
        try:
            state_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui_state.json")
            state_data = {
                'last_updated': datetime.now().isoformat(),
                'bosses': []
            }
            for boss in self._boss_data:
                if (boss.get('channel', '-') != '-' or
                        boss.get('status', '-') != '-' or
                        boss.get('countdown', '') != '' or
                        boss.get('time_display', '') != ''):
                    state_data['bosses'].append({
                        'name': boss.get('name', ''),
                        'channel': boss.get('channel', '-'),
                        'status': boss.get('status', '-'),
                        'countdown': boss.get('countdown', ''),
                        'spawn_time': boss.get('spawn_time', ''),
                        'time_display': boss.get('time_display', ''),
                        'last_updated': boss.get('last_updated', ''),
                        'map': boss.get('map', ''),
                        'type': boss.get('type', ''),
                        'map_lv': boss.get('map_lv', ''),
                        'rating': boss.get('rating', 0)
                    })
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _setup_window_properties(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowMinMaxButtonsHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setWindowOpacity(self._base_opacity)

    def _init_ui(self) -> None:
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 4)
        self.central_widget.setGraphicsEffect(shadow)

        self.central_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0.2, y2: 1,
                    stop: 0 rgba(10, 12, 24, 0.97),
                    stop: 1 rgba(6, 8, 18, 0.98)
                );
                border-radius: 14px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
        """)

        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(14, 12, 14, 12)
        self.layout.setSpacing(6)

        # ── Summary stats bar ──────────────────────────────────────
        self._summary_bar = SummaryStatsBar(self._boss_data_path)

        # ── Column headers ─────────────────────────────────────────
        headers = QHBoxLayout()
        headers.setContentsMargins(8, 2, 8, 2)
        headers.setSpacing(4)

        headers_data = [
            ("Boss",    140, False),
            ("Map",     140, False),
            ("LV",       45, True),
            ("CH",       50, True),
            ("Status",   55, True),
            ("Spawn",    55, True),
            ("Scanned",  65, True),
            ("Rating",  100, False),
        ]

        for text, width, sortable in headers_data:
            if sortable:
                column_key = text.lower().replace(' ', '_')
                is_spawn = (text == "Spawn")
                header = SortableHeaderButton(text, width, align_right=is_spawn)
                header.clicked.connect(lambda column=column_key: self._on_header_clicked(column))
                self._header_buttons[column_key] = header
                if column_key == "status":
                    header.set_sort_direction("asc")
            else:
                header = QLabel(text)
                header.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                header.setStyleSheet("color: #334155; background: transparent; letter-spacing: 0.5px;")
            header.setFixedWidth(width)
            headers.addWidget(header)

        del_spacer = QLabel()
        del_spacer.setFixedWidth(24)
        headers.addWidget(del_spacer)

        # ── Boss rows ──────────────────────────────────────────────
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 4px 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(99, 102, 241, 0.35);
                border-radius: 3px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(99, 102, 241, 0.55);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self.rows_layout = QVBoxLayout(scroll_content)
        self.rows_layout.setSpacing(3)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)

        self.boss_rows: List[BossRow] = []
        for _ in range(72):
            row = BossRow()
            row.delete_clicked.connect(self._delete_boss_record)
            row.rating_changed.connect(self._on_rating_changed)
            self.boss_rows.append(row)
            self.rows_layout.addWidget(row)

        self.rows_layout.addStretch()
        self.scroll_area.setWidget(scroll_content)

        # ── Divider ────────────────────────────────────────────────
        div1 = QFrame()
        div1.setFrameShape(QFrame.Shape.HLine)
        div1.setFixedHeight(1)
        div1.setStyleSheet("background: rgba(255, 255, 255, 0.06); border: none;")

        # ── Tab bar ────────────────────────────────────────────────
        tab_container = QWidget()
        tab_container.setStyleSheet("background: transparent; border: none;")
        tab_layout = QHBoxLayout(tab_container)
        tab_layout.setContentsMargins(0, 2, 0, 2)
        tab_layout.setSpacing(6)
        tab_layout.addStretch()

        for tab_key, tab_label in [("all", "All"), ("#2", "#2"), ("#3", "#3"), ("#4", "#4"), ("#5", "#5"), ("#6", "#6"), ("#7", "#7"), ("#8", "#8"), ("#9", "#9"), ("#10", "#10"), ("#11", "#11"), ("#12", "#12"), ("#13", "#13")]:
            btn = QPushButton(tab_label)
            btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(26)
            if tab_key != "all":
                btn.setCheckable(True)
            btn.clicked.connect(lambda checked, key=tab_key: self._on_tab_clicked(key))
            self._tab_buttons[tab_key] = btn
            tab_layout.addWidget(btn)
        self._update_tab_styles()

        # ── Status bar ─────────────────────────────────────────────
        status_container = QWidget()
        status_container.setStyleSheet("""
            background: rgba(255, 255, 255, 0.03);
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.06);
        """)
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(10, 5, 10, 5)
        status_layout.setSpacing(8)

        self.status_label = QLabel("◎  Ready — Alt+1 to scan")
        self.status_label.setFont(QFont("Segoe UI", 9))
        self.status_label.setStyleSheet("color: #475569; background: transparent;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.setStyleSheet("""
            QPushButton {
                color: #64748B;
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 6px;
                padding: 4px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                color: #FDA4AF;
                background: rgba(244, 63, 94, 0.1);
                border: 1px solid rgba(244, 63, 94, 0.25);
            }
            QPushButton:pressed {
                background: rgba(244, 63, 94, 0.2);
            }
        """)
        self.reset_btn.clicked.connect(self._reset_boss_data)
        status_layout.addWidget(self.reset_btn)

        # ── Divider ────────────────────────────────────────────────
        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.HLine)
        div2.setFixedHeight(1)
        div2.setStyleSheet("background: rgba(255, 255, 255, 0.06); border: none;")

        # ── Title bar ──────────────────────────────────────────────
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(4, 2, 4, 2)
        header_layout.setSpacing(6)

        title_dot = QLabel("◆")
        title_dot.setFont(QFont("Segoe UI", 9))
        title_dot.setStyleSheet("color: #6366F1; background: transparent;")
        header_layout.addWidget(title_dot)

        self.title_label = QLabel("Boss Tracker")
        self.title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #94A3B8; background: transparent;")
        header_layout.addWidget(self.title_label)

        header_layout.addSpacing(12)

        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Filter...")
        self.search_box.setFont(QFont("Segoe UI", 9))
        self.search_box.setFixedWidth(140)
        self.search_box.setFixedHeight(24)
        self.search_box.setStyleSheet("""
            QLineEdit {
                color: #94A3B8;
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 2px 8px;
            }
            QLineEdit:focus {
                border: 1px solid rgba(99, 102, 241, 0.5);
                background: rgba(99, 102, 241, 0.07);
            }
        """)
        self.search_box.textChanged.connect(self._on_search_changed)
        header_layout.addWidget(self.search_box)

        header_layout.addStretch()

        # Opacity control
        opacity_label = QLabel("○")
        opacity_label.setFont(QFont("Segoe UI", 10))
        opacity_label.setStyleSheet("color: #334155; background: transparent;")
        header_layout.addWidget(opacity_label)

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(20, 100)
        self.opacity_slider.setValue(int(self._base_opacity * 100))
        self.opacity_slider.setFixedWidth(72)
        self.opacity_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border-radius: 2px;
                height: 3px;
                background: rgba(255, 255, 255, 0.1);
            }
            QSlider::handle:horizontal {
                background: #6366F1;
                width: 10px;
                height: 10px;
                margin: -4px 0;
                border-radius: 5px;
            }
            QSlider::sub-page:horizontal {
                background: rgba(99, 102, 241, 0.5);
                border-radius: 2px;
            }
        """)
        self.opacity_slider.valueChanged.connect(self._change_opacity)
        header_layout.addWidget(self.opacity_slider)

        # Lock button
        self.lock_btn = QPushButton("Auto")
        self.lock_btn.setFixedSize(52, 24)
        self.lock_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lock_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.lock_btn.setStyleSheet("""
            QPushButton {
                color: #475569;
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 6px;
            }
            QPushButton:hover {
                color: #94A3B8;
                background: rgba(255, 255, 255, 0.06);
            }
        """)
        self.lock_btn.clicked.connect(self._toggle_lock)
        header_layout.addWidget(self.lock_btn)

        # Stats popup
        self.stats_btn = QPushButton("📊")
        self.stats_btn.setFont(QFont("Segoe UI", 12))
        self.stats_btn.setFixedSize(28, 28)
        self.stats_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stats_btn.setToolTip("Boss Statistics")
        self.stats_btn.setStyleSheet("""
            QPushButton {
                color: #475569;
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 6px;
            }
            QPushButton:hover {
                color: #818CF8;
                background: rgba(99, 102, 241, 0.12);
                border: 1px solid rgba(99, 102, 241, 0.3);
            }
            QPushButton:pressed {
                background: rgba(99, 102, 241, 0.22);
            }
        """)
        self.stats_btn.clicked.connect(self._toggle_stats_window)
        header_layout.addWidget(self.stats_btn)

        # Minimize
        self.minimize_btn = QPushButton("−")
        self.minimize_btn.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.minimize_btn.setFixedSize(28, 28)
        self.minimize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.minimize_btn.setStyleSheet("""
            QPushButton {
                color: #475569;
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 6px;
            }
            QPushButton:hover {
                color: #94A3B8;
                background: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(255, 255, 255, 0.12);
            }
        """)
        self.minimize_btn.clicked.connect(self._minimize_window)
        header_layout.addWidget(self.minimize_btn)

        # Maximize
        self.maximize_btn = QPushButton("□")
        self.maximize_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.maximize_btn.setFixedSize(28, 28)
        self.maximize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.maximize_btn.setStyleSheet("""
            QPushButton {
                color: #475569;
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 6px;
            }
            QPushButton:hover {
                color: #94A3B8;
                background: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(255, 255, 255, 0.12);
            }
        """)
        self.maximize_btn.clicked.connect(self._maximize_window)
        header_layout.addWidget(self.maximize_btn)

        self.drag_hint = QLabel("Alt+Drag")
        self.drag_hint.setFont(QFont("Segoe UI", 8))
        self.drag_hint.setStyleSheet("color: #1E293B; background: transparent;")
        header_layout.addWidget(self.drag_hint)

        # ── Assemble layout ────────────────────────────────────────
        self.layout.addWidget(self._summary_bar)
        self.layout.addLayout(headers)
        self.layout.addWidget(self.scroll_area, 1)
        self.layout.addWidget(div1)
        self.layout.addWidget(tab_container)
        self.layout.addWidget(div2)
        self.layout.addLayout(header_layout)
        self.layout.addWidget(status_container)

        self.setMinimumSize(820, 286)

        self.size_grip = QSizeGrip(self)
        self.size_grip.setStyleSheet("""
            QSizeGrip {
                background: rgba(99, 102, 241, 0.2);
                border: 1px solid rgba(99, 102, 241, 0.3);
                width: 12px;
                height: 12px;
                border-radius: 3px;
            }
        """)
        self.size_grip.move(self.width() - 16, self.height() - 16)

    def _toggle_lock(self):
        self._is_locked = not self._is_locked
        if self._is_locked:
            self.lock_btn.setText("Lock")
            self.lock_btn.setStyleSheet("""
                QPushButton {
                    color: #A5B4FC;
                    background: rgba(99, 102, 241, 0.15);
                    border: 1px solid rgba(99, 102, 241, 0.35);
                    border-radius: 6px;
                    font-weight: 700;
                }
            """)
        else:
            self.lock_btn.setText("Auto")
            self.lock_btn.setStyleSheet("""
                QPushButton {
                    color: #475569;
                    background: transparent;
                    border: 1px solid rgba(255, 255, 255, 0.07);
                    border-radius: 6px;
                }
                QPushButton:hover {
                    color: #94A3B8;
                    background: rgba(255, 255, 255, 0.06);
                }
            """)

    def _toggle_stats_window(self) -> None:
        from .stats_window import StatsPopupWindow
        if self._stats_window is None:
            self._stats_window = StatsPopupWindow(self._boss_data_path, parent=None)
        if self._stats_window.isVisible():
            self._stats_window.hide()
        else:
            geo = self.geometry()
            self._stats_window.move(geo.x() + geo.width() + 12, geo.y())
            self._stats_window.show()
            self._stats_window.refresh()

    def _change_opacity(self, value):
        self._base_opacity = value / 100.0
        if not self.underMouse():
            self.setWindowOpacity(self._base_opacity)

    def show_snapshot_feedback(self) -> None:
        self.status_label.setText("◎  Scanning...")
        self.status_label.setStyleSheet("color: #FCD34D; background: transparent;")
        self.repaint()

    def update_status(self, message: str) -> None:
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: #818CF8; background: transparent;")

    def set_close_callback(self, callback: Callable[[], None]) -> None:
        self._close_callback = callback

    def update_data(self, data: Dict[str, Any]) -> None:
        self.data_updated.emit(data)

    def _on_data_updated(self, data: Dict[str, Any]) -> None:
        if "error" in data:
            self.status_label.setText(f"Error: {data['error']}")
            return

        bosses: List[Dict[str, Any]] = data.get("bosses", [])
        boss_dict = {}
        for b in self._boss_data:
            name = b.get('name', '').lower()
            channel = b.get('channel', '--')
            key = f"{name}_{channel}"
            boss_dict[key] = b

        for new_boss in bosses:
            name = new_boss.get('name', '').lower()
            channel = new_boss.get('channel', '--')
            if name:
                key = f"{name}_{channel}"

                countdown = new_boss.get('countdown', '')
                if countdown and countdown != '--':
                    try:
                        parts = countdown.split(':')
                        if len(parts) == 2:
                            minutes, seconds = map(int, parts)
                            delta = timedelta(minutes=minutes, seconds=seconds)
                        elif len(parts) == 3:
                            hours, minutes, seconds = map(int, parts)
                            delta = timedelta(hours=hours, minutes=minutes, seconds=seconds)
                        else:
                            delta = None

                        if delta:
                            spawn_time = datetime.now() + delta
                            new_boss['spawn_time'] = spawn_time.isoformat()
                    except:
                        pass

                if key not in boss_dict or not new_boss.get('from_map_update', False):
                    new_boss['last_updated'] = datetime.now().isoformat()
                elif key in boss_dict and new_boss.get('from_map_update', False):
                    existing_boss = boss_dict[key]
                    new_boss.update({
                        'channel': existing_boss.get('channel', '--'),
                        'countdown': existing_boss.get('countdown', ''),
                        'status': existing_boss.get('status', 'N'),
                        'spawn_time': existing_boss.get('spawn_time', ''),
                        'time_display': existing_boss.get('time_display', ''),
                        'last_updated': existing_boss.get('last_updated', datetime.now().isoformat()),
                        'urgent': existing_boss.get('urgent', False),
                        'expired': existing_boss.get('expired', False),
                        'rating': existing_boss.get('rating', 0)
                    })

                if new_boss.get('from_map_update', False):
                    if key in boss_dict:
                        boss_dict[key] = new_boss
                    else:
                        continue
                else:
                    if key in boss_dict:
                        existing_boss = boss_dict[key]
                        old_status = existing_boss.get('status', 'N')
                        new_status = new_boss.get('status', 'N')
                        if new_status == 'N' and old_status != 'N':
                            new_boss['rating'] = 0
                        else:
                            new_boss['rating'] = existing_boss.get('rating', 0)
                    else:
                        new_status = new_boss.get('status', 'N')
                        if new_status == 'N':
                            new_boss['rating'] = 0
                    boss_dict[key] = new_boss

        self._boss_data = list(boss_dict.values())
        sorted_bosses = self._sort_bosses(self._boss_data)

        self._auto_sort_timer.stop()
        self._auto_sort_timer.start(60000)

        self._update_display(sorted_bosses)
        self._save_ui_state()
        if hasattr(self, '_summary_bar'):
            self._summary_bar.refresh()

    def _auto_sort_bosses(self) -> None:
        if not self._boss_data:
            return
        sorted_bosses = self._sort_bosses(self._boss_data)
        self._update_display(sorted_bosses)

    def _update_display(self, sorted_bosses: List[Dict[str, Any]]) -> None:
        sorted_bosses = self._filter_by_tab(sorted_bosses)
        sorted_bosses = self._filter_by_name(sorted_bosses)

        for i, row in enumerate(self.boss_rows):
            if i < len(sorted_bosses):
                b = sorted_bosses[i]
                name = b.get('name', 'Unknown')
                channel = b.get('channel', '--')
                countdown = b.get('countdown', '')
                status = b.get('status', 'N')

                has_scan_data = (
                    (b.get('time_display') and b.get('time_display') != '--') or
                    (countdown and countdown != '') or
                    (status and status not in ['N', '-', '--']) or
                    (b.get('last_updated') and b.get('last_updated') != '')
                )

                if not has_scan_data:
                    row.set_data("", "", "", "", "", "", "", False, "", False, "")
                    row.setVisible(False)
                    continue

                lookup_map, lookup_lv, lookup_type = get_boss_info(name)

                boss_type = b.get('type', '') or lookup_type
                map_name = b.get('map', '') or lookup_map
                map_lv = lookup_lv

                time_display = "--"
                urgent = False

                if b.get('time_display') and b.get('time_display') != '--':
                    time_display = b.get('time_display')
                    spawn_time_str = b.get('spawn_time', '')
                    if spawn_time_str:
                        try:
                            spawn_time = datetime.fromisoformat(spawn_time_str)
                            now = datetime.now()
                            if spawn_time > now:
                                delta = spawn_time - now
                                urgent = delta.total_seconds() <= 180
                            else:
                                urgent = False
                        except:
                            pass
                elif status == "N" and countdown:
                    try:
                        spawn_time_str = b.get('spawn_time', '')
                        if spawn_time_str:
                            try:
                                spawn_time = datetime.fromisoformat(spawn_time_str)
                                now = datetime.now()

                                if spawn_time > now:
                                    delta = spawn_time - now
                                    time_display = spawn_time.strftime("%H:%M")
                                    b['time_display'] = time_display
                                    urgent = delta.total_seconds() <= 180

                                    if urgent:
                                        boss_key = f"{name.lower()}_{channel}"
                                        if boss_key not in self._urgent_notified:
                                            self._play_notification_sound()
                                            self._urgent_notified.add(boss_key)
                                    else:
                                        boss_key = f"{name.lower()}_{channel}"
                                        self._urgent_notified.discard(boss_key)
                                else:
                                    urgent = False
                            except ValueError:
                                delta = None
                        else:
                            parts = countdown.split(':')
                            if len(parts) == 2:
                                minutes, seconds = map(int, parts)
                                delta = timedelta(minutes=minutes, seconds=seconds)
                            elif len(parts) == 3:
                                hours, minutes, seconds = map(int, parts)
                                delta = timedelta(hours=hours, minutes=minutes, seconds=seconds)
                            else:
                                delta = None

                            if delta:
                                spawn_time = datetime.now() + delta
                                time_display = spawn_time.strftime("%H:%M")

                                b['spawn_time'] = spawn_time.isoformat()
                                b['time_display'] = time_display
                                urgent = delta.total_seconds() <= 180

                                if urgent:
                                    boss_key = f"{name.lower()}_{channel}"
                                    if boss_key not in self._urgent_notified:
                                        self._play_notification_sound()
                                        self._urgent_notified.add(boss_key)
                                else:
                                    boss_key = f"{name.lower()}_{channel}"
                                    self._urgent_notified.discard(boss_key)
                            else:
                                urgent = False
                    except:
                        time_display = countdown
                        urgent = False
                elif status.startswith("LV"):
                    time_display = "-"
                elif status == "Active":
                    time_display = "-"

                update_date = "--"
                last_updated_dt = None
                if status != "-" and status != "--":
                    last_updated = b.get('last_updated', '')
                    if last_updated:
                        try:
                            dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                            update_date = dt.strftime("%H:%M")
                            last_updated_dt = dt
                        except:
                            update_date = datetime.now().strftime("%H:%M")
                    else:
                        update_date = datetime.now().strftime("%H:%M")

                expired = False
                if time_display != "--" and time_display != "-":
                    spawn_time_str = b.get('spawn_time', '')
                    if spawn_time_str:
                        try:
                            spawn_time = datetime.fromisoformat(spawn_time_str)
                            now = datetime.now()
                            expired = spawn_time <= now
                        except:
                            pass

                row.set_data(name, map_name or '--', channel, status, boss_type, time_display, map_lv, urgent if status == "N" else False, update_date, expired, str(b.get('rating', 0)))
                if last_updated_dt is not None:
                    row.set_update_date(update_date, last_updated_dt=last_updated_dt)
                row.setVisible(True)
            else:
                row.set_data("", "", "", "", "", "", "", False, "", False, "")
                row.setVisible(False)

    def _on_rating_changed(self, name: str, channel: str, rating: int) -> None:
        for boss in self._boss_data:
            if (boss.get('name', '').lower() == name.lower() and boss.get('channel', '--') == channel):
                boss['rating'] = rating
                break
        self._save_ui_state()
        self.status_label.setText(f"★  Rating saved — {name[:20]}")
        self.status_label.setStyleSheet("color: #FCD34D; background: transparent;")

    def _sync_map_json_to_ui(self) -> None:
        pass

    def _update_boss_from_map_entry(self, boss: Dict[str, Any], map_entry: Dict[str, Any]) -> None:
        if not boss.get('map') or boss.get('map') == '--':
            boss['map'] = map_entry.get('map', '')
        if not boss.get('type') or boss.get('type') == '--':
            boss['type'] = map_entry.get('type', '')
        if not boss.get('map_lv') or boss.get('map_lv') == '--':
            boss['map_lv'] = map_entry.get('lv', '')
        if 'rating' in map_entry:
            boss['rating'] = map_entry['rating']
        elif 'note' in map_entry:
            try:
                rating = int(map_entry['note'])
                boss['rating'] = max(0, min(5, rating))
            except (ValueError, TypeError):
                pass
        boss['from_map_update'] = True

    def _create_boss_from_map_entry(self, map_entry: Dict[str, Any]) -> Dict[str, Any]:
        boss_name = map_entry.get('boss', '').strip()
        if not boss_name:
            return None
        return {
            'name': boss_name,
            'map': map_entry.get('map', ''),
            'channel': '--',
            'status': '--',
            'countdown': '',
            'type': map_entry.get('type', ''),
            'map_lv': map_entry.get('lv', ''),
            'rating': map_entry.get('rating', 0),
            'from_map_update': True,
            'last_updated': datetime.now().isoformat()
        }

    # Note: _save_note_to_map method removed - ratings are now saved to ui_state.json only

    def _delete_boss_record(self, name: str, channel: str) -> None:
        def _norm_ch(ch) -> str:
            if not ch or ch in ('-', '--'):
                return ''
            return str(ch)

        target_name = name.lower()
        target_ch = _norm_ch(channel)

        matched = None
        for boss in self._boss_data:
            boss_name = boss.get('name', '').lower()
            boss_ch = _norm_ch(boss.get('channel'))
            if boss_name == target_name and boss_ch == target_ch:
                matched = boss
                break

        # Fallback: match by name only (when channel is empty/unknown)
        if matched is None and not target_ch:
            for boss in self._boss_data:
                if boss.get('name', '').lower() == target_name:
                    matched = boss
                    break

        # Fallback: match by channel only (when name is empty)
        if matched is None and not target_name:
            for boss in self._boss_data:
                if _norm_ch(boss.get('channel')) == target_ch:
                    matched = boss
                    break

        if matched is not None:
            matched['channel'] = "-"
            matched['status'] = "-"
            matched['countdown'] = ""
            matched['time_display'] = ""
            matched['spawn_time'] = ""
            matched['last_updated'] = ""
            matched['type'] = "-"
            self.status_label.setText(f"◎  Cleared — {name[:20]}")
            self.status_label.setStyleSheet("color: #475569; background: transparent;")

        sorted_bosses = self._sort_bosses(self._boss_data)
        self._update_display(sorted_bosses)
        self._save_ui_state()
        self._auto_sort_timer.stop()
        self._auto_sort_timer.start(60000)

    def _reset_boss_data(self) -> None:
        self._boss_data.clear()
        try:
            state_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui_state.json")
            if os.path.exists(state_file):
                os.remove(state_file)
        except Exception:
            pass
        self._update_display([])
        self.status_label.setText("◎  Cleared")
        self.status_label.setStyleSheet("color: #475569; background: transparent;")

    def _refresh_countdowns(self) -> None:
        if not self._boss_data:
            return
        boss_by_key = {
            f"{b.get('name', '').lower()}_{b.get('channel', '--')}": b
            for b in self._boss_data
        }
        for row in self.boss_rows:
            if not row.isVisible() or not row._boss_key:
                continue
            boss = boss_by_key.get(row._boss_key)
            if not boss or boss.get('status', 'N') != 'N':
                continue
            spawn_time_str = boss.get('spawn_time', '')
            if not spawn_time_str:
                continue
            try:
                spawn_time = datetime.fromisoformat(spawn_time_str)
                if spawn_time > datetime.now():
                    row.update_time(spawn_time.strftime("%H:%M"))
            except Exception:
                pass

    def _refresh_elapsed_times(self) -> None:
        """Refresh elapsed time display for all visible rows."""
        for row in self.boss_rows:
            if row.isVisible():
                row.update_elapsed_display()

    def _get_status_priority(self, status: str) -> int:
        priority_map = {
            "Active": 0, "LV4": 1, "LV3": 2, "LV2": 3, "LV1": 4, "N": 5,
        }
        if status.startswith("LV"):
            try:
                level = int(status[2:])
                return 5 - level
            except:
                pass
        return priority_map.get(status, 6)

    def _sort_bosses(self, bosses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        def sort_key(boss):
            if self._sort_column == "lv":
                lookup_map, lookup_lv, lookup_type = get_boss_info(boss.get('name', ''))
                map_lv = lookup_lv or boss.get('map_lv', '')
                if map_lv and map_lv != '--':
                    try:
                        level = int(map_lv[2:]) if map_lv.startswith('LV') else int(map_lv)
                        lv_value = level
                    except:
                        lv_value = 999
                else:
                    lv_value = 1000
                return (lv_value, boss.get('name', '').lower())

            elif self._sort_column == "ch":
                channel = boss.get('channel', '--')
                if channel and channel != '--':
                    try:
                        if channel.startswith('CH.'):
                            ch_num = int(channel[3:].replace(' ', ''))
                        elif channel.startswith('CH '):
                            ch_num = int(channel[3:].replace(' ', ''))
                        else:
                            numbers = re.findall(r'\d+', channel)
                            ch_num = int(numbers[0]) if numbers else 999
                    except:
                        ch_num = 999
                else:
                    ch_num = 1000
                return (ch_num, boss.get('name', '').lower())

            elif self._sort_column == "spawn":
                spawn_time_str = boss.get('spawn_time', '')
                if spawn_time_str:
                    try:
                        spawn_time = datetime.fromisoformat(spawn_time_str)
                        spawn_timestamp = spawn_time.timestamp()
                    except:
                        spawn_timestamp = 999999999999
                else:
                    spawn_timestamp = 999999999999
                return (spawn_timestamp, boss.get('name', '').lower())

            elif self._sort_column == "scanned":
                last_updated = boss.get('last_updated', '')
                if last_updated:
                    try:
                        update_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                        update_timestamp = update_time.timestamp()
                    except:
                        update_timestamp = 0
                else:
                    update_timestamp = 0
                return (update_timestamp, boss.get('name', '').lower())

            elif self._sort_column == "status":
                status = boss.get('status', 'N')
                priority = self._get_status_priority(status)
                if status == "N":
                    spawn_time_str = boss.get('spawn_time', '')
                    if spawn_time_str:
                        try:
                            spawn_time = datetime.fromisoformat(spawn_time_str)
                            spawn_timestamp = spawn_time.timestamp()
                        except:
                            spawn_timestamp = 999999999999
                    else:
                        countdown = boss.get('countdown', '')
                        try:
                            parts = countdown.split(':')
                            if len(parts) == 2:
                                minutes, seconds = map(int, parts)
                                spawn_timestamp = datetime.now().timestamp() + (minutes * 60 + seconds)
                            elif len(parts) == 3:
                                hours, minutes, seconds = map(int, parts)
                                spawn_timestamp = datetime.now().timestamp() + (hours * 3600 + minutes * 60 + seconds)
                            else:
                                spawn_timestamp = 999999999999
                        except:
                            spawn_timestamp = 999999999999
                    return (priority, spawn_timestamp)
                else:
                    return (priority, 0)
            return (boss.get('name', '').lower(),)

        sorted_bosses = sorted(bosses, key=sort_key)
        if self._sort_direction == "desc":
            sorted_bosses.reverse()
        return sorted_bosses

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Alt:
            self._alt_pressed = True
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
            self.drag_hint.setStyleSheet("color: #6EE7B7; background: transparent;")
            self.drag_hint.setText("Drag")
        elif event.key() == Qt.Key.Key_F12:
            if self._is_expanded:
                self._collapse_window()
            else:
                self._expand_window()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Alt:
            self._alt_pressed = False
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self.drag_hint.setStyleSheet("color: #1E293B; background: transparent;")
            self.drag_hint.setText("Alt+Drag")

    def mousePressEvent(self, event) -> None:
        from PyQt6.QtWidgets import QApplication
        modifiers = QApplication.keyboardModifiers()
        is_alt_pressed = (modifiers & Qt.KeyboardModifier.AltModifier) != 0

        if event.button() == Qt.MouseButton.LeftButton:
            if is_alt_pressed:
                self._window_dragging = True
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                self.drag_hint.setStyleSheet("color: #A5B4FC; background: transparent;")
                self.drag_hint.setText("Moving")
                event.accept()
                return
            edges = self._get_resize_edges(event.position().toPoint())
            if edges != 0:
                self._resizing = True
                self._resize_edges = edges
                self._drag_pos = event.globalPosition().toPoint()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._resizing:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self._resize_window(delta)
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()
        elif self._window_dragging:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            self.move(new_pos)
            event.accept()
        else:
            edges = self._get_resize_edges(event.position().toPoint())
            self._update_cursor(edges)
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._resizing:
            self._resizing = False
            self._resize_edges = 0
            event.accept()
        elif self._window_dragging:
            self._window_dragging = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _get_resize_edges(self, pos: QPoint) -> int:
        rect = self.rect()
        edges = 0
        if pos.x() <= self._edge_size: edges |= 1
        elif pos.x() >= rect.width() - self._edge_size: edges |= 2
        if pos.y() <= self._edge_size: edges |= 8
        elif pos.y() >= rect.height() - self._edge_size: edges |= 4
        return edges

    def _update_cursor(self, edges: int) -> None:
        if edges & 1 and edges & 8: self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif edges & 2 and edges & 4: self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif edges & 1 and edges & 4: self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif edges & 2 and edges & 8: self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif edges & 1 or edges & 2: self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif edges & 8 or edges & 4: self.setCursor(Qt.CursorShape.SizeVerCursor)
        else: self.setCursor(Qt.CursorShape.ArrowCursor)

    def _resize_window(self, delta: QPoint) -> None:
        new_rect = self.rect()
        min_size = self.minimumSize()
        if self._resize_edges & 1:
            new_rect.setLeft(new_rect.left() + delta.x())
            if new_rect.width() < min_size.width(): new_rect.setLeft(new_rect.right() - min_size.width())
        elif self._resize_edges & 2:
            new_rect.setRight(new_rect.right() + delta.x())
            if new_rect.width() < min_size.width(): new_rect.setRight(new_rect.left() + min_size.width())
        if self._resize_edges & 8:
            new_rect.setTop(new_rect.top() + delta.y())
            if new_rect.height() < min_size.height(): new_rect.setTop(new_rect.bottom() - min_size.height())
        elif self._resize_edges & 4:
            new_rect.setBottom(new_rect.bottom() + delta.y())
            if new_rect.height() < min_size.height(): new_rect.setBottom(new_rect.top() + min_size.height())
        self.setGeometry(new_rect)

    def _minimize_window(self) -> None:
        self.showMinimized()

    def _maximize_window(self) -> None:
        if self.isMaximized():
            self.showNormal()
            self.maximize_btn.setText("□")
        else:
            self.showMaximized()
            self.maximize_btn.setText("❐")

    def enterEvent(self, event) -> None:
        self._opacity_anim.stop()
        self._opacity_anim.setStartValue(self.windowOpacity())
        self._opacity_anim.setEndValue(1.0)
        self._opacity_anim.start()

        if not self._is_expanded and not self._is_locked:
            self._collapse_timer.stop()
            self._expand_timer.start(self._expand_delay)

    def leaveEvent(self, event) -> None:
        if self.geometry().contains(QCursor.pos()):
            return

        self._opacity_anim.stop()
        self._opacity_anim.setStartValue(self.windowOpacity())
        self._opacity_anim.setEndValue(self._base_opacity)
        self._opacity_anim.start()

        if self._is_expanded and not self._is_locked:
            self._expand_timer.stop()
            self._collapse_timer.start(self._collapse_delay)

    def _expand_window(self) -> None:
        if not self._is_expanded and not self._is_locked:
            if self.geometry().contains(QCursor.pos()):
                self._is_expanded = True

                current_geom = self.geometry()
                new_height = self._expanded_height
                y_shift = new_height - current_geom.height()

                end_geom = QRect(
                    current_geom.x(),
                    current_geom.y() - y_shift,
                    current_geom.width(),
                    new_height
                )

                self._geom_anim.stop()
                self._geom_anim.setStartValue(current_geom)
                self._geom_anim.setEndValue(end_geom)
                self._geom_anim.start()

    def _collapse_window(self) -> None:
        if self._is_expanded and not self._is_locked:
            if not self.geometry().contains(QCursor.pos()):
                self._is_expanded = False

                current_geom = self.geometry()
                new_height = self._collapsed_height
                y_shift = current_geom.height() - new_height

                end_geom = QRect(
                    current_geom.x(),
                    current_geom.y() + y_shift,
                    current_geom.width(),
                    new_height
                )

                self._geom_anim.stop()
                self._geom_anim.setStartValue(current_geom)
                self._geom_anim.setEndValue(end_geom)
                self._geom_anim.start()

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized():
                self._is_expanded = False
            elif not self.isMinimized() and not self.isMaximized():
                if self.underMouse():
                    self._expand_window()
        super().changeEvent(event)

    def closeEvent(self, event) -> None:
        if self._close_callback:
            self._close_callback()
        event.accept()
