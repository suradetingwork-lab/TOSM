"""Main overlay window — transparent, always-on-top boss tracker."""

import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable

from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QPoint, QEvent, QRect,
    QPropertyAnimation, QEasingCurve, QAbstractAnimation,
)
from PyQt6.QtGui import QColor, QFont, QMouseEvent, QCursor
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
    QSlider,
    QLineEdit,
    QGraphicsDropShadowEffect,
)
import winsound

from ..map_level import get_boss_info
from .widgets import SortableHeaderButton
from .boss_row import BossRow
from .summary_stats import SummaryStatsBar


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
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'boss_data.json'
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

        self._search_debounce = QTimer()
        self._search_debounce.setSingleShot(True)
        self._search_debounce.setInterval(300)
        self._search_debounce.timeout.connect(self._apply_search_filter)

        self._boss_data: List[Dict[str, Any]] = []
        self._reset_boss_data()
        self.resize(820, self._collapsed_height)
        self._urgent_notified = set()
        
        if hasattr(self, '_summary_bar'):
            self._summary_bar.refresh(self._boss_data)

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
                color: #1A5A80;
                background: rgba(54, 104, 141, 0.18);
                border: 1px solid rgba(54, 104, 141, 0.45);
                border-radius: 12px;
                padding: 3px 14px;
                font-weight: 700;
            }
        """
        inactive_style = """
            QPushButton {
                color: #A89880;
                background: transparent;
                border: 1px solid rgba(189, 165, 137, 0.20);
                border-radius: 12px;
                padding: 3px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                color: #1A2A38;
                background: rgba(54, 104, 141, 0.08);
                border: 1px solid rgba(54, 104, 141, 0.25);
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
            "1-10": (1, 10),
            "11-20": (11, 20),
            "21-30": (21, 30),
            "31-40": (31, 40),
            "41-50": (41, 50),
            "51-60": (51, 60),
            "61-70": (61, 70),
            "71-80": (71, 80),
            "81-90": (81, 90),
            "91-100": (91, 100),
            "101-110": (101, 110),
            "111-120": (111, 120),
            "121-130": (121, 130),
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
        self._search_filter = text.strip().lower()
        self._search_debounce.stop()
        self._search_debounce.start()

    def _apply_search_filter(self) -> None:
        sorted_bosses = self._sort_bosses(self._boss_data)
        self._update_display(sorted_bosses)

    def _filter_by_name(self, bosses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self._search_filter:
            return bosses
        q = self._search_filter
        return [b for b in bosses if q in b.get('name', '').lower()]

    def _load_initial_data(self) -> None:
        return

    def _load_ui_state(self) -> bool:
        try:
            state_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ui_state.json")
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
                if hasattr(self, '_summary_bar'):
                    self._summary_bar.refresh(self._boss_data)
                return True
            return False
        except Exception:
            return False

    def _save_ui_state(self) -> None:
        try:
            state_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ui_state.json")
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
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(54, 104, 141, 60))
        shadow.setOffset(0, 4)
        self.central_widget.setGraphicsEffect(shadow)

        self.central_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0.2, y2: 1,
                    stop: 0 rgba(245, 240, 232, 0.97),
                    stop: 1 rgba(238, 232, 222, 0.98)
                );
                border-radius: 14px;
                border: 1px solid rgba(54, 104, 141, 0.30);
            }
        """)

        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(14, 12, 14, 12)
        self.layout.setSpacing(6)

        # ── Summary stats bar ──────────────────────────────────────
        self._summary_bar = SummaryStatsBar()

        # ── Search / filter box ────────────────────────────────────
        search_container = QWidget()
        search_container.setStyleSheet("background: transparent; border: none;")
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(8, 0, 8, 0)
        search_layout.setSpacing(8)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Filter bosses...")
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
                background: rgba(255, 255, 255, 0.90);
            }
        """)
        self.search_box.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_box)

        self.filter_count_label = QLabel("")
        self.filter_count_label.setFont(QFont("Segoe UI", 8))
        self.filter_count_label.setStyleSheet("color: #A89880; background: transparent;")
        self.filter_count_label.setFixedWidth(100)
        self.filter_count_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.filter_count_label.setVisible(False)
        search_layout.addWidget(self.filter_count_label)

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
                header.setStyleSheet("color: #8A7A68; background: transparent; letter-spacing: 0.5px;")
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
                background: rgba(54, 104, 141, 0.06);
                width: 6px;
                margin: 4px 0;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(54, 104, 141, 0.30);
                border-radius: 3px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(54, 104, 141, 0.55);
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
        div1.setStyleSheet("background: rgba(54, 104, 141, 0.12); border: none;")

        # ── Tab bar ────────────────────────────────────────────────
        tab_container = QWidget()
        tab_container.setStyleSheet("background: transparent; border: none;")
        tab_layout = QHBoxLayout(tab_container)
        tab_layout.setContentsMargins(0, 2, 0, 2)
        tab_layout.setSpacing(6)
        tab_layout.addStretch()

        for tab_key, tab_label in [("all", "All"), ("1-10", "1-10"), ("11-20", "11-20"), ("21-30", "21-30"), ("31-40", "31-40"), ("41-50", "41-50"), ("51-60", "51-60"), ("61-70", "61-70"), ("71-80", "71-80"), ("81-90", "81-90"), ("91-100", "91-100"), ("101-110", "101-110"), ("111-120", "111-120"), ("121-130", "121-130")]:
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
            background: rgba(255, 255, 255, 0.55);
            border-radius: 8px;
            border: 1px solid rgba(54, 104, 141, 0.18);
        """)
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(10, 5, 10, 5)
        status_layout.setSpacing(8)

        self.status_label = QLabel("◎  Ready — Alt+1 to scan")
        self.status_label.setFont(QFont("Segoe UI", 9))
        self.status_label.setStyleSheet("color: #8A7A68; background: transparent;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.setStyleSheet("""
            QPushButton {
                color: #8A7A68;
                background: transparent;
                border: 1px solid rgba(189, 165, 137, 0.35);
                border-radius: 6px;
                padding: 4px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                color: #8B5E00;
                background: rgba(244, 159, 5, 0.10);
                border: 1px solid rgba(244, 159, 5, 0.40);
            }
            QPushButton:pressed {
                background: rgba(244, 159, 5, 0.22);
            }
        """)
        self.reset_btn.clicked.connect(self._reset_boss_data)
        status_layout.addWidget(self.reset_btn)

        # ── Divider ────────────────────────────────────────────────
        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.HLine)
        div2.setFixedHeight(1)
        div2.setStyleSheet("background: rgba(54, 104, 141, 0.12); border: none;")

        # ── Title bar ──────────────────────────────────────────────
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(4, 2, 4, 2)
        header_layout.setSpacing(6)

        title_dot = QLabel("◆")
        title_dot.setFont(QFont("Segoe UI", 9))
        title_dot.setStyleSheet("color: #D4860A; background: transparent;")
        header_layout.addWidget(title_dot)

        self.title_label = QLabel("Boss Tracker")
        self.title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #1A2A38; background: transparent;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        # Opacity control
        opacity_label = QLabel("○")
        opacity_label.setFont(QFont("Segoe UI", 10))
        opacity_label.setStyleSheet("color: #A89880; background: transparent;")
        header_layout.addWidget(opacity_label)

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(20, 100)
        self.opacity_slider.setValue(int(self._base_opacity * 100))
        self.opacity_slider.setFixedWidth(72)
        self.opacity_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border-radius: 2px;
                height: 3px;
                background: rgba(54, 104, 141, 0.20);
            }
            QSlider::handle:horizontal {
                background: #36688D;
                width: 10px;
                height: 10px;
                margin: -4px 0;
                border-radius: 5px;
            }
            QSlider::sub-page:horizontal {
                background: rgba(54, 104, 141, 0.55);
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
                color: #8A7A68;
                background: transparent;
                border: 1px solid rgba(189, 165, 137, 0.30);
                border-radius: 6px;
            }
            QPushButton:hover {
                color: #1A2A38;
                background: rgba(54, 104, 141, 0.08);
                border: 1px solid rgba(54, 104, 141, 0.30);
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
                color: #8A7A68;
                background: transparent;
                border: 1px solid rgba(189, 165, 137, 0.30);
                border-radius: 6px;
            }
            QPushButton:hover {
                color: #8B5E00;
                background: rgba(243, 205, 5, 0.12);
                border: 1px solid rgba(243, 205, 5, 0.40);
            }
            QPushButton:pressed {
                background: rgba(243, 205, 5, 0.22);
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
                color: #8A7A68;
                background: transparent;
                border: 1px solid rgba(189, 165, 137, 0.30);
                border-radius: 6px;
            }
            QPushButton:hover {
                color: #1A2A38;
                background: rgba(54, 104, 141, 0.08);
                border: 1px solid rgba(54, 104, 141, 0.30);
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
                color: #8A7A68;
                background: transparent;
                border: 1px solid rgba(189, 165, 137, 0.30);
                border-radius: 6px;
            }
            QPushButton:hover {
                color: #1A2A38;
                background: rgba(54, 104, 141, 0.08);
                border: 1px solid rgba(54, 104, 141, 0.30);
            }
        """)
        self.maximize_btn.clicked.connect(self._maximize_window)
        header_layout.addWidget(self.maximize_btn)

        self.drag_hint = QLabel("Alt+Drag")
        self.drag_hint.setFont(QFont("Segoe UI", 8))
        self.drag_hint.setStyleSheet("color: #C8B8A8; background: transparent;")
        header_layout.addWidget(self.drag_hint)

        # ── Assemble layout ────────────────────────────────────────
        self.layout.addWidget(self._summary_bar)
        self.layout.addWidget(search_container)
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
                background: rgba(54, 104, 141, 0.15);
                border: 1px solid rgba(54, 104, 141, 0.30);
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
                    color: #1A5A80;
                    background: rgba(54, 104, 141, 0.14);
                    border: 1px solid rgba(54, 104, 141, 0.40);
                    border-radius: 6px;
                    font-weight: 700;
                }
            """)
        else:
            self.lock_btn.setText("Auto")
            self.lock_btn.setStyleSheet("""
                QPushButton {
                    color: #8A7A68;
                    background: transparent;
                    border: 1px solid rgba(189, 165, 137, 0.30);
                    border-radius: 6px;
                }
                QPushButton:hover {
                    color: #1A2A38;
                    background: rgba(54, 104, 141, 0.08);
                }
            """)

    def _toggle_stats_window(self) -> None:
        from ..stats_window import StatsPopupWindow
        if self._stats_window is None:
            self._stats_window = StatsPopupWindow(self._boss_data_path, parent=None)
        if self._stats_window.isVisible():
            self._stats_window.hide()
        else:
            geo = self.geometry()
            self._stats_window.move(geo.x() + geo.width() + 12, geo.y())
            self._stats_window.show()
            self._stats_window.refresh(self._boss_data)

    def _change_opacity(self, value):
        self._base_opacity = value / 100.0
        if not self.underMouse():
            self.setWindowOpacity(self._base_opacity)

    def refresh_stats_window(self) -> None:
        """Refresh the stats/checklist window if it exists."""
        if self._stats_window is not None:
            self._stats_window.refresh(self._boss_data)

    def show_snapshot_feedback(self) -> None:
        self.status_label.setText("◎  Scanning...")
        self.status_label.setStyleSheet("color: #B8860B; background: transparent;")
        self.repaint()

    def update_status(self, message: str) -> None:
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: #1A5A80; background: transparent;")

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
            self._summary_bar.refresh(self._boss_data)
        if self._stats_window is not None and self._stats_window.isVisible():
            self._stats_window.refresh(self._boss_data)

    def _auto_sort_bosses(self) -> None:
        if not self._boss_data:
            return
        sorted_bosses = self._sort_bosses(self._boss_data)
        self._update_display(sorted_bosses)

    def _update_display(self, sorted_bosses: List[Dict[str, Any]]) -> None:
        sorted_bosses = self._filter_by_tab(sorted_bosses)
        tab_filtered = sorted_bosses

        sorted_bosses = self._filter_by_name(sorted_bosses)

        if hasattr(self, 'filter_count_label'):
            if self._search_filter:
                def _has_data(b):
                    s = b.get('status', 'N')
                    cd = b.get('countdown', '')
                    return (
                        (b.get('time_display') and b.get('time_display') != '--') or
                        (cd and cd != '') or
                        (s and s not in ['N', '-', '--']) or
                        (b.get('last_updated') and b.get('last_updated') != '')
                    )
                total = sum(1 for b in tab_filtered if _has_data(b))
                shown = sum(1 for b in sorted_bosses if _has_data(b))
                self.filter_count_label.setText(f"{shown} of {total} bosses")
                self.filter_count_label.setVisible(True)
            else:
                self.filter_count_label.setVisible(False)

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
                minutes_elapsed = None
                last_updated_dt_val = None
                if status != "-" and status != "--":
                    last_updated = b.get('last_updated', '')
                    if last_updated:
                        try:
                            dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                            update_date = dt.strftime("%H:%M")
                            now = datetime.now()
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=now.tzinfo)
                            elapsed = now - dt
                            minutes_elapsed = int(elapsed.total_seconds() / 60)
                            last_updated_dt_val = dt.replace(tzinfo=None)
                        except:
                            update_date = datetime.now().strftime("%H:%M")
                            minutes_elapsed = 0
                    else:
                        update_date = datetime.now().strftime("%H:%M")
                        minutes_elapsed = 0

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
                if last_updated_dt_val is not None:
                    row.set_update_date(update_date, minutes_elapsed, last_updated_dt_val)
                elif minutes_elapsed is not None:
                    row.set_update_date(update_date, minutes_elapsed)
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
        self.status_label.setStyleSheet("color: #B8860B; background: transparent;")

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

        if matched is None and not target_ch:
            for boss in self._boss_data:
                if boss.get('name', '').lower() == target_name:
                    matched = boss
                    break

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
            state_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ui_state.json")
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
            row.update_elapsed_display()
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
