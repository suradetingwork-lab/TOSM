"""Summary statistics bar — Active / Upcoming ≤5m / Total Tracked cards."""

import json
from datetime import datetime, timedelta
from typing import Dict

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QFrame, QLabel


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
