"""Boss checklist popup — shows all bosses from map.json with found status."""

import json
import os
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QAbstractItemView,
)


class BossChecklistLoader:
    """Loads master boss list and cross-references with detected bosses."""

    def __init__(self, map_path: str, boss_data_path: str):
        self._map_path = map_path
        self._boss_data_path = boss_data_path

    def load_checklist(self) -> List[Dict[str, Any]]:
        """Return list of dicts: {name, type, map, lv, found}."""
        master = []
        try:
            with open(self._map_path, 'r', encoding='utf-8') as f:
                master = json.load(f)
        except Exception:
            master = []

        detected_names = set()
        try:
            with open(self._boss_data_path, 'r', encoding='utf-8') as f:
                boss_data = json.load(f)
            for entry in boss_data.values():
                name = entry.get('name', '').strip()
                if name:
                    detected_names.add(name.lower())
        except Exception:
            pass

        result = []
        for item in master:
            name = item.get('boss', '').strip()
            map_name = item.get('map', '').strip()
            lv = item.get('lv', '').strip()
            btype = item.get('type', '').strip()
            found = name.lower() in detected_names
            result.append({
                'name': name,
                'type': btype,
                'map': map_name,
                'lv': lv,
                'found': found,
            })

        def sort_key(row):
            try:
                return (int(row['lv']), row['name'].lower())
            except ValueError:
                return (9999, row['name'].lower())
        result.sort(key=sort_key)
        return result


class StatsPopupWindow(QWidget):
    """Frameless always-on-top boss checklist popup."""

    def __init__(self, data_path: str, parent=None):
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._boss_data_path = data_path
        base_dir = os.path.dirname(data_path)
        self._map_path = os.path.join(base_dir, 'data', 'map.json')
        self._loader = BossChecklistLoader(self._map_path, self._boss_data_path)
        self._drag_pos: Optional[QPoint] = None
        self._all_rows: List[Dict[str, Any]] = []
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        self.setFixedSize(720, 520)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        container = QFrame(self)
        container.setStyleSheet("""
            QFrame {
                background: rgba(8, 12, 26, 0.98);
                border: 1px solid rgba(99, 102, 241, 0.4);
                border-radius: 12px;
            }
        """)
        main = QVBoxLayout(container)
        main.setContentsMargins(16, 12, 16, 14)
        main.setSpacing(10)

        # Title strip
        title_row = QHBoxLayout()
        title_row.setSpacing(6)

        dot = QLabel("◆")
        dot.setFont(QFont("Segoe UI", 9))
        dot.setStyleSheet("color: #6366F1; background: transparent; border: none;")
        title_row.addWidget(dot)

        title_lbl = QLabel("Boss Checklist")
        title_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #E2E8F0; background: transparent; border: none;")
        title_row.addWidget(title_lbl)
        title_row.addStretch()

        self._count_lbl = QLabel("")
        self._count_lbl.setFont(QFont("Segoe UI", 9))
        self._count_lbl.setStyleSheet("color: #64748B; background: transparent; border: none;")
        title_row.addWidget(self._count_lbl)

        refresh_btn = QPushButton("↻  Refresh")
        refresh_btn.setFixedSize(88, 26)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setFont(QFont("Segoe UI", 9))
        refresh_btn.setStyleSheet("""
            QPushButton {
                color: #818CF8;
                background: transparent;
                border: 1px solid rgba(99, 102, 241, 0.35);
                border-radius: 6px;
            }
            QPushButton:hover { background: rgba(99, 102, 241, 0.15); }
            QPushButton:pressed { background: rgba(99, 102, 241, 0.25); }
        """)
        refresh_btn.clicked.connect(self.refresh)
        title_row.addWidget(refresh_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        close_btn.setStyleSheet("""
            QPushButton {
                color: #475569;
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 6px;
            }
            QPushButton:hover {
                color: #FDA4AF;
                background: rgba(244, 63, 94, 0.15);
                border: 1px solid rgba(244, 63, 94, 0.3);
            }
        """)
        close_btn.clicked.connect(self.hide)
        title_row.addWidget(close_btn)
        main.addLayout(title_row)

        # Search box
        search_row = QHBoxLayout()
        search_row.setSpacing(6)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Filter bosses or maps...")
        self.search_box.setFont(QFont("Segoe UI", 9))
        self.search_box.setFixedHeight(26)
        self.search_box.setStyleSheet("""
            QLineEdit {
                color: #94A3B8;
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 7px;
                padding: 2px 10px;
            }
            QLineEdit:focus {
                border: 1px solid rgba(99, 102, 241, 0.5);
                background: rgba(99, 102, 241, 0.07);
            }
        """)
        self.search_box.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self.search_box)
        main.addLayout(search_row)

        # Checklist table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Boss (type)", "Map", "Lv", "Found"])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 50)
        self.table.setColumnWidth(3, 60)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSortingEnabled(True)

        self.table.setStyleSheet("""
            QTableWidget {
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
                gridline-color: transparent;
            }
            QHeaderView::section {
                background: rgba(255, 255, 255, 0.03);
                color: #64748B;
                padding: 6px 8px;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.06);
                font-family: "Segoe UI";
                font-size: 9pt;
                font-weight: 700;
            }
            QTableWidget::item {
                color: #94A3B8;
                padding: 4px 8px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            }
            QTableWidget::item:selected {
                background: rgba(99, 102, 241, 0.15);
                color: #E2E8F0;
            }
        """)
        main.addWidget(self.table, 1)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setFixedHeight(1)
        div.setStyleSheet("background: rgba(255, 255, 255, 0.05); border: none;")
        main.addWidget(div)

        outer.addWidget(container)

    def _on_search_changed(self, text: str):
        self._apply_filter(text.strip().lower())

    def _apply_filter(self, query: str):
        filtered = self._all_rows
        if query:
            filtered = [
                r for r in self._all_rows
                if query in r['name'].lower() or query in r['map'].lower()
            ]
        self._populate_table(filtered)

    def _populate_table(self, rows: List[Dict[str, Any]]):
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            boss_text = row['name']
            if row['type']:
                boss_text += f" ({row['type']})"
            item = QTableWidgetItem(boss_text)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 0, item)

            item = QTableWidgetItem(row['map'])
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 1, item)

            item = QTableWidgetItem(row['lv'])
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 2, item)

            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            if row['found']:
                chk.setCheckState(Qt.CheckState.Checked)
            else:
                chk.setCheckState(Qt.CheckState.Unchecked)
            self.table.setItem(i, 3, chk)

        # Update count label
        found_count = sum(1 for r in self._all_rows if r['found'])
        total = len(self._all_rows)
        self._count_lbl.setText(f"{found_count}/{total}")

    def refresh(self):
        self._all_rows = self._loader.load_checklist()
        self._apply_filter(self.search_box.text().strip().lower())

        # Alternate row coloring
        for i in range(self.table.rowCount()):
            bg = QColor(12, 15, 26) if i % 2 else QColor(8, 12, 26)
            for j in range(self.table.columnCount()):
                item = self.table.item(i, j)
                if item:
                    item.setBackground(bg)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)
