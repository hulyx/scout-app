from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QFormLayout, QComboBox, QMessageBox, QSpinBox,
)
from PyQt6.QtCore import Qt

from scout.gui.widgets.data_table import DataTable
from scout.gui.workers.pod_workers import PodFindForMeWorker


POD_SEEDS_COLUMNS = [
    "row_num", "seed", "category", "source",
]

POD_SEEDS_DISPLAY_NAMES = {
    "row_num": "#",
    "seed": "Seed Keyword",
    "category": "Category",
    "source": "Source",
}


class PodSeedsPage(QWidget):
    """Page for generating POD seeds by category."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._keywords_data = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = QLabel("<h2>🌱 POD Seeds</h2>")
        layout.addWidget(header)

        # Category selector
        category_group = QGroupBox("Generate Seeds")
        category_layout = QFormLayout(category_group)

        self._category_combo = QComboBox()
        self._category_combo.addItems([
            "All", "Professions", "Animals", "Family",
            "Hobbies", "Humor", "Holidays", "Sports",
            "Geographic", "Lifestyle",
        ])
        category_layout.addRow("Category:", self._category_combo)

        self._limit_spin = QSpinBox()
        self._limit_spin.setRange(5, 50)
        self._limit_spin.setValue(10)
        category_layout.addRow("Limit per category:", self._limit_spin)

        layout.addWidget(category_group)

        # Buttons
        btn_layout = QHBoxLayout()

        self._generate_btn = QPushButton("🌱 Generate Seeds")
        self._generate_btn.setProperty("class", "btn-primary")
        self._generate_btn.clicked.connect(self._generate_seeds)
        btn_layout.addWidget(self._generate_btn)

        btn_layout.addStretch()

        self._send_btn = QPushButton("⛏ Send to Keywords")
        self._send_btn.clicked.connect(self._send_to_keywords)
        btn_layout.addWidget(self._send_btn)

        layout.addLayout(btn_layout)

        # Results table
        self._table = DataTable()
        self._table._model._columns = POD_SEEDS_COLUMNS
        self._table._model._display_names = POD_SEEDS_DISPLAY_NAMES
        layout.addWidget(self._table, 1)

    def _generate_seeds(self):
        from scout.pod_seeds import get_all_seeds, expand_seed

        category = self._category_combo.currentText().lower()
        limit = self._limit_spin.value()

        seeds = get_all_seeds(category=category, limit_per_category=limit)

        self._keywords_data = []
        for seed in seeds:
            expanded = expand_seed(seed, depth=2)
            for kw in expanded:
                self._keywords_data.append({
                    "seed": kw,
                    "category": category.capitalize() if category != "all" else "Mixed",
                    "source": "generated",
                })

        self._populate_table()
        QMessageBox.information(
            self, "Seeds Generated",
            f"Generated {len(self._keywords_data)} seeds."
        )

    def _populate_table(self):
        data = []
        for i, kw in enumerate(self._keywords_data, 1):
            row = {
                "row_num": i,
                "seed": kw.get("seed", ""),
                "category": kw.get("category", ""),
                "source": kw.get("source", ""),
            }
            data.append(row)
        self._table.load_data(data)

    def _send_to_keywords(self):
        if not self._keywords_data:
            QMessageBox.warning(self, "No Data", "Please generate seeds first.")
            return

        # Placeholder - will navigate to pod_keywords_page with seeds
        QMessageBox.information(
            self, "Send to Keywords",
            f"Will send {len(self._keywords_data)} keywords to Keywords page."
        )
