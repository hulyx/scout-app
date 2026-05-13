from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QMessageBox,
)
from PyQt6.QtCore import Qt

from scout.gui.widgets.data_table import DataTable
from scout.gui.widgets.progress_panel import ProgressPanel
from scout.gui.helpers import make_header
from scout.gui.workers.pod_workers import PodBubbleTrendsWorker
from scout.gui.search_history import SearchHistory


BT_COLUMNS = ["rank", "keyword", "result_count"]
BT_DISPLAY_NAMES = {
    "rank": "#",
    "keyword": "Keyword",
    "result_count": "Result Count",
}


class PodBubbleTrendsPage(QWidget):
    """Display trending Redbubble keywords from Bubble Trends."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._trends_data = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        make_header(self, layout, "<h2> Bubble Trends (Redbubble)</h2>",
                     "Trending keywords on Redbubble with real result counts, "
                     "aggregated by Bubble Trends. Data refreshes every 24 hours. "
                     "Sorted by result count (highest first).",
                     title_style="color: #cba6f7;")

        btn_layout = QHBoxLayout()

        self._fetch_btn = QPushButton(" Fetch Bubble Trends")
        self._fetch_btn.setProperty("class", "btn-primary")
        self._fetch_btn.setMinimumHeight(48)
        self._fetch_btn.setStyleSheet("font-size: 16px; font-weight: bold;")
        self._fetch_btn.clicked.connect(self._start_fetch)
        btn_layout.addWidget(self._fetch_btn)

        self._export_btn = QPushButton("📤  Export")
        self._export_btn.clicked.connect(self._export_csv)
        btn_layout.addWidget(self._export_btn)

        self._clear_btn = QPushButton("  Clear")
        self._clear_btn.clicked.connect(self._clear_all)
        btn_layout.addWidget(self._clear_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self._table = DataTable()
        self._table._extra_context_actions = self._extra_table_actions
        layout.addWidget(self._table, 1)

        self._progress = ProgressPanel(show_log=True)
        self._progress.cancel_requested.connect(self._cancel_worker)
        layout.addWidget(self._progress)

    def _start_fetch(self):
        SearchHistory.instance().log(
            tool="POD Bubble Trends",
            action="fetch",
            query="bubbletrends-redbubble",
        )

        self._progress.start()
        self._fetch_btn.setEnabled(False)

        self._worker = PodBubbleTrendsWorker()
        self._worker.status.connect(self._progress.set_status)
        self._worker.progress.connect(self._progress.set_progress)
        self._worker.log.connect(self._progress.set_status)
        self._worker.finished_with_result.connect(self._on_fetch_finished)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_fetch_finished(self, items):
        items = items or []
        self._progress.finish(f"  {len(items)} items found")
        self._fetch_btn.setEnabled(True)
        self._trends_data = items
        self._populate_table()
        self._worker = None

    def _normalize(self, item):
        """Handle both BubbleTrends format ({keyword, result_count}) and
        Redbubble popular fallback ({title, price, artist})."""
        keyword = item.get("keyword") or item.get("title", "")
        count = item.get("result_count") or item.get("price", "") or ""
        if isinstance(count, float):
            count = f"${count:.2f}"
        return {"keyword": keyword, "result_count": count}

    def _populate_table(self):
        data = []
        for i, item in enumerate(self._trends_data):
            n = self._normalize(item)
            data.append({
                "rank": i + 1,
                "keyword": n["keyword"],
                "result_count": n["result_count"],
            })
        self._table.load_data(
            data,
            columns=BT_COLUMNS,
            display_names=BT_DISPLAY_NAMES,
        )

    def _export_csv(self):
        if not self._trends_data:
            QMessageBox.warning(self, "No data", "Nothing to export.")
            return
        import csv
        from scout.gui.export_helper import get_export_path
        filepath, delimiter = get_export_path(self, "bubble_trends.csv", "Export")
        if filepath:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=delimiter)
                writer.writerow(["Rank", "Keyword", "Result Count"])
                for i, item in enumerate(self._trends_data):
                    n = self._normalize(item)
                    writer.writerow([i + 1, n["keyword"], n["result_count"]])
            QMessageBox.information(self, "Export done", f"Saved to {filepath}")

    def _extra_table_actions(self, row_data: dict) -> list:
        from PyQt6.QtGui import QAction
        import urllib.parse
        import webbrowser

        keyword = (row_data.get("keyword") or "").strip()
        if not keyword:
            return []
        action = QAction("\U0001f3a8 Search on Redbubble", self)
        url = f"https://www.redbubble.com/shop?query={urllib.parse.quote(keyword)}"
        action.triggered.connect(lambda: webbrowser.open(url))
        return [action]

    def _clear_all(self):
        self._table.clear()
        self._trends_data = []
        self._progress.set_status("")

    def _cancel_worker(self):
        if self._worker:
            self._worker.cancel()

    def _on_worker_error(self, error_msg):
        self._progress.finish(f"  Error: {error_msg}")
        self._fetch_btn.setEnabled(True)
        self._worker = None
