from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QComboBox, QLabel, QMessageBox, QGroupBox, QFormLayout,
    QSpinBox,
)

from scout.gui.widgets.data_table import DataTable
from scout.gui.widgets.progress_panel import ProgressPanel
from scout.gui.workers.pod_workers import PodMineWorker, PodScoreWorker
from scout.gui.search_history import SearchHistory


POD_KEYWORD_COLUMNS = [
    "row_num", "keyword", "score",
    "merch_ac", "etsy_comp", "rb_comp", "pinterest_boards",
    "reddit_demand", "g_trends", "avg_price", "sources",
]

POD_KEYWORD_DISPLAY_NAMES = {
    "row_num": "#",
    "keyword": "Keyword",
    "score": "Score",
    "merch_ac": "Merch AC",
    "etsy_comp": "Etsy Comp.",
    "rb_comp": "RB Comp.",
    "pinterest_boards": "Pinterest",
    "reddit_demand": "Reddit",
    "g_trends": "G.Trends",
    "avg_price": "Avg Price",
    "sources": "Sources",
}

PRODUCT_TYPES = ["All", "T-shirt", "Mug", "Sticker", "Poster", "Hoodie"]
MARKETPLACES = ["US", "UK", "DE", "FR", "CA"]


class PodKeywordsPage(QWidget):
    """Mine POD keywords depuis Amazon Merch autocomplete + Google Suggest."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._keywords_data = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel("<h2>🔍 POD Keywords</h2>")
        header.setStyleSheet("color: #cba6f7;")
        layout.addWidget(header)

        desc = QLabel(
            "Mine les keywords depuis Amazon Merch autocomplete + Google Suggest. "
            "Score basé sur compétition Etsy/Redbubble, Pinterest, Reddit et Google Trends."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #a6adc8; font-size: 12px;")
        layout.addWidget(desc)

        search_group = QGroupBox("Paramètres de recherche")
        search_layout = QFormLayout(search_group)
        search_layout.setSpacing(8)

        self._seed_input = QLineEdit()
        self._seed_input.setPlaceholderText("ex: cat, nurse, funny coffee, dog mom...")
        self._seed_input.returnPressed.connect(self._start_mine)
        search_layout.addRow("Seed keyword :", self._seed_input)

        self._product_combo = QComboBox()
        self._product_combo.addItems(PRODUCT_TYPES)
        search_layout.addRow("Type de produit :", self._product_combo)

        self._marketplace_combo = QComboBox()
        self._marketplace_combo.addItems(MARKETPLACES)
        search_layout.addRow("Marketplace :", self._marketplace_combo)

        self._depth_spin = QSpinBox()
        self._depth_spin.setRange(1, 4)
        self._depth_spin.setValue(2)
        self._depth_spin.setToolTip("Profondeur d'expansion (1=rapide, 3=exhaustif)")
        search_layout.addRow("Depth :", self._depth_spin)

        layout.addWidget(search_group)

        btn_layout = QHBoxLayout()

        self._mine_btn = QPushButton("⛏  Mine Keywords")
        self._mine_btn.setProperty("class", "btn-primary")
        self._mine_btn.clicked.connect(self._start_mine)
        btn_layout.addWidget(self._mine_btn)

        self._score_btn = QPushButton("📊  Score All")
        self._score_btn.setProperty("class", "btn-primary")
        self._score_btn.clicked.connect(self._start_score)
        btn_layout.addWidget(self._score_btn)

        self._export_btn = QPushButton("📤  Export CSV")
        self._export_btn.clicked.connect(self._export_csv)
        btn_layout.addWidget(self._export_btn)

        btn_layout.addStretch()

        self._clear_btn = QPushButton("🗑  Clear")
        self._clear_btn.clicked.connect(self._clear_table)
        btn_layout.addWidget(self._clear_btn)

        layout.addLayout(btn_layout)

        self._table = DataTable()
        layout.addWidget(self._table, 1)

        self._progress = ProgressPanel(show_log=True)
        self._progress.cancel_requested.connect(self._cancel_worker)
        layout.addWidget(self._progress)

    def _start_mine(self):
        seed = self._seed_input.text().strip()
        if not seed:
            QMessageBox.warning(self, "Seed requis", "Veuillez saisir un mot-clé seed.")
            return

        product = self._product_combo.currentText().lower()
        if product == "all":
            product = "all"

        marketplace = self._marketplace_combo.currentText().lower()
        depth = self._depth_spin.value()

        SearchHistory.instance().log(
            tool="POD Keywords",
            action="mine",
            query=seed,
            notes=f"product={product} marketplace={marketplace} depth={depth}",
        )

        self._progress.start()
        self._mine_btn.setEnabled(False)
        self._score_btn.setEnabled(False)

        self._worker = PodMineWorker(
            seed=seed,
            platform="all",
            product_type=product,
            depth=depth,
        )
        self._worker.status.connect(self._progress.set_status)
        self._worker.progress.connect(self._progress.set_progress)
        self._worker.log.connect(self._progress.set_status)
        self._worker.finished_with_result.connect(self._on_mine_finished)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_mine_finished(self, keywords):
        if not keywords:
            keywords = []
        self._progress.finish(f"✅  {len(keywords)} keywords trouvés")
        self._mine_btn.setEnabled(True)
        self._score_btn.setEnabled(True)
        self._keywords_data = keywords
        self._populate_table()
        self._worker = None

    def _start_score(self):
        if not self._keywords_data:
            QMessageBox.warning(self, "Pas de données", "Lancez d'abord un mining.")
            return

        self._progress.start()
        self._score_btn.setEnabled(False)

        self._worker = PodScoreWorker(self._keywords_data)
        self._worker.status.connect(self._progress.set_status)
        self._worker.progress.connect(self._progress.set_progress)
        self._worker.log.connect(self._progress.set_status)
        self._worker.finished_with_result.connect(self._on_score_finished)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_score_finished(self, scored_keywords):
        if not scored_keywords:
            scored_keywords = []
        self._progress.finish(f"✅  {len(scored_keywords)} keywords scorés")
        self._score_btn.setEnabled(True)
        self._keywords_data = scored_keywords
        SearchHistory.instance().log(
            tool="POD Keywords",
            action="score",
            query=self._seed_input.text().strip(),
            results=self._keywords_data,
            result_count=len(self._keywords_data),
        )
        self._populate_table()
        self._worker = None

    def _populate_table(self):
        data = []
        for i, kw in enumerate(self._keywords_data, 1):
            score_val  = kw.get("score", 0) or 0
            reddit_val = kw.get("reddit_score", 0) or 0
            trends_val = kw.get("google_trends_score", 0) or 0
            price_val  = kw.get("avg_price", 0) or 0
            row = {
                "row_num":          i,
                "keyword":          kw.get("keyword", ""),
                "score":            f"{score_val:.2f}",
                "merch_ac":         kw.get("merch_ac_position", "—"),
                "etsy_comp":        kw.get("etsy_competition", "—"),
                "rb_comp":          kw.get("redbubble_competition", "—"),
                "pinterest_boards": kw.get("pinterest_board_followers", "—"),
                "reddit_demand":    f"{reddit_val:.1f}",
                "g_trends":         f"{trends_val:.1f}",
                "avg_price":        f"${price_val:.2f}" if price_val else "—",
                "sources":          kw.get("source", kw.get("sources", "")),
            }
            data.append(row)
        self._table.load_data(
            data,
            columns=POD_KEYWORD_COLUMNS,
            display_names=POD_KEYWORD_DISPLAY_NAMES,
        )

    def _export_csv(self):
        if not self._keywords_data:
            QMessageBox.warning(self, "Pas de données", "Rien à exporter.")
            return
        from PyQt6.QtWidgets import QFileDialog
        import csv
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Exporter CSV", "pod_keywords.csv", "CSV Files (*.csv)"
        )
        if filepath:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=POD_KEYWORD_COLUMNS)
                writer.writeheader()
                for kw in self._keywords_data:
                    row = {col: kw.get(col, "") for col in POD_KEYWORD_COLUMNS}
                    writer.writerow(row)
            QMessageBox.information(self, "Export terminé", f"Exporté vers {filepath}")

    def _clear_table(self):
        self._table.clear()
        self._keywords_data = []
        self._progress.set_status("")

    def _cancel_worker(self):
        if self._worker:
            self._worker.cancel()

    def _on_worker_error(self, error_msg):
        self._progress.finish(f"❌  Erreur : {error_msg}")
        self._mine_btn.setEnabled(True)
        self._score_btn.setEnabled(True)
        self._worker = None

    def focus_search(self):
        self._seed_input.setFocus()
