"""Map-related display widgets: image viewer, popup, and inline icon label."""

import os
from typing import Optional

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap, QFontMetrics
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
)

from ..map_level import get_map_coordinates
from .timeline_widget import _TimelineCanvas, TimelineRowModel


class MapImageWidget(QWidget):
    """Widget displaying a boss image."""

    def __init__(self, map_name: str, boss_name: str = "", parent=None):
        super().__init__(parent)
        self._map_name = map_name
        self._boss_name = boss_name
        self._pixmap: Optional[QPixmap] = None
        self._boss_spawn_color = QColor("#64748B")  # Default gray
        self._max_width = 400
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
            img_width = self._pixmap.width()
            img_height = self._pixmap.height()

            scale = min(self._max_width / img_width, self._max_height / img_height, 1.0)

            self._scaled_width = int(img_width * scale)
            self._scaled_height = int(img_height * scale)
        else:
            self._scaled_width = 220
            self._scaled_height = 220

        self.setFixedSize(self._scaled_width, self._scaled_height)
        self.update()

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

        coords = get_map_coordinates(self._map_name)
        if not coords:
            painter.setPen(QColor("#94A3B8"))
            painter.setFont(QFont("Segoe UI", 10))
            text = "Map unavailable"
            fm = QFontMetrics(painter.font())
            text_width = fm.horizontalAdvance(text)
            x = (self.width() - text_width) // 2
            y = self.height() // 2
            painter.drawText(x, y, text)
            return

        if self._pixmap and not self._pixmap.isNull():
            scaled_pixmap = self._pixmap.scaled(
                self._scaled_width,
                self._scaled_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            x_offset = (self.width() - scaled_pixmap.width()) // 2
            y_offset = (self.height() - scaled_pixmap.height()) // 2
            painter.drawPixmap(x_offset, y_offset, scaled_pixmap)

            img_rect = scaled_pixmap.rect()
            img_rect.moveCenter(self.rect().center())
        else:
            painter.fillRect(self.rect(), QColor("#E2E8F0"))


class MapImagePopup(QWidget):
    """Popup window showing map image with markers."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._map_name = ""
        self._map_lv = ""
        self._boss_name = ""

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(8)

        self._container = QFrame(self)
        self._container.setStyleSheet("""
            QFrame {
                background: rgba(245, 240, 232, 0.98);
                border: 1px solid rgba(54, 104, 141, 0.40);
                border-radius: 12px;
            }
        """)
        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(12, 12, 12, 12)
        container_layout.setSpacing(8)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)

        self._icon_label = QLabel("🗺")
        self._icon_label.setFont(QFont("Segoe UI", 11))
        self._icon_label.setStyleSheet("color: #5A6A78;")
        header_layout.addWidget(self._icon_label)

        self._name_label = QLabel("")
        self._name_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self._name_label.setStyleSheet("color: #1A2A38;")
        header_layout.addWidget(self._name_label)

        self._level_label = QLabel("")
        self._level_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self._level_label.setStyleSheet("""
            color: #1A5A80;
            background: rgba(54, 104, 141, 0.12);
            padding: 2px 8px;
            border-radius: 4px;
            border: 1px solid rgba(54, 104, 141, 0.30);
        """)
        header_layout.addWidget(self._level_label)
        header_layout.addStretch()
        container_layout.addLayout(header_layout)

        images_layout = QHBoxLayout()
        images_layout.setSpacing(12)

        self._boss_section = QVBoxLayout()
        self._boss_section.setSpacing(4)
        boss_label = QLabel("👹 Boss")
        boss_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        boss_label.setStyleSheet("color: #5A6A78;")
        boss_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._boss_section.addWidget(boss_label)

        self._boss_image_widget = QLabel("No image")
        self._boss_image_widget.setFixedSize(220, 220)
        self._boss_image_widget.setStyleSheet("""
            QLabel {
                background: rgba(255, 255, 255, 0.60);
                border: 1px solid rgba(54, 104, 141, 0.25);
                border-radius: 8px;
                color: #A89880;
            }
        """)
        self._boss_image_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._boss_section.addWidget(self._boss_image_widget)
        images_layout.addLayout(self._boss_section)

        self._map_section = QVBoxLayout()
        self._map_section.setSpacing(4)
        map_label = QLabel("🗺 Map")
        map_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        map_label.setStyleSheet("color: #5A6A78;")
        map_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._map_section.addWidget(map_label)

        self._map_image_widget = MapImageWidget("", "", self._container)
        self._map_image_widget.setFixedSize(220, 220)
        self._map_section.addWidget(self._map_image_widget)
        images_layout.addLayout(self._map_section)

        container_layout.addLayout(images_layout)
        
        # Timeline Canvas (Hidden by default until model is set)
        self._timeline_canvas = _TimelineCanvas(self._container)
        self._timeline_canvas.setStyleSheet("""
            background: rgba(255, 255, 255, 0.40);
            border: 1px solid rgba(54, 104, 141, 0.15);
            border-radius: 10px;
        """)
        self._timeline_canvas.hide()
        container_layout.addWidget(self._timeline_canvas)

        self._layout.addWidget(self._container)

    def set_map_data(self, map_name: str, map_lv: str, boss_urgent: bool = False, boss_name: str = ""):
        """Set map data and update display."""
        self._map_name = map_name
        self._map_lv = map_lv
        self._boss_name = boss_name

        self._name_label.setText(map_name if map_name else "Unknown")
        self._level_label.setText(f"LV {map_lv}" if map_lv else "")
        self._level_label.setVisible(bool(map_lv))

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

        self._map_image_widget.set_map_name(map_name, "")
        self._map_image_widget.setFixedSize(220, 220)

        if boss_urgent:
            color = QColor("#22C55E")
        else:
            color = QColor("#EF4444")

        coords = get_map_coordinates(map_name)
        if not coords:
            color = QColor("#64748B")

        self._map_image_widget.set_boss_spawn_color(color)

        # Hide timeline initially when resetting map data
        self._timeline_canvas.hide()
        self._timeline_canvas.set_model(None)

        self.adjustSize()

    def set_timeline_model(self, model: Optional[TimelineRowModel]):
        """Set timeline model and show timeline canvas if model exists."""
        if model:
            self._timeline_canvas.update_now()
            self._timeline_canvas.set_model(model)
            self._timeline_canvas.show()
        else:
            self._timeline_canvas.hide()
            self._timeline_canvas.set_model(None)
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

        self._icon_label = QLabel("🗺")
        self._icon_label.setFont(QFont("Segoe UI", 9))
        self._icon_label.setStyleSheet("color: #64748B;")
        self._icon_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self._icon_label.hide()
        layout.addWidget(self._icon_label)

        self._text_label = QLabel("")
        self._text_label.setFont(QFont("Segoe UI", 9))
        self._text_label.setStyleSheet("color: #64748B; background: transparent;")
        self._text_label.setFixedWidth(140)
        layout.addWidget(self._text_label)

        self._popup = MapImagePopup(self)
        self._popup.hide()

        self.setMouseTracking(True)

    def set_map_data(self, map_name: str, map_lv: str, boss_urgent: bool = False, boss_name: str = ""):
        """Set map data and update display."""
        self._map_name = map_name
        self._map_lv = map_lv
        self._boss_name = boss_name
        self._boss_urgent = boss_urgent

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

        self._popup.set_map_data(self._map_name, self._map_lv, self._boss_urgent, self._boss_name)

        popup_pos = self.mapToGlobal(QPoint(0, 0))
        popup_pos.setY(popup_pos.y() - self._popup.height() - 8)
        popup_pos.setX(popup_pos.x())

        self._popup.show_at(popup_pos)

    def leaveEvent(self, event):
        """Hide popup when leaving."""
        self._popup.hide()
