from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QMessageBox, QDialog, QTextEdit,
)
from PyQt6.QtCore import Qt

from scout.gui.widgets.data_table import DataTable
from scout.gui.widgets.progress_panel import ProgressPanel
from scout.gui.workers.pod_workers import PodNicheBloomWorker
from scout.gui.search_history import SearchHistory


BLOOM_COLUMNS = [
    "bloom_score", "name", "category", "bloom_level", "description",
]

BLOOM_DISPLAY_NAMES = {
    "bloom_score": "Score",
    "name": "Niche Name",
    "category": "Category",
    "bloom_level": "Demand",
    "description": "Description",
}

BLOOM_EMOJI = {5: "🌳", 4: "🌺", 3: "🌸", 2: "🌿", 1: "🌱"}


class PodNicheBloomPage(QWidget):
    """Browse NicheBloom's 100 curated POD niches with bloom scores."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._niches_data = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel("<h2>🌳 Bloom Trends (NicheBloom)</h2>")
        header.setStyleSheet("color: #cba6f7;")
        layout.addWidget(header)

        desc = QLabel(
            "100 curated POD niches with demand ratings from NicheBloom. "
            "Double-click a niche to see starter ideas, strategy, and "
            "monetization tips. Updated regularly — reflects real market demand "
            "across Etsy, Redbubble, and Amazon Merch."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #a6adc8; font-size: 12px;")
        layout.addWidget(desc)

        btn_layout = QHBoxLayout()

        self._fetch_btn = QPushButton("🌳  Load Bloom Trends")
        self._fetch_btn.setProperty("class", "btn-primary")
        self._fetch_btn.setMinimumHeight(48)
        self._fetch_btn.setStyleSheet("font-size: 16px; font-weight: bold;")
        self._fetch_btn.clicked.connect(self._start_fetch)
        btn_layout.addWidget(self._fetch_btn)

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

    def _start_fetch(self):
        SearchHistory.instance().log(
            tool="POD Bloom Trends",
            action="fetch",
            query="nichebloom-100-niches",
        )

        self._progress.start()
        self._fetch_btn.setEnabled(False)

        self._worker = PodNicheBloomWorker()
        self._worker.status.connect(self._progress.set_status)
        self._worker.progress.connect(self._progress.set_progress)
        self._worker.log.connect(self._progress.set_status)
        self._worker.finished_with_result.connect(self._on_fetch_finished)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_fetch_finished(self, niches):
        niches = niches or []
        self._progress.finish(f"✅  {len(niches)} niches loaded")
        self._fetch_btn.setEnabled(True)
        self._niches_data = niches
        self._populate_table()
        self._worker = None

    def _populate_table(self):
        data = []
        for n in self._niches_data:
            score = n.get("bloom_score", 0)
            emoji = BLOOM_EMOJI.get(score, "")
            row = {
                "bloom_score": score,
                "name": n.get("name", ""),
                "category": n.get("category", ""),
                "bloom_level": f"{emoji} {n.get('bloom_level', '')}",
                "description": n.get("description", ""),
                "_id": n.get("id"),
            }
            data.append(row)
        self._table.load_data(
            data,
            columns=BLOOM_COLUMNS,
            display_names=BLOOM_DISPLAY_NAMES,
        )

    def _show_details(self, row_data):
        niche_id = row_data.get("_id")
        if not niche_id:
            return

        from scout.collectors.pod_nichebloom_collector import scrape_niche_detail

        try:
            detail = scrape_niche_detail(niche_id)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load detail: {e}")
            return

        if detail.get("error"):
            QMessageBox.warning(self, "Error", detail["error"])
            return

        name = detail.get("name", row_data.get("name", ""))
        lines = [
            f"<h2>{name}</h2>",
            f"<p><b>Category:</b> {detail.get('category', '')} | "
            f"<b>Bloom Score:</b> {detail.get('bloom_level', '')} "
            f"({detail.get('bloom_score', '')}/5)</p>",
            f"<p>{detail.get('description', '')}</p>",
        ]

        ideas = detail.get("starter_ideas") or []
        if ideas:
            lines.append("<hr><h3>Starter Ideas</h3><ul>")
            for idea in ideas:
                lines.append(f"<li>{idea}</li>")
            lines.append("</ul>")

        strategy = detail.get("strategy") or {}
        if strategy:
            lines.append("<hr><h3>Strategy — Why This Niche Works</h3>")
            labels = {
                "category": "Category",
                "best_use": "Best Use",
                "design_angle": "Design Angle",
                "monetization_note": "Monetization Note",
            }
            for key, label in labels.items():
                val = strategy.get(key)
                if val:
                    lines.append(f"<p><b>{label}:</b> {val}</p>")

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Niche: {name}")
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

    def _export_csv(self):
        if not self._niches_data:
            QMessageBox.warning(self, "No data", "Nothing to export.")
            return
        import csv
        from scout.gui.export_helper import get_export_path
        filepath, delimiter = get_export_path(self, "bloom_trends.csv", "Export")
        if not filepath:
            return

        from scout.collectors.pod_nichebloom_collector import scrape_niche_detail

        self._progress.start()
        self._export_btn.setEnabled(False)
        total = len(self._niches_data)

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=delimiter)
            writer.writerow([
                "Score", "Niche Name", "Category", "Demand", "Description",
                "Starter Ideas", "Best Use", "Design Angle", "Monetization Note",
            ])
            for i, n in enumerate(self._niches_data):
                self._progress.set_status(f"Fetching details: {i+1}/{total}")
                self._progress.set_progress(i + 1, total)

                ideas_str = ""
                best_use = design_angle = monetization = ""

                niche_id = n.get("id")
                if niche_id:
                    try:
                        detail = scrape_niche_detail(niche_id)
                        if detail and not detail.get("error"):
                            ideas = detail.get("starter_ideas") or []
                            ideas_str = "; ".join(ideas)
                            strategy = detail.get("strategy") or {}
                            best_use = strategy.get("best_use", "")
                            design_angle = strategy.get("design_angle", "")
                            monetization = strategy.get("monetization_note", "")
                    except Exception:
                        pass

                writer.writerow([
                    n.get("bloom_score", ""),
                    n.get("name", ""),
                    n.get("category", ""),
                    n.get("bloom_level", ""),
                    n.get("description", ""),
                    ideas_str,
                    best_use,
                    design_angle,
                    monetization,
                ])

        self._progress.finish(f"✅  Exported {total} niches with details to {filepath}")
        self._export_btn.setEnabled(True)
        QMessageBox.information(self, "Export done", f"Saved to {filepath}")

    def _clear_all(self):
        self._table.clear()
        self._niches_data = []
        self._progress.set_status("")

    def _cancel_worker(self):
        if self._worker:
            self._worker.cancel()

    def _on_worker_error(self, error_msg):
        self._progress.finish(f"❌  Error: {error_msg}")
        self._fetch_btn.setEnabled(True)
        self._worker = None
