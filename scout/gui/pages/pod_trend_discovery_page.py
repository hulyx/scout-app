from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QMessageBox, QDialog, QTextEdit,
)
from PyQt6.QtCore import Qt

from scout.gui.widgets.data_table import DataTable
from scout.gui.widgets.progress_panel import ProgressPanel
from scout.gui.helpers import make_header
from scout.gui.workers.pod_workers import PodTrendDiscoveryWorker
from scout.gui.search_history import SearchHistory


TREND_COLUMNS = [
    "score", "title", "cluster_size", "seed_diversity", "keywords",
]

TREND_DISPLAY_NAMES = {
    "score": "Trend Score",
    "title": "Trending Theme",
    "cluster_size": "Keywords",
    "seed_diversity": "Categories",
    "keywords": "Sample Keywords",
}


class PodTrendDiscoveryPage(QWidget):
    """Discover trending keywords and products across all POD platforms.

    Zero-input tool: click the button and get trend data from
    Etsy, Redbubble, Spreadshirt, Google Suggest, and more.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._trend_data = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        make_header(self, layout, "<h2>🔥 POD Trend Scout</h2>",
                     "Discovers trending POD topics by expanding ~40 curated seed "
                     "keywords through Google Suggest, then groups them into thematic "
                     "clusters via NLP overlap. Hot trends surface as large clusters "
                     "spanning multiple seed categories. Uses the browser extension "
                     "if available, falls back to direct API.",
                     title_style="color: #cba6f7;")

        btn_layout = QHBoxLayout()

        self._scout_btn = QPushButton("🔥  Scout Trends Now")
        self._scout_btn.setProperty("class", "btn-primary")
        self._scout_btn.setMinimumHeight(48)
        self._scout_btn.setStyleSheet("font-size: 16px; font-weight: bold;")
        self._scout_btn.clicked.connect(self._start_scout)
        btn_layout.addWidget(self._scout_btn)

        self._export_btn = QPushButton("📤  Export")
        self._export_btn.clicked.connect(self._export_csv)
        btn_layout.addWidget(self._export_btn)

        self._clear_btn = QPushButton("🗑  Clear")
        self._clear_btn.clicked.connect(self._clear_all)
        btn_layout.addWidget(self._clear_btn)

        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        self._table = DataTable()
        self._table.row_double_clicked.connect(self._show_details)
        layout.addWidget(self._table, 1)

        self._progress = ProgressPanel(show_log=True)
        self._progress.cancel_requested.connect(self._cancel_worker)
        layout.addWidget(self._progress)

    def _start_scout(self):
        SearchHistory.instance().log(
            tool="POD Trend Scout",
            action="scout",
            query="auto-trend-discovery",
        )

        self._progress.start()
        self._scout_btn.setEnabled(False)

        self._worker = PodTrendDiscoveryWorker()
        self._worker.status.connect(self._progress.set_status)
        self._worker.progress.connect(self._progress.set_progress)
        self._worker.log.connect(self._progress.set_status)
        self._worker.finished_with_result.connect(self._on_scout_finished)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_scout_finished(self, items):
        items = items or []
        self._progress.finish(f"✅  {len(items)} trending items found")
        self._scout_btn.setEnabled(True)
        self._trend_data = items
        self._populate_table()
        self._worker = None

    def _populate_table(self):
        data = []
        for item in self._trend_data:
            kws = item.get("keywords") or []
            preview = ", ".join(kws[:4])
            if len(kws) > 4:
                preview += f" … (+{len(kws) - 4} more)"
            seeds = item.get("seeds") or []
            row = {
                "score": item.get("score", 0),
                "title": item.get("title", ""),
                "cluster_size": item.get("cluster_size", 0),
                "seed_diversity": item.get("seed_diversity", 0),
                "keywords": preview,
                "_all_keywords": kws,
                "_seeds": seeds,
            }
            data.append(row)
        self._table.load_data(
            data,
            columns=TREND_COLUMNS,
            display_names=TREND_DISPLAY_NAMES,
        )

    def _export_csv(self):
        if not self._trend_data:
            QMessageBox.warning(self, "No data", "Nothing to export.")
            return
        import csv
        from scout.gui.export_helper import get_export_path
        filepath, delimiter = get_export_path(self, "pod_trends.csv", "Export")
        if filepath:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=TREND_COLUMNS, delimiter=delimiter)
                writer.writeheader()
                for item in self._trend_data:
                    kws = item.get("keywords") or []
                    row = {
                        "score": item.get("score", ""),
                        "title": item.get("title", ""),
                        "cluster_size": item.get("cluster_size", ""),
                        "seed_diversity": item.get("seed_diversity", ""),
                        "keywords": "; ".join(kws),
                    }
                    writer.writerow(row)
            QMessageBox.information(self, "Export done", f"Saved to {filepath}")

    def _clear_all(self):
        self._table.clear()
        self._trend_data = []
        self._progress.set_status("")

    def _cancel_worker(self):
        if self._worker:
            self._worker.cancel()

    def _show_details(self, row_data):
        kws = row_data.get("_all_keywords") or []
        seeds = row_data.get("_seeds") or []
        if not kws:
            return

        title = row_data.get("title", "")
        score = row_data.get("score", 0)

        lines = [f"<h3>{title}</h3>",
                 f"<p>Trend Score: <b>{score}</b> | "
                 f"{len(kws)} keywords from {len(seeds)} seed categories</p>",
                 "<hr><h4>All Keywords:</h4><ol>"]
        for kw in kws:
            lines.append(f"<li>{kw}</li>")
        lines.append("</ol>")
        if seeds:
            lines.append(f"<h4>Seed Categories ({len(seeds)}):</h4><p>")
            lines.append(", ".join(sorted(seeds)))
            lines.append("</p>")

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Cluster: {title}")
        dlg.resize(600, 500)
        dlg.setStyleSheet("background: #1e1e2e; color: #cdd6f4;")
        layout = QVBoxLayout(dlg)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml("".join(lines))
        layout.addWidget(text)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn)
        dlg.exec()

    def _on_worker_error(self, error_msg):
        self._progress.finish(f"❌  Error: {error_msg}")
        self._scout_btn.setEnabled(True)
        self._worker = None
