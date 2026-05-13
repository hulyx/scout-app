from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QFormLayout, QLineEdit, QMessageBox, QTextEdit,
)
from PyQt6.QtCore import Qt

from scout.gui.widgets.data_table import DataTable
from scout.gui.widgets.progress_panel import ProgressPanel
from scout.gui.workers.pod_workers import PodBSRAnalyzerWorker
from scout.gui.search_history import SearchHistory


BSR_COLUMNS = [
    "asin", "title", "price", "bsr", "bsr_category",
    "estimated_daily_sales", "estimated_monthly_sales",
]

BSR_DISPLAY_NAMES = {
    "asin": "ASIN",
    "title": "Title",
    "price": "Price",
    "bsr": "BSR",
    "bsr_category": "BSR Category",
    "estimated_daily_sales": "Est. Daily Sales",
    "estimated_monthly_sales": "Est. Monthly Sales",
}


class PodBSRAnalyzerPage(QWidget):
    """Analyze Amazon Best Sellers Rank for POD products."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._bsr_data = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel("<h2>📊 BSR Analyzer (POD)</h2>")
        header.setStyleSheet("color: #cba6f7;")
        layout.addWidget(header)

        desc = QLabel(
            "Enter Amazon ASINs (one per line) to fetch Best Sellers Rank "
            "and estimate daily/monthly sales for POD products. "
            "BSR is extracted from Amazon's server-rendered product pages."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #a6adc8; font-size: 12px;")
        layout.addWidget(desc)

        input_group = QGroupBox("ASINs")
        input_layout = QVBoxLayout(input_group)

        self._input_area = QTextEdit()
        self._input_area.setPlaceholderText(
            "Enter one ASIN per line...\n\n"
            "Example:\nB09XYZ1234\nB08ABC5678\n"
            "Or paste full Amazon URLs (ASINs will be extracted)"
        )
        self._input_area.setMinimumHeight(120)
        input_layout.addWidget(self._input_area)

        layout.addWidget(input_group)

        btn_layout = QHBoxLayout()

        self._analyze_btn = QPushButton("📊  Analyze BSR")
        self._analyze_btn.setProperty("class", "btn-primary")
        self._analyze_btn.clicked.connect(self._start_analysis)
        btn_layout.addWidget(self._analyze_btn)

        self._clear_btn = QPushButton("🗑  Clear")
        self._clear_btn.clicked.connect(self._clear_all)
        btn_layout.addWidget(self._clear_btn)

        btn_layout.addStretch()

        self._export_btn = QPushButton("📤  Export")
        self._export_btn.clicked.connect(self._export_csv)
        btn_layout.addWidget(self._export_btn)

        layout.addLayout(btn_layout)

        self._table = DataTable()
        layout.addWidget(self._table, 1)

        self._progress = ProgressPanel(show_log=True)
        self._progress.cancel_requested.connect(self._cancel_worker)
        layout.addWidget(self._progress)

    def _extract_asins(self):
        import re
        text = self._input_area.toPlainText().strip()
        if not text:
            return []
        # Extract ASINs: B + 9 alphanumeric chars (standard Amazon ASIN)
        asins = re.findall(r"/(?:dp|product)/([A-Z0-9]{10})", text)
        asins += re.findall(r"\b([A-Z0-9]{10})\b", text)
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for a in asins:
            if a not in seen:
                seen.add(a)
                unique.append(a)
        return unique

    def _start_analysis(self):
        asins = self._extract_asins()
        if not asins:
            QMessageBox.warning(
                self, "Input required",
                "Enter at least one ASIN (10-character Amazon product ID)."
            )
            return
        if len(asins) > 20:
            reply = QMessageBox.question(
                self, "Many ASINs",
                f"Scraping {len(asins)} products will take ~{len(asins)} seconds "
                "due to rate limiting. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        SearchHistory.instance().log(
            tool="POD BSR Analyzer",
            action="analyze",
            query=", ".join(asins[:5]),
            notes=f"{len(asins)} ASINs",
        )

        self._progress.start()
        self._analyze_btn.setEnabled(False)

        self._worker = PodBSRAnalyzerWorker(asins)
        self._worker.status.connect(self._progress.set_status)
        self._worker.progress.connect(self._progress.set_progress)
        self._worker.log.connect(self._progress.set_status)
        self._worker.finished_with_result.connect(self._on_analysis_finished)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_analysis_finished(self, results):
        results = results or []
        found = sum(1 for r in results if r.get("bsr"))
        self._progress.finish(f"✅  {found}/{len(results)} ASINs had BSR data")
        self._analyze_btn.setEnabled(True)
        self._bsr_data = results
        self._populate_table()
        self._worker = None

    def _populate_table(self):
        data = []
        for r in self._bsr_data:
            row = {
                "asin": r.get("asin", ""),
                "title": r.get("title", "—"),
                "price": f"${r.get('price', 0):.2f}" if r.get("price") else "—",
                "bsr": r.get("bsr", "—") if r.get("bsr") else "—",
                "bsr_category": (r.get("bsr_category") or "")[:80] if r.get("bsr_category") else "—",
                "estimated_daily_sales": f"{r.get('estimated_daily_sales', 0):.1f}",
                "estimated_monthly_sales": f"{r.get('estimated_monthly_sales', 0):.0f}",
            }
            data.append(row)
        self._table.load_data(
            data,
            columns=BSR_COLUMNS,
            display_names=BSR_DISPLAY_NAMES,
        )

    def _export_csv(self):
        if not self._bsr_data:
            QMessageBox.warning(self, "No data", "Nothing to export.")
            return
        import csv
        from scout.gui.export_helper import get_export_path
        filepath, delimiter = get_export_path(self, "pod_bsr_data.csv", "Export")
        if filepath:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=BSR_COLUMNS, delimiter=delimiter)
                writer.writeheader()
                for r in self._bsr_data:
                    writer.writerow({col: r.get(col, "") for col in BSR_COLUMNS})
            QMessageBox.information(self, "Export done", f"Saved to {filepath}")

    def _clear_all(self):
        self._input_area.clear()
        self._table.clear()
        self._bsr_data = []
        self._progress.set_status("")

    def _cancel_worker(self):
        if self._worker:
            self._worker.cancel()

    def _on_worker_error(self, error_msg):
        self._progress.finish(f"❌  Error: {error_msg}")
        self._analyze_btn.setEnabled(True)
        self._worker = None
