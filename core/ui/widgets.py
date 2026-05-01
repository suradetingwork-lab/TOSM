"""Reusable atomic UI widgets: sortable header button and star rating."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QPushButton, QWidget, QHBoxLayout


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
