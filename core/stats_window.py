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

from .ui.map_widgets import MapImagePopup


class NumericTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        if isinstance(other, QTableWidgetItem):
            try:
                return float(self.text() or 0) < float(other.text() or 0)
            except ValueError:
                return self.text() < other.text()
        return super().__lt__(other)


class BossChecklistLoader:
    """Loads master boss list and cross-references with detected bosses via map id."""

    def __init__(self, map_path: str):
        self._map_path = map_path

    def load_checklist(self, current_bosses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Return list of dicts: {name, type, map, lv, found}.
        
        'found' is True when the boss is present in the current_bosses table with scan data.
        """
        master = []
        try:
            with open(self._map_path, 'r', encoding='utf-8') as f:
                master = json.load(f)
        except Exception:
            master = []

        # Find names of bosses currently in the tracker
        tracked_boss_names = set()
        for b in current_bosses:
            s = b.get('status', 'N')
            cd = b.get('countdown', '')
            has_scan_data = (
                (b.get('time_display') and b.get('time_display') != '--') or
                (cd and cd != '') or
                (s and s not in ['N', '-', '--']) or
                (b.get('last_updated') and b.get('last_updated') != '')
            )
            if has_scan_data:
                tracked_boss_names.add(b.get('name', '').strip().lower())

        result = []
        for item in master:
            name = item.get('boss', '').strip()
            map_name = item.get('map', '').strip()
            lv = item.get('lv', '').strip()
            btype = item.get('type', '').strip()

            found = name.lower() in tracked_boss_names

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
        base_dir = os.path.dirname(data_path)
        self._map_path = os.path.join(base_dir, 'data', 'map.json')
        self._loader = BossChecklistLoader(self._map_path)
        self._drag_pos: Optional[QPoint] = None
        self._all_rows: List[Dict[str, Any]] = []
        self._displayed_rows: List[Dict[str, Any]] = []
        self._init_ui()

    def _init_ui(self):
        self.setFixedSize(720, 520)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        container = QFrame(self)
        container.setStyleSheet("""
            QFrame {
                background: rgba(245, 240, 232, 0.98);
                border: 1px solid rgba(54, 104, 141, 0.30);
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
        dot.setStyleSheet("color: #D4860A; background: transparent; border: none;")
        title_row.addWidget(dot)

        title_lbl = QLabel("Boss Checklist")
        title_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #1A2A38; background: transparent; border: none;")
        title_row.addWidget(title_lbl)
        title_row.addStretch()

        self._count_lbl = QLabel("")
        self._count_lbl.setFont(QFont("Segoe UI", 9))
        self._count_lbl.setStyleSheet("color: #8A7A68; background: transparent; border: none;")
        title_row.addWidget(self._count_lbl)

        refresh_btn = QPushButton("↻  Refresh")
        refresh_btn.setFixedSize(88, 26)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setFont(QFont("Segoe UI", 9))
        refresh_btn.setStyleSheet("""
            QPushButton {
                color: #1A5A80;
                background: transparent;
                border: 1px solid rgba(54, 104, 141, 0.35);
                border-radius: 6px;
            }
            QPushButton:hover { background: rgba(54, 104, 141, 0.12); }
            QPushButton:pressed { background: rgba(54, 104, 141, 0.22); }
        """)
        # The button won't just call self.refresh(), we will leave it or remove it. 
        # Actually, let's keep it but connect to a local method or lambda if possible. 
        # Since refresh requires current_bosses, we might not have it inside StatsPopupWindow easily without storing it.
        # Let's store self._last_bosses in StatsPopupWindow.
        refresh_btn.clicked.connect(self.refresh)
        title_row.addWidget(refresh_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        close_btn.setStyleSheet("""
            QPushButton {
                color: #A89880;
                background: transparent;
                border: 1px solid rgba(189, 165, 137, 0.30);
                border-radius: 6px;
            }
            QPushButton:hover {
                color: #8B5E00;
                background: rgba(241, 137, 4, 0.10);
                border: 1px solid rgba(241, 137, 4, 0.40);
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
                color: #1A2A38;
                background: rgba(255, 255, 255, 0.70);
                border: 1px solid rgba(54, 104, 141, 0.20);
                border-radius: 7px;
                padding: 2px 10px;
            }
            QLineEdit:focus {
                border: 1px solid rgba(54, 104, 141, 0.60);
                background: rgba(255, 255, 255, 0.92);
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
        self.table.setMouseTracking(True)
        self.table.cellEntered.connect(self._on_cell_entered)
        self.table.viewport().installEventFilter(self)
        
        self._popup = MapImagePopup(self)
        self._popup.hide()

        self.table.setStyleSheet("""
            QTableWidget {
                background: transparent;
                border: 1px solid rgba(54, 104, 141, 0.15);
                border-radius: 8px;
                gridline-color: transparent;
            }
            QHeaderView::section {
                background: rgba(54, 104, 141, 0.08);
                color: #5A6A78;
                padding: 6px 8px;
                border: none;
                border-bottom: 1px solid rgba(54, 104, 141, 0.18);
                font-family: "Segoe UI";
                font-size: 9pt;
                font-weight: 700;
            }
            QTableWidget::item {
                color: #1A2A38;
                padding: 4px 8px;
                border-bottom: 1px solid rgba(54, 104, 141, 0.07);
            }
            QTableWidget::item:selected {
                background: rgba(54, 104, 141, 0.16);
                color: #0E3A58;
            }
        """)
        main.addWidget(self.table, 1)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setFixedHeight(1)
        div.setStyleSheet("background: rgba(54, 104, 141, 0.12); border: none;")
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
        self.table.setSortingEnabled(False)
        self._displayed_rows = rows
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

            item = NumericTableWidgetItem(row['lv'])
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

        self.table.setSortingEnabled(True)

        # Update count label
        found_count = sum(1 for r in self._all_rows if r['found'])
        total = len(self._all_rows)
        self._count_lbl.setText(f"{found_count}/{total}")

    def refresh(self, current_bosses=None):
        if isinstance(current_bosses, bool):
            current_bosses = None
            
        if current_bosses is not None:
            self._last_bosses = current_bosses
        elif not hasattr(self, '_last_bosses'):
            self._last_bosses = []
        
        self._all_rows = self._loader.load_checklist(self._last_bosses)
        self._apply_filter(self.search_box.text().strip().lower())

        # Alternate row coloring
        for i in range(self.table.rowCount()):
            bg = QColor(240, 236, 228) if i % 2 else QColor(250, 247, 242)
            for j in range(self.table.columnCount()):
                item = self.table.item(i, j)
                if item:
                    item.setBackground(bg)

    def _on_cell_entered(self, row, col):
        if row < 0 or row >= self.table.rowCount():
            return

        map_item = self.table.item(row, 1)
        if not map_item:
            return
            
        map_name = map_item.text()
        
        boss_item = self.table.item(row, 0)
        boss_text = boss_item.text() if boss_item else ""
        boss_name = boss_text.split(" (")[0] if " (" in boss_text else boss_text
        
        lv_item = self.table.item(row, 2)
        map_lv = lv_item.text() if lv_item else ""

        if not map_name or map_name == "--":
            self._popup.hide()
            return

        self._popup.set_map_data(map_name, map_lv, False, boss_name)

        index = self.table.model().index(row, 0)
        rect = self.table.visualRect(index)
        popup_pos = self.table.viewport().mapToGlobal(rect.topLeft())
        popup_pos.setY(popup_pos.y() - self._popup.height() - 8)

        self._popup.show_at(popup_pos)

    def eventFilter(self, source, event):
        if hasattr(self, 'table') and source == self.table.viewport():
            if event.type() == event.Type.Leave:
                if hasattr(self, '_popup'):
                    self._popup.hide()
        return super().eventFilter(source, event)

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
