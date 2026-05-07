from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QFormLayout, QLineEdit, QMessageBox,
    QRadioButton,
)
from PyQt6.QtCore import Qt

from scout.gui.widgets.progress_panel import ProgressPanel
from scout.gui.workers.pod_workers import PodProductLookupWorker


class PodProductLookupPage(QWidget):
    """Page for looking up POD product data."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._product_data = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = QLabel("<h2>🔎 POD Product Lookup</h2>")
        layout.addWidget(header)

        # Input section
        input_group = QGroupBox("Product Lookup")
        input_layout = QFormLayout(input_group)

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("Enter Etsy/Redbubble URL or Merch ASIN...")
        input_layout.addRow("URL / ASIN:", self._url_input)

        self._platform_radio_etsy = QRadioButton("Etsy")
        self._platform_radio_etsy.setChecked(True)
        self._platform_radio_rb = QRadioButton("Redbubble")
        self._platform_radio_merch = QRadioButton("Merch Amazon")

        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self._platform_radio_etsy)
        radio_layout.addWidget(self._platform_radio_rb)
        radio_layout.addWidget(self._platform_radio_merch)
        radio_layout.addStretch()

        input_layout.addRow("Platform:", radio_layout)

        layout.addWidget(input_group)

        # Buttons
        btn_layout = QHBoxLayout()

        self._lookup_btn = QPushButton("🔎 Lookup Product")
        self._lookup_btn.setProperty("class", "btn-primary")
        self._lookup_btn.clicked.connect(self._start_lookup)
        btn_layout.addWidget(self._lookup_btn)

        btn_layout.addStretch()

        self._analyze_btn = QPushButton("🔬 Analyze Niche")
        self._analyze_btn.clicked.connect(self._analyze_niche)
        btn_layout.addWidget(self._analyze_btn)

        layout.addLayout(btn_layout)

        # Results placeholder
        self._results_label = QLabel("Enter a product URL or ASIN to lookup.")
        self._results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._results_label.setStyleSheet("color: #6c7086; font-size: 14px; padding: 40px;")
        layout.addWidget(self._results_label, 1)

        # Progress
        self._progress = ProgressPanel(show_log=True)
        self._progress.cancel_requested.connect(self._cancel_worker)
        layout.addWidget(self._progress)

    def _start_lookup(self):
        url_or_id = self._url_input.text().strip()
        if not url_or_id:
            QMessageBox.warning(self, "Input Required", "Please enter a URL or ASIN.")
            return

        # Determine platform
        if self._platform_radio_etsy.isChecked():
            platform = "etsy"
        elif self._platform_radio_rb.isChecked():
            platform = "redbubble"
        else:
            platform = "merch"

        self._progress.start()
        self._lookup_btn.setEnabled(False)

        self._worker = PodProductLookupWorker(url_or_id, platform=platform)
        self._worker.status.connect(self._progress.set_status)
        self._worker.log.connect(self._progress.set_status)
        self._worker.finished_with_result.connect(self._on_lookup_finished)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_lookup_finished(self, product_data):
        self._progress.finish("Lookup complete!")
        self._lookup_btn.setEnabled(True)
        self._product_data = product_data

        # Display results
        title = product_data.get('title', 'N/A')
        keywords = ', '.join(product_data.get('keywords', []))
        price = product_data.get('price', 0)
        reviews = product_data.get('reviews', 0)
        seller = product_data.get('seller', 'N/A')

        html = f"""
        <h3>Product Found</h3>
        <p><b>Title:</b> {title}</p>
        <p><b>Price:</b> ${price:.2f}</p>
        <p><b>Reviews:</b> {reviews}</p>
        <p><b>Seller:</b> {seller}</p>
        <p><b>Keywords:</b> {keywords}</p>
        """

        self._results_label.setText(html)
        self._worker = None

    def _analyze_niche(self):
        if not self._product_data:
            QMessageBox.warning(self, "No Data", "Please lookup a product first.")
            return

        # Placeholder - will navigate to niche analyzer
        niche = self._product_data.get('title', '').split()[:3]
        niche_str = ' '.join(niche)
        QMessageBox.information(
            self, "Analyze Niche",
            f"Will analyze niche: {niche_str}"
        )

    def _cancel_worker(self):
        if self._worker:
            self._worker.cancel()

    def _on_worker_error(self, error_msg):
        self._progress.finish(f"Error: {error_msg}")
        self._lookup_btn.setEnabled(True)
        self._worker = None
