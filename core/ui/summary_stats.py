"""Summary statistics bar — Coming / Soon / Total Tracked cards."""

import json
from datetime import datetime, timedelta
from typing import Dict

from PyQt6.QtCore import QTimer, pyqtSignal, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QFrame, QLabel


class ClickableFrame(QFrame):
    """QFrame that emits clicked signal on left mouse press."""
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def set_active(self, active: bool):
        self._active = active
        self._update_border()

    def _update_border(self):
        # Extract current stylesheet color values; re-apply border highlight when active
        sheet = self.styleSheet()
        if self._active:
            # Add a stronger border when active
            if "border: 2px solid" not in sheet:
                sheet = sheet.replace(
                    "border: 1px solid rgba(54, 104, 141, 0.15);",
                    "border: 2px solid rgba(54, 104, 141, 0.60);"
                )
        else:
            sheet = sheet.replace(
                "border: 2px solid rgba(54, 104, 141, 0.60);",
                "border: 1px solid rgba(54, 104, 141, 0.15);"
            )
        self.setStyleSheet(sheet)


class SummaryStatsBar(QWidget):
    """Three metric cards shown above the boss table: Coming | Soon | Total Tracked."""

    filter_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        self._cards: Dict[str, QLabel] = {}
        self._frames: Dict[str, ClickableFrame] = {}
        for key, label, color in [
            ("coming", "Coming", "#1A5A80"),
            ("soon",   "Soon",   "#B8860B"),
        ]:
            frame = ClickableFrame()
            frame.setCursor(Qt.CursorShape.PointingHandCursor)
            frame.setStyleSheet(f"""
                QFrame {{
                    background: rgba(255, 255, 255, 0.60);
                    border: 1px solid rgba(54, 104, 141, 0.15);
                    border-left: 3px solid {color};
                    border-radius: 6px;
                }}
            """)
            frame.clicked.connect(lambda k=key: self.filter_clicked.emit(k))
            fl = QHBoxLayout(frame)
            fl.setContentsMargins(10, 4, 10, 4)
            fl.setSpacing(6)

            val_lbl = QLabel("0")
            val_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            val_lbl.setStyleSheet(f"color: {color}; background: transparent; border: none;")

            txt_lbl = QLabel(label)
            txt_lbl.setFont(QFont("Segoe UI", 8))
            txt_lbl.setStyleSheet("color: #8A7A68; background: transparent; border: none;")

            fl.addWidget(val_lbl)
            fl.addWidget(txt_lbl)
            fl.addStretch()

            self._cards[key] = val_lbl
            self._frames[key] = frame
            layout.addWidget(frame)

        # The timer is removed because refresh will be called by OverlayWindow whenever data updates

    def refresh(self, boss_data: list = None):
        if not boss_data:
            self._cards['coming'].setText("0")
            self._cards['soon'].setText("0")
            return

        now = datetime.now()
        coming = 0
        soon = 0

        for b in boss_data:
            s = b.get('status', 'N')
            cd = b.get('countdown', '')
            has_scan_data = (
                (b.get('time_display') and b.get('time_display') != '--') or
                (cd and cd != '') or
                (s and s not in ['N', '-', '--']) or
                (b.get('last_updated') and b.get('last_updated') != '')
            )
            if not has_scan_data:
                continue

            spawn_str = b.get('spawn_time')
            spawn_dt = None
            if spawn_str:
                try:
                    spawn_dt = datetime.fromisoformat(spawn_str)
                except (ValueError, TypeError):
                    pass

            is_coming = False
            is_soon = False

            if s != "N" or (spawn_dt and spawn_dt < now):
                is_coming = True

            if s == "N" or (spawn_dt and spawn_dt > now):
                is_soon = True

            if is_coming:
                coming += 1
            if is_soon:
                soon += 1

        self._cards['coming'].setText(str(coming))
        self._cards['soon'].setText(str(soon))

    def set_active_filter(self, key: str | None):
        """Highlight the card matching key; clear highlight on all others."""
        for k, frame in self._frames.items():
            frame.set_active(k == key)
