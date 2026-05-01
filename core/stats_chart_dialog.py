"""Matplotlib-based statistics chart dialog for boss spawn analytics."""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QLabel, QTabWidget, QFrame
)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt


class BossStatsLoader:
    """Reads boss_data.json and returns structured stats for charting."""

    def __init__(self, data_path: str):
        self._path = Path(data_path)

    def _load(self) -> Dict[str, Any]:
        try:
            with open(self._path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def top_bosses_by_spawn_count(self, n: int = 10) -> List[Tuple[str, int]]:
        """Returns list of (boss_name, total_spawn_count) sorted descending, grouped by name."""
        raw = self._load()
        from collections import defaultdict
        counts: Dict[str, int] = defaultdict(int)
        for entry in raw.values():
            name = entry.get('name', '').strip()
            if name:
                counts[name] += entry.get('spawn_count', 0)
        sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_items[:n]

    def spawn_events_last_24h(self) -> List[datetime]:
        """Returns sorted list of detected_at datetimes within the last 24 hours."""
        raw = self._load()
        cutoff = datetime.now() - timedelta(hours=24)
        events: List[datetime] = []
        for entry in raw.values():
            for loc in entry.get('locations', {}).values():
                for record in loc.get('spawn_history', []):
                    detected_str = record.get('detected_at')
                    if not detected_str:
                        continue
                    try:
                        dt = datetime.fromisoformat(detected_str.replace('Z', '+00:00'))
                        if dt >= cutoff:
                            events.append(dt)
                    except (ValueError, TypeError):
                        pass
        events.sort()
        return events

    def channel_distribution(self) -> List[Tuple[str, int]]:
        """Returns list of (channel, boss_count) sorted descending."""
        raw = self._load()
        from collections import defaultdict
        counts: Dict[str, int] = defaultdict(int)
        for entry in raw.values():
            channel = entry.get('channel') or ''
            channel = channel.strip()
            if channel and channel not in ('-', '--'):
                counts[channel] += 1
        return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:15]

    def hourly_spawn_distribution(self) -> List[int]:
        """Returns list of spawn counts per hour (0-23) for last 24h."""
        events = self.spawn_events_last_24h()
        hourly = [0] * 24
        for dt in events:
            hourly[dt.hour] += 1
        return hourly


class ChartWidget(QWidget):
    """Base widget for matplotlib charts."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(8, 5), dpi=100)
        self.figure.patch.set_facecolor('#0a0c18')
        self.canvas = FigureCanvas(self.figure)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)

    def clear(self):
        self.figure.clear()


class BossRankingChart(ChartWidget):
    """Horizontal bar chart of top bosses by spawn count."""

    def update_chart(self, data: List[Tuple[str, int]]):
        self.clear()
        if not data:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center',
                   transform=ax.transAxes, color='#64748B', fontsize=12)
            ax.set_facecolor('#0a0c18')
            ax.axis('off')
            self.canvas.draw()
            return

        names = [item[0] for item in data]
        counts = [item[1] for item in data]

        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#0a0c18')

        colors = plt.cm.viridis([0.7 - i * 0.07 for i in range(len(data))])
        bars = ax.barh(range(len(names)), counts, color=colors, height=0.7)

        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names, color='#94A3B8', fontsize=9)
        ax.tick_params(axis='x', colors='#64748B')
        ax.spines['bottom'].set_color('#334155')
        ax.spines['left'].set_color('#334155')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        ax.set_xlabel('Spawn Count', color='#64748B', fontsize=10)
        ax.set_title('Top Bosses by Spawn Count', color='#E2E8F0', fontsize=12, fontweight='bold', pad=15)

        for i, (bar, count) in enumerate(zip(bars, counts)):
            ax.text(count + 0.5, i, str(count), va='center', color='#E2E8F0', fontsize=9)

        ax.invert_yaxis()
        self.canvas.draw()


class HourlyDistributionChart(ChartWidget):
    """Bar chart of spawn events by hour of day."""

    def update_chart(self, hourly_data: List[int]):
        self.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#0a0c18')

        hours = list(range(24))
        colors = ['#6366F1' if c > 0 else '#1E293B' for c in hourly_data]

        bars = ax.bar(hours, hourly_data, color=colors, width=0.8)

        ax.set_xlabel('Hour of Day', color='#64748B', fontsize=10)
        ax.set_ylabel('Spawn Events', color='#64748B', fontsize=10)
        ax.set_title('Spawn Activity (Last 24 Hours)', color='#E2E8F0', fontsize=12, fontweight='bold', pad=15)

        ax.tick_params(axis='x', colors='#64748B')
        ax.tick_params(axis='y', colors='#64748B')
        ax.spines['bottom'].set_color('#334155')
        ax.spines['left'].set_color('#334155')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        ax.set_xticks([0, 6, 12, 18, 23])
        ax.set_xticklabels(['00:00', '06:00', '12:00', '18:00', '23:00'])

        self.canvas.draw()


class ChannelDistributionChart(ChartWidget):
    """Pie chart of boss distribution by channel."""

    def update_chart(self, data: List[Tuple[str, int]]):
        self.clear()
        if not data:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center',
                   transform=ax.transAxes, color='#64748B', fontsize=12)
            ax.set_facecolor('#0a0c18')
            ax.axis('off')
            self.canvas.draw()
            return

        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#0a0c18')

        channels = [item[0] for item in data[:8]]  # Top 8 channels
        counts = [item[1] for item in data[:8]]

        colors = plt.cm.viridis([i * 0.12 for i in range(len(channels))])

        wedges, texts, autotexts = ax.pie(counts, labels=channels, autopct='%1.1f%%',
                                           colors=colors, startangle=90)

        for text in texts:
            text.set_color('#94A3B8')
        for autotext in autotexts:
            autotext.set_color('#0a0c18')
            autotext.set_fontweight('bold')

        ax.set_title('Channel Distribution', color='#E2E8F0', fontsize=12, fontweight='bold', pad=15)

        self.canvas.draw()


class StatsChartDialog(QDialog):
    """Dialog window for displaying matplotlib-based boss statistics charts."""

    def __init__(self, data_path: str, parent=None):
        super().__init__(parent)
        self._loader = BossStatsLoader(data_path)
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        self.setWindowTitle("Boss Spawn Analytics")
        self.setMinimumSize(900, 600)
        self.setStyleSheet("""
            QDialog {
                background: #0a0c18;
            }
            QTabWidget::pane {
                border: 1px solid #334155;
                background: #0a0c18;
            }
            QTabBar::tab {
                background: #1e293b;
                color: #94A3B8;
                padding: 8px 20px;
                border: none;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background: #6366F1;
                color: #E2E8F0;
            }
            QTabBar::tab:hover:!selected {
                background: #334155;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Header
        header = QLabel("📊 Boss Spawn Analytics")
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header.setStyleSheet("color: #E2E8F0; margin-bottom: 10px;")
        layout.addWidget(header)

        # Tab widget
        self.tabs = QTabWidget()

        # Tab 1: Boss Ranking
        self.ranking_tab = BossRankingChart()
        self.tabs.addTab(self.ranking_tab, "Boss Ranking")

        # Tab 2: Hourly Distribution
        self.hourly_tab = HourlyDistributionChart()
        self.tabs.addTab(self.hourly_tab, "Hourly Activity")

        # Tab 3: Channel Distribution
        self.channel_tab = ChannelDistributionChart()
        self.tabs.addTab(self.channel_tab, "Channels")

        layout.addWidget(self.tabs)

        # Refresh button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #6366F1;
                color: #E2E8F0;
                border: none;
                padding: 8px 20px;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #818CF8;
            }
        """)
        refresh_btn.clicked.connect(self.refresh)
        btn_layout.addWidget(refresh_btn)

        close_btn = QPushButton("Close")
        close_btn.setFont(QFont("Segoe UI", 9))
        close_btn.setStyleSheet("""
            QPushButton {
                background: #334155;
                color: #94A3B8;
                border: none;
                padding: 8px 20px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #475569;
            }
        """)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def refresh(self):
        """Refresh all charts with latest data."""
        ranking_data = self._loader.top_bosses_by_spawn_count(10)
        self.ranking_tab.update_chart(ranking_data)

        hourly_data = self._loader.hourly_spawn_distribution()
        self.hourly_tab.update_chart(hourly_data)

        channel_data = self._loader.channel_distribution()
        self.channel_tab.update_chart(channel_data)
