from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QFormLayout, QComboBox, QMessageBox, QSpinBox, QLineEdit,
)
from PyQt6.QtCore import Qt

from scout.gui.widgets.data_table import DataTable
from scout.gui.widgets.progress_panel import ProgressPanel
from scout.gui.helpers import make_header
from scout.gui.workers.pod_workers import PodPinterestExplorerWorker
from scout.gui.search_history import SearchHistory


POD_PEX_COLUMNS = [
    "row_num", "keyword", "type", "trend_score",
    "pinterest_pins", "followers", "category", "source",
]

POD_PEX_DISPLAY_NAMES = {
    "row_num": "#",
    "keyword": "Keyword",
    "type": "Type",
    "trend_score": "Trend",
    "pinterest_pins": "Pins",
    "followers": "Followers",
    "category": "Category",
    "source": "Source",
}


class PodPinterestExplorerPage(QWidget):
    """Unified Pinterest Explorer: discover seeds + explore Pinterest data."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._data = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        make_header(self, layout, "<h2>📌 Pinterest Explorer</h2>",
                     "Browse niches by category or enter a seed to explore Pinterest. "
                     "Results show trend scores + Pinterest data (suggestions, boards, trending).")

        # Parameters
        param_group = QGroupBox("Parameters")
        param_layout = QVBoxLayout(param_group)
        param_layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        top_row.addWidget(QLabel("Category:"))
        self._category_combo = QComboBox()
        self._category_combo.addItems([
            "All", "Professions", "Animals", "Family",
            "Hobbies", "Humor", "Holidays", "Sports",
            "Geographic", "Lifestyle",
        ])
        top_row.addWidget(self._category_combo)

        top_row.addWidget(QLabel("Limit:"))
        self._limit_spin = QSpinBox()
        self._limit_spin.setRange(5, 50)
        self._limit_spin.setValue(10)
        top_row.addWidget(self._limit_spin)

        top_row.addWidget(QLabel("Show:"))
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["All", "Seeds", "Suggestions", "Boards", "Trending"])
        top_row.addWidget(self._mode_combo)

        top_row.addWidget(QLabel("Seed:"))
        self._seed_input = QLineEdit()
        self._seed_input.setPlaceholderText("Overrides category")
        top_row.addWidget(self._seed_input, 1)
        param_layout.addLayout(top_row)

        layout.addWidget(param_group)

        # Buttons
        btn_layout = QHBoxLayout()

        self._explore_btn = QPushButton("🔍 Explore")
        self._explore_btn.setProperty("class", "btn-primary")
        self._explore_btn.clicked.connect(self._start_explore)
        btn_layout.addWidget(self._explore_btn)

        btn_layout.addStretch()

        self._analyze_btn = QPushButton("🔬 Analyze Niche")
        self._analyze_btn.setEnabled(False)
        self._analyze_btn.clicked.connect(self._analyze_niche)
        btn_layout.addWidget(self._analyze_btn)

        self._send_btn = QPushButton("⛏ Send to Keywords")
        self._send_btn.setEnabled(False)
        self._send_btn.clicked.connect(self._send_to_keywords)
        btn_layout.addWidget(self._send_btn)

        self._export_btn = QPushButton("📤 Export")
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._export_csv)
        btn_layout.addWidget(self._export_btn)

        layout.addLayout(btn_layout)

        # Results table
        self._table = DataTable()
        self._table._model._columns = POD_PEX_COLUMNS
        self._table._model._display_names = POD_PEX_DISPLAY_NAMES
        layout.addWidget(self._table, 1)

        # Progress
        self._progress = ProgressPanel(show_log=True)
        self._progress.cancel_requested.connect(self._cancel_worker)
        layout.addWidget(self._progress)

    def _start_explore(self):
        seed = self._seed_input.text().strip()
        category = self._category_combo.currentText().lower()
        limit = self._limit_spin.value()
        mode = self._mode_combo.currentText().lower()

        self._progress.start()
        self._explore_btn.setEnabled(False)
        self._analyze_btn.setEnabled(False)
        self._send_btn.setEnabled(False)
        self._export_btn.setEnabled(False)

        if self._worker:
            if self._worker.isRunning():
                self._worker.quit()
                self._worker.wait(1000)
            self._worker.deleteLater()
            self._worker = None

        self._worker = PodPinterestExplorerWorker(
            category=category, seed=seed if seed else None,
            limit_per_category=limit, mode=mode,
        )
        self._worker.status.connect(self._progress.set_status)
        self._worker.progress.connect(self._progress.set_progress)
        self._worker.log.connect(self._progress.set_status)
        self._worker.finished_with_result.connect(self._on_explore_finished)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_explore_finished(self, results):
        self._progress.finish(f"Found {len(results)} results")
        self._explore_btn.setEnabled(True)

        self._data = results
        if results:
            self._populate_table()
            self._analyze_btn.setEnabled(True)
            self._send_btn.setEnabled(True)
            self._export_btn.setEnabled(True)
        else:
            self._table.load_data([])
            self._progress.set_status("No results. Try a different category or seed.")

        self._worker = None
        try:
            SearchHistory.instance().log(
                tool="POD Pinterest", action="explore",
                query=f"{self._seed_input.text().strip() or self._category_combo.currentText()} [{self._mode_combo.currentText()}]",
                results=results, result_count=len(results),
            )
        except Exception:
            pass

    def _populate_table(self):
        data = []
        for i, item in enumerate(self._data, 1):
            row = {
                "row_num": i,
                "keyword": item.get("keyword", ""),
                "type": item.get("type", ""),
                "trend_score": f"{item.get('trend_score', 0):.1f}",
                "pinterest_pins": item.get("pinterest_pins", 0),
                "followers": item.get("followers", 0),
                "category": item.get("category", ""),
                "source": item.get("source", ""),
            }
            data.append(row)
        self._table.load_data(data)

    def _analyze_niche(self):
        row = self._table.get_selected_row()
        if not row:
            QMessageBox.information(
                self, "Select a Niche",
                "Please select a keyword from the table first."
            )
            return
        niche = row.get("keyword", "").strip()
        if not niche:
            return
        mw = self.window()
        if hasattr(mw, '_switch_page'):
            mw._switch_page("Niche Analyzer")
            current = mw._stack.currentWidget()
            if hasattr(current, '_niche_input'):
                current._niche_input.setText(niche)
                current._start_analysis()

    def _send_to_keywords(self):
        row = self._table.get_selected_row()
        if not row:
            QMessageBox.information(
                self, "Select a Keyword",
                "Please select a keyword from the table first."
            )
            return
        keyword = row.get("keyword", "").strip()
        if not keyword:
            return
        mw = self.window()
        if hasattr(mw, '_switch_page'):
            mw._switch_page("Keywords")
            current = mw._stack.currentWidget()
            if hasattr(current, '_seed_input'):
                current._seed_input.setText(keyword)
            if hasattr(current, '_start_mine'):
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(500, current._start_mine)

    def _export_csv(self):
        if not self._data:
            QMessageBox.warning(self, "No Data", "Nothing to export.")
            return
        import csv
        from scout.gui.export_helper import get_export_path
        filepath, delimiter = get_export_path(self, "pinterest_explorer.csv", "Export")
        if filepath:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=POD_PEX_COLUMNS, delimiter=delimiter)
                writer.writeheader()
                for item in self._data:
                    row = {col: item.get(col, "") for col in POD_PEX_COLUMNS}
                    writer.writerow(row)
            QMessageBox.information(self, "Export Complete", f"Exported to {filepath}")

    def _cancel_worker(self):
        if self._worker:
            self._worker.cancel()

    def _on_worker_error(self, error_msg):
        self._progress.finish(f"Error: {error_msg}")
        self._explore_btn.setEnabled(True)
        self._worker = None
