from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt

class PodPage(QFrame):
    """POD mode placeholder page."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "chart-frame")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("POD Mode")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #f38ba8;")
        layout.addWidget(title)

        info = QLabel("Print on Demand interface coming soon...")
        info.setStyleSheet("font-size: 14px; color: #a6adc8; margin-top: 12px;")
        layout.addWidget(info)
