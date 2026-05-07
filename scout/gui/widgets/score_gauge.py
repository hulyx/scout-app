"""Score gauge widget for displaying numeric scores visually."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class ScoreGauge(QWidget):
    """A simple score display widget (gauge-like)."""

    def __init__(self, score=0, max_score=100, parent=None):
        super().__init__(parent)
        try:
            self._score = float(score)
        except (ValueError, TypeError):
            self._score = 0.0
        self._max_score = max_score
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._score_label = QLabel(f"{self._score:.0f}")
        self._score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._score_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self._score_label.setStyleSheet("color: #cba6f7;")
        layout.addWidget(self._score_label)

        self._label = QLabel("Score")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("color: #6c7086; font-size: 11px;")
        layout.addWidget(self._label)

    def set_score(self, score):
        self._score = score
        self._score_label.setText(f"{score:.0f}")
        # Color based on score
        if score >= 80:
            color = "#a6e3a1"  # green
        elif score >= 60:
            color = "#f9e2af"  # yellow
        elif score >= 40:
            color = "#fab387"  # orange
        else:
            color = "#f38ba8"  # red
        self._score_label.setStyleSheet(f"color: {color};")

    def set_label(self, text):
        self._label.setText(text)
