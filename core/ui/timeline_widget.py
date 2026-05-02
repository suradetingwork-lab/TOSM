"""Timeline widgets for Boss Statistics popup (Checklist | Timeline)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPolygon
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


# ───────────────────────── helpers ─────────────────────────


def _try_parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            return None
    return None


def _norm_boss_name(name: str) -> str:
    return (name or "").strip().lower()


def _norm_channel(channel: str) -> str:
    """Normalize channel strings so 'CH.1', 'CH. 1', 'CH 1' compare equal."""
    ch = (channel or "").strip().upper()
    ch = ch.replace(" ", "")
    if ch.startswith("CH") and not ch.startswith("CH."):
        ch = "CH." + ch[2:]
    return ch


def _has_scan_data(b: Dict[str, Any]) -> bool:
    s = b.get("status", "N")
    cd = b.get("countdown", "")
    return (
        (b.get("time_display") and b.get("time_display") != "--")
        or (cd and cd != "")
        or (s and s not in ["N", "-", "--"])
        or (b.get("last_updated") and b.get("last_updated") != "")
    )


def _status_to_current_phase(status: str) -> int:
    """Map status -> current_phase index.

    0  = pre-spawn (status 'N')
    1..4 = LV1..LV4
    5  = Active (engaged after all phases)
    """
    s = (status or "").strip()
    if s == "N":
        return 0
    if s.startswith("LV"):
        try:
            n = int(s[2:])
        except Exception:
            return 0
        return max(1, min(n, 4))
    if s.lower() == "active":
        return 5
    return 0


# Global shared state so BossRow popups and TimelineView stay perfectly synchronized
_GLOBAL_PHASE_CACHE: Dict[Tuple[str, str, datetime], Dict[int, datetime]] = {}
_GLOBAL_SYNTHETIC_SPAWN: Dict[Tuple[str, str], datetime] = {}


def _extract_phase_times_current_cycle(
    record: Optional[Dict[str, Any]],
    spawn_time: Optional[datetime],
    current_phase: int,
) -> Dict[int, datetime]:
    """Return phase transition times for the *current* spawn cycle.

    - P1 is anchored to ``spawn_time`` (live tracker value), since spawn IS
      the start of phase 1.
    - P2..P_current_phase use the earliest ``detected_at`` in spawn_history
      that is on/after ``spawn_time`` (with a small clock-drift buffer).
    - Phases beyond ``current_phase`` are *not* included (caller is expected
      to render only what has happened so far).
    """
    pts: Dict[int, datetime] = {}
    if not spawn_time or current_phase < 1:
        return pts

    pts[1] = spawn_time
    if current_phase < 2:
        return pts

    drift = timedelta(minutes=2)
    cycle_entries: List[Tuple[datetime, str]] = []
    for loc in (record or {}).get("locations", {}).values():
        for entry in (loc or {}).get("spawn_history", []):
            t = _try_parse_dt(entry.get("detected_at") if isinstance(entry, dict) else None)
            if t and t >= spawn_time - drift:
                cycle_entries.append((t, (entry or {}).get("status") or ""))
    cycle_entries.sort(key=lambda x: x[0])

    upper = min(current_phase, 4)
    for lv in range(2, upper + 1):
        target = f"LV{lv}"
        for t, s in cycle_entries:
            if s == target:
                pts[lv] = t
                break
    return pts


def build_timeline_model(
    raw_boss: Dict[str, Any],
    record: Optional[Dict[str, Any]],
    now: datetime
) -> Optional['TimelineRowModel']:
    """Construct a TimelineRowModel from live tracking data and persistent history.
    Uses a shared cache to maintain phase timestamps and stable synthetic spawn times.
    """
    name = (raw_boss.get("name") or "").strip()
    if not name:
        return None
    channel = raw_boss.get("channel", "--") or "--"
    status = raw_boss.get("status", "N") or "N"
    boss_type = raw_boss.get("type", "") or ""
    map_name = raw_boss.get("map", "") or ""

    spawn_time = _try_parse_dt(raw_boss.get("spawn_time"))
    current_phase = _status_to_current_phase(status)

    key_id: Tuple[str, str] = (_norm_boss_name(name), _norm_channel(channel))

    if not spawn_time:
        spawn_time = _GLOBAL_SYNTHETIC_SPAWN.setdefault(key_id, now)
    else:
        _GLOBAL_SYNTHETIC_SPAWN.pop(key_id, None)

    cache_key: Tuple[str, str, datetime] = (key_id[0], key_id[1], spawn_time)

    fresh = _extract_phase_times_current_cycle(record, spawn_time, current_phase)

    cached = _GLOBAL_PHASE_CACHE.get(cache_key, {})
    merged: Dict[int, datetime] = dict(cached)
    for ph, t in fresh.items():
        merged.setdefault(ph, t)  # cached value wins; new value fills gaps
    _GLOBAL_PHASE_CACHE[cache_key] = merged
    phase_times = merged

    return TimelineRowModel(
        name=name,
        boss_type=boss_type,
        map_name=map_name,
        channel=channel,
        status=status,
        spawn_time=spawn_time,
        phase_times=phase_times,
        current_phase=current_phase,
    )


# ───────────────────────── data model ─────────────────────────


@dataclass(frozen=True)
class TimelineRowModel:
    name: str
    boss_type: str
    map_name: str
    channel: str
    status: str
    spawn_time: Optional[datetime]
    phase_times: Dict[int, datetime] = field(default_factory=dict)
    current_phase: int = 0


# ───────────────────────── canvas (custom paint) ─────────────────────────


class _TimelineCanvas(QFrame):
    _CANVAS_HEIGHT = 130  # Increased slightly to prevent label clipping

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(self._CANVAS_HEIGHT)
        self.setMinimumHeight(self._CANVAS_HEIGHT)
        self._model: Optional[TimelineRowModel] = None
        self._now = datetime.now()

    def set_model(self, model: TimelineRowModel) -> None:
        self._model = model
        self.update()

    def update_now(self) -> None:
        self._now = datetime.now()
        self.update()

    # ── range ────────────────────────────────────────────────
    def _compute_range(self) -> Tuple[datetime, datetime]:
        now = self._now
        model = self._model

        if not model:
            start = (now - timedelta(minutes=5)).replace(second=0, microsecond=0)
            end = (now + timedelta(minutes=90)).replace(second=0, microsecond=0)
            return (start, end)

        # Range start should be first stamp time - 5m (small visual gap).
        stamps: List[datetime] = []
        if model.spawn_time:
            stamps.append(model.spawn_time)
        for t in (model.phase_times or {}).values():
            if t:
                stamps.append(t)
        if not stamps:
            stamps.append(now)

        first_stamp = min(stamps)
        start = (first_stamp - timedelta(minutes=5)).replace(second=0, microsecond=0)

        known_times = [t for t in model.phase_times.values() if t]
        last_known = max(known_times + [now]) if known_times else now
        anchor = model.spawn_time or model.phase_times.get(1) or first_stamp
        end = max(
            (last_known + timedelta(minutes=45)).replace(second=0, microsecond=0),
            (anchor + timedelta(hours=1, minutes=30)).replace(second=0, microsecond=0),
        )

        if end <= start:
            end = start + timedelta(hours=2)
        return (start, end)

    # ── painting ─────────────────────────────────────────────
    def paintEvent(self, event) -> None:  # noqa: N802 (Qt API)
        super().paintEvent(event)
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            self._paint(p)
        finally:
            p.end()

    def _paint(self, p: QPainter) -> None:
        rect = self.rect()
        left_pad = 18
        right_pad = 22
        top_pad = 6
        bottom_pad = 6

        # Axis sits a bit below center to leave room for two-line phase labels above.
        y_axis = rect.top() + top_pad + 56
        x0 = rect.left() + left_pad
        x1 = rect.right() - right_pad
        if x1 <= x0:
            return

        t_start, t_end = self._compute_range()
        total_seconds = max(1.0, (t_end - t_start).total_seconds())

        def time_to_x(t: datetime) -> int:
            s = (t - t_start).total_seconds()
            ratio = max(0.0, min(1.0, s / total_seconds))
            return int(x0 + ratio * (x1 - x0))

        # ── axis line + arrow head ────────────────────────────
        axis_pen = QPen(QColor(60, 80, 100, 180), 1)
        p.setPen(axis_pen)
        p.drawLine(x0, y_axis, x1, y_axis)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(60, 80, 100, 200))
        ah = 6
        p.drawPolygon(
            QPolygon([
                QPoint(x1 + 6, y_axis),
                QPoint(x1 - ah, y_axis - 4),
                QPoint(x1 - ah, y_axis + 4),
            ])
        )

        # ── 30-minute grid ────────────────────────────────────
        # Snap first tick to the nearest past :00 or :30 boundary.
        tick_time = t_start.replace(second=0, microsecond=0)
        if tick_time.minute >= 30:
            tick_time = tick_time.replace(minute=30)
        else:
            tick_time = tick_time.replace(minute=0)
        if tick_time < t_start:
            tick_time += timedelta(minutes=30)

        tick_step = timedelta(minutes=30)

        grid_pen = QPen(QColor(140, 150, 160, 70), 1)
        grid_label_pen = QPen(QColor(140, 130, 110, 170), 1)
        p.setFont(QFont("Segoe UI", 8))
        while tick_time <= t_end:
            x = time_to_x(tick_time)
            p.setPen(grid_pen)
            p.drawLine(x, y_axis - 4, x, y_axis + 4)
            p.setPen(grid_label_pen)
            p.drawText(
                x - 22,
                y_axis + 6,
                44,
                14,
                Qt.AlignmentFlag.AlignCenter,
                tick_time.strftime("%H:%M"),
            )
            tick_time += tick_step

        model = self._model
        if not model:
            return

        # ── phase markers ─────────────────────────────────────
        # Render only phases up to current_phase (or 1..4 if Active).
        if model.current_phase >= 5:
            phases_to_show = [p_ for p_ in (1, 2, 3, 4) if model.phase_times.get(p_)]
        else:
            phases_to_show = [
                p_ for p_ in range(1, max(1, model.current_phase) + 1)
                if model.phase_times.get(p_)
            ]

        # collision-aware label slots: shorter slot if neighbour <60px away
        marker_xs = {ph: time_to_x(model.phase_times[ph]) for ph in phases_to_show}

        solid_phase_color = QColor(212, 134, 10, 230)        # amber
        ghost_phase_color = QColor(212, 134, 10, 110)        # amber, faded
        phase_label_color = QColor(26, 42, 56, 230)
        phase_time_color = QColor(80, 90, 105, 220)

        # base label baseline above axis
        base_label_y = rect.top() + top_pad          # row 1 (Phase n)
        time_label_y = base_label_y + 14             # row 2 (HH:MM)
        alt_label_y = base_label_y + 28              # alt row 1 if collision
        alt_time_y = alt_label_y + 14                # alt row 2

        sorted_phases = sorted(phases_to_show)
        prev_x: Optional[int] = None
        use_alt: Dict[int, bool] = {}
        for ph in sorted_phases:
            x = marker_xs[ph]
            alt = bool(prev_x is not None and (x - prev_x) < 60)
            use_alt[ph] = alt
            prev_x = x

        for ph in sorted_phases:
            t = model.phase_times[ph]
            x = marker_xs[ph]

            # marker
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(solid_phase_color)
            p.drawEllipse(x - 4, y_axis - 4, 8, 8)

            # text
            y_phase = alt_label_y if use_alt[ph] else base_label_y
            y_time = alt_time_y if use_alt[ph] else time_label_y
            p.setPen(QPen(phase_label_color, 1))
            p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            p.drawText(x - 30, y_phase, 60, 14, Qt.AlignmentFlag.AlignCenter, f"Phase {ph}")
            p.setPen(QPen(phase_time_color, 1))
            p.setFont(QFont("Segoe UI", 8))
            p.drawText(x - 24, y_time, 48, 14, Qt.AlignmentFlag.AlignCenter, t.strftime("%H:%M"))

        # ── ghost marker for status N (Time to Phase 1) ───────
        if model.current_phase == 0 and model.spawn_time:
            x = time_to_x(model.spawn_time)
            # outlined ghost circle
            p.setBrush(QColor(0, 0, 0, 0))
            p.setPen(QPen(ghost_phase_color, 2))
            p.drawEllipse(x - 4, y_axis - 4, 8, 8)

            # one-line label "Time to Phase 1 HH:MM" centered above
            p.setPen(QPen(phase_label_color, 1))
            p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            p.drawText(x - 60, base_label_y, 120, 14,
                       Qt.AlignmentFlag.AlignCenter, "Time to Phase 1")
            p.setPen(QPen(phase_time_color, 1))
            p.setFont(QFont("Segoe UI", 8))
            p.drawText(x - 30, time_label_y, 60, 14,
                       Qt.AlignmentFlag.AlignCenter, model.spawn_time.strftime("%H:%M"))

        # ── time-now marker (always below) ────────────────────
        now = self._now
        now_x = time_to_x(now)
        now_color = QColor(54, 104, 141, 235)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(now_color)
        p.drawEllipse(now_x - 5, y_axis - 5, 10, 10)

        now_label_y = rect.bottom() - bottom_pad - 16
        p.setPen(QPen(QColor(26, 90, 128, 255), 1))
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        p.drawText(
            now_x - 50,
            now_label_y,
            100,
            14,
            Qt.AlignmentFlag.AlignCenter,
            f"Time now {now.strftime('%H:%M')}",
        )


# ───────────────────────── row widget ─────────────────────────


def _build_status_text(model: TimelineRowModel, now: datetime) -> str:
    if model.current_phase == 0:
        if model.spawn_time:
            return (f"Boss ยังไม่เกิด แต่จะเข้า Phase 1 ตอน "
                    f"{model.spawn_time.strftime('%H:%M')}  "
                    f"เวลาปัจจุบัน {now.strftime('%H:%M')}")
        return f"Boss ยังไม่เกิด  เวลาปัจจุบัน {now.strftime('%H:%M')}"

    if 1 <= model.current_phase <= 4:
        t = model.phase_times.get(model.current_phase)
        if t:
            return (f"เริ่ม Phase {model.current_phase} {t.strftime('%H:%M')}  "
                    f"เวลาปัจจุบัน {now.strftime('%H:%M')}")
        return f"เริ่ม Phase {model.current_phase}  เวลาปัจจุบัน {now.strftime('%H:%M')}"

    if model.current_phase >= 5:
        return f"Active  เวลาปัจจุบัน {now.strftime('%H:%M')}"
    return f"{model.status}  เวลาปัจจุบัน {now.strftime('%H:%M')}"


class BossTimelineRow(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            """
            QFrame {
                background: rgba(255, 255, 255, 0.55);
                border: 1px solid rgba(54, 104, 141, 0.16);
                border-radius: 10px;
            }
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(8)

        self._title = QLabel("")
        self._title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self._title.setStyleSheet("color: #1A2A38; background: transparent;")
        top.addWidget(self._title, 1)

        self._status = QLabel("")
        self._status.setFont(QFont("Segoe UI", 9))
        self._status.setStyleSheet("color: #8A7A68; background: transparent;")
        top.addWidget(self._status, 0, Qt.AlignmentFlag.AlignRight)

        layout.addLayout(top)

        self._canvas = _TimelineCanvas()
        self._canvas.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self._canvas)

        self._model: Optional[TimelineRowModel] = None

    def set_model(self, model: TimelineRowModel) -> None:
        self._model = model

        title_bits = [model.name]
        if model.boss_type and model.boss_type != "--":
            title_bits.append(f"({model.boss_type})")
        if model.channel:
            title_bits.append(model.channel)
        if model.map_name and model.map_name != "--":
            title_bits.append(f"— {model.map_name}")
        title_text = " ".join(title_bits)
        self._title.setText(title_text)
        self._title.setToolTip(title_text)

        self._status.setText(_build_status_text(model, datetime.now()))
        self._canvas.set_model(model)

    def update_now(self) -> None:
        if not self._model:
            return
        self._status.setText(_build_status_text(self._model, datetime.now()))
        self._canvas.update_now()


# ───────────────────────── timeline view (scroll list) ─────────────────────────


class TimelineView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent; border: none;")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet(
            """
            QScrollArea { background: transparent; border: none; }
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
            QScrollBar::handle:vertical:hover { background: rgba(54, 104, 141, 0.55); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
            """
        )
        outer.addWidget(self._scroll, 1)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setContentsMargins(6, 6, 6, 6)
        self._content_layout.setSpacing(8)
        self._content_layout.addStretch()
        self._scroll.setWidget(content)

        self._rows: List[BossTimelineRow] = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

        # Stable per-cycle phase timestamps and synthetic spawns moved to module level.

    def _tick(self) -> None:
        for row in self._rows:
            row.update_now()

    def _gc_cache(self) -> None:
        """Remove cache entries older than 24 hours to prevent unbounded growth."""
        cutoff = datetime.now() - timedelta(hours=24)
        global _GLOBAL_PHASE_CACHE, _GLOBAL_SYNTHETIC_SPAWN
        _GLOBAL_PHASE_CACHE = {
            k: v for k, v in _GLOBAL_PHASE_CACHE.items() if k[2] >= cutoff
        }
        _GLOBAL_SYNTHETIC_SPAWN = {
            k: t for k, t in _GLOBAL_SYNTHETIC_SPAWN.items() if t >= cutoff
        }

    def refresh(
        self,
        current_bosses: List[Dict[str, Any]],
        persistent_data: Dict[str, Any],
    ) -> None:
        # Build lookup for persistent boss records with normalized key.
        persistent_lookup: Dict[str, Dict[str, Any]] = {}
        for record in (persistent_data or {}).values():
            try:
                name = _norm_boss_name((record or {}).get("name") or "")
                ch = _norm_channel((record or {}).get("channel") or "")
                if not name:
                    continue
                persistent_lookup[f"{name}_{ch}"] = record
            except Exception:
                continue

        models: List[TimelineRowModel] = []
        now = datetime.now()
        for b in current_bosses or []:
            if not _has_scan_data(b):
                continue

            name = (b.get("name") or "").strip()
            if not name:
                continue
            channel = b.get("channel", "--") or "--"
            key_id: Tuple[str, str] = (_norm_boss_name(name), _norm_channel(channel))
            norm_key = f"{key_id[0]}_{key_id[1]}"
            record = persistent_lookup.get(norm_key)

            model = build_timeline_model(b, record, now)
            if model:
                models.append(model)

        # Stable order: by anchor time (spawn_time / now), then name.
        def _model_sort_key(m: TimelineRowModel):
            t = m.spawn_time or m.phase_times.get(1) or now
            return (t, m.name.lower())

        models.sort(key=_model_sort_key)

        # Rebuild rows.
        for row in self._rows:
            row.setParent(None)
            row.deleteLater()
        self._rows = []

        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        if not models:
            empty = QLabel("No tracked bosses with timeline data yet.")
            empty.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            empty.setStyleSheet("color: #A89880; background: transparent; padding: 10px;")
            self._content_layout.addWidget(empty)
            self._content_layout.addStretch()
            self._gc_cache()
            return

        for m in models:
            row = BossTimelineRow()
            row.set_model(m)
            self._rows.append(row)
            self._content_layout.addWidget(row)
        self._content_layout.addStretch()
        self._gc_cache()
