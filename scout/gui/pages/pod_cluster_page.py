from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QFormLayout, QDoubleSpinBox, QMessageBox, QTextEdit,
)
from PyQt6.QtCore import Qt

from scout.gui.widgets.data_table import DataTable
from scout.gui.widgets.progress_panel import ProgressPanel
from scout.gui.workers.pod_workers import PodClusterWorker
from scout.gui.search_history import SearchHistory


CLUSTER_COLUMNS = [
    "cluster_label", "cluster_id", "size", "keywords_preview",
]

CLUSTER_DISPLAY_NAMES = {
    "cluster_label": "Cluster Theme",
    "cluster_id": "ID",
    "size": "Size",
    "keywords_preview": "Keywords",
}


class PodClusterPage(QWidget):
    """Cluster mined keywords by semantic similarity."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._cluster_data = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel("<h2>🔬 Keyword Clustering</h2>")
        header.setStyleSheet("color: #cba6f7;")
        layout.addWidget(header)

        desc = QLabel(
            "Paste a list of keywords (one per line) or send results from another tool. "
            "Keywords are grouped by topic using TF-IDF similarity — "
            "no external API calls, all processing is local."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #a6adc8; font-size: 12px;")
        layout.addWidget(desc)

        input_group = QGroupBox("Input Keywords")
        input_layout = QVBoxLayout(input_group)

        self._input_area = QTextEdit()
        self._input_area.setPlaceholderText(
            "Enter one keyword per line...\n\n"
            "Example:\ncat lover mug\ncrazy cat lady shirt\ncat mom gift\n"
            "nurse coffee mug\nnurse life shirt\nfunny nurse gift\n"
            "dog mom shirt\ndog dad hoodie\ndog lover mug"
        )
        self._input_area.setMinimumHeight(150)
        input_layout.addWidget(self._input_area)

        layout.addWidget(input_group)

        # Threshold control
        params_layout = QHBoxLayout()
        params_layout.addWidget(QLabel("Similarity threshold:"))

        self._threshold_spin = QDoubleSpinBox()
        self._threshold_spin.setRange(0.05, 0.95)
        self._threshold_spin.setSingleStep(0.05)
        self._threshold_spin.setValue(0.4)
        self._threshold_spin.setToolTip(
            "Higher = tighter groups, Lower = broader clusters"
        )
        params_layout.addWidget(self._threshold_spin)
        params_layout.addStretch()

        self._cluster_btn = QPushButton("🔬  Cluster Keywords")
        self._cluster_btn.setProperty("class", "btn-primary")
        self._cluster_btn.clicked.connect(self._start_clustering)
        params_layout.addWidget(self._cluster_btn)

        self._clear_btn = QPushButton("🗑  Clear")
        self._clear_btn.clicked.connect(self._clear_all)
        params_layout.addWidget(self._clear_btn)

        layout.addLayout(params_layout)

        # Results table
        self._table = DataTable()
        layout.addWidget(self._table, 1)

        # Progress
        self._progress = ProgressPanel(show_log=True)
        self._progress.cancel_requested.connect(self._cancel_worker)
        layout.addWidget(self._progress)

    def _start_clustering(self):
        text = self._input_area.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Input required", "Paste some keywords first.")
            return

        keywords = [line.strip() for line in text.split("\n") if line.strip()]
        if len(keywords) < 2:
            QMessageBox.warning(self, "Not enough data", "Need at least 2 keywords.")
            return

        SearchHistory.instance().log(
            tool="POD Cluster",
            action="cluster",
            query=f"{len(keywords)} keywords, threshold={self._threshold_spin.value()}",
        )

        self._progress.start()
        self._cluster_btn.setEnabled(False)

        self._worker = PodClusterWorker(keywords, threshold=self._threshold_spin.value())
        self._worker.status.connect(self._progress.set_status)
        self._worker.progress.connect(self._progress.set_progress)
        self._worker.log.connect(self._progress.set_status)
        self._worker.finished_with_result.connect(self._on_cluster_finished)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_cluster_finished(self, clusters):
        clusters = clusters or []
        self._progress.finish(f"✅  {len(clusters)} clusters found")
        self._cluster_btn.setEnabled(True)
        self._cluster_data = clusters
        self._populate_table()
        self._worker = None

    def _populate_table(self):
        data = []
        for cl in self._cluster_data:
            kws = cl.get("keywords", [])
            preview = ", ".join(kws[:5])
            if len(kws) > 5:
                preview += f" … (+{len(kws) - 5} more)"
            row = {
                "cluster_label": cl.get("label", ""),
                "cluster_id": cl.get("cluster", -1),
                "size": cl.get("size", 0),
                "keywords_preview": preview,
            }
            data.append(row)
        self._table.load_data(
            data,
            columns=CLUSTER_COLUMNS,
            display_names=CLUSTER_DISPLAY_NAMES,
        )

    def _clear_all(self):
        self._input_area.clear()
        self._table.clear()
        self._cluster_data = []
        self._progress.set_status("")

    def _cancel_worker(self):
        if self._worker:
            self._worker.cancel()

    def _on_worker_error(self, error_msg):
        self._progress.finish(f"❌  Error: {error_msg}")
        self._cluster_btn.setEnabled(True)
        self._worker = None

    def load_keywords(self, keywords):
        """Pre-fill keywords from another page (e.g. Keywords, Find For Me)."""
        if isinstance(keywords, list):
            text = "\n".join(k if isinstance(k, str) else k.get("keyword", str(k))
                            for k in keywords)
            self._input_area.setText(text)
