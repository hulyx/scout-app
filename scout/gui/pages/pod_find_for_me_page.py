from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QFormLayout, QComboBox, QSpinBox, QMessageBox,
)
from PyQt6.QtCore import Qt

from scout.gui.widgets.progress_panel import ProgressPanel
from scout.gui.workers.pod_workers import PodFindForMeWorker


class PodFindForMePage(QWidget):
    """Page for automatically discovering profitable POD niches."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._results = []
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header
        header = QLabel("<h2>🎯 POD Find For Me</h2>")
        layout.addWidget(header)
        
        # Parameters
        param_group = QGroupBox("Discovery Parameters")
        param_layout = QFormLayout(param_group)
        
        self._type_combo = QComboBox()
        self._type_combo.addItems(["All", "T-shirt", "Mug", "Sticker", "Poster", "Hoodie"])
        param_layout.addRow("Product Type:", self._type_combo)
        
        self._comp_combo = QComboBox()
        self._comp_combo.addItems(["Low", "Medium", "High", "Any"])
        param_layout.addRow("Desired Competition:", self._comp_combo)
        
        self._category_combo = QComboBox()
        self._category_combo.addItems([
            "All", "Professions", "Animals", "Family", 
            "Hobbies", "Humor", "Holidays", "Sports", 
            "Geographic", "Lifestyle"
        ])
        param_layout.addRow("Category:", self._category_combo)
        
        layout.addWidget(param_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self._find_btn = QPushButton("🎯 Find Profitable Niches")
        self._find_btn.setProperty("class", "btn-primary")
        self._find_btn.clicked.connect(self._start_discovery)
        btn_layout.addWidget(self._find_btn)
        
        btn_layout.addStretch()
        
        self._analyze_btn = QPushButton("🔬 Analyze This Niche")
        self._analyze_btn.setProperty("class", "btn-primary")
        self._analyze_btn.setEnabled(False)
        self._analyze_btn.clicked.connect(self._analyze_selected)
        btn_layout.addWidget(self._analyze_btn)
        
        layout.addLayout(btn_layout)
        
        # Results placeholder
        self._results_label = QLabel("Click 'Find Profitable Niches' to start discovery.")
        self._results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._results_label.setStyleSheet("color: #6c7086; font-size: 14px; padding: 40px;")
        layout.addWidget(self._results_label, 1)
        
        # Progress
        self._progress = ProgressPanel(show_log=True)
        self._progress.cancel_requested.connect(self._cancel_worker)
        layout.addWidget(self._progress)
    
    def _start_discovery(self):
        self._progress.start()
        self._find_btn.setEnabled(False)
        self._analyze_btn.setEnabled(False)
        
        product_type = self._type_combo.currentText().lower()
        competition_level = self._comp_combo.currentText().lower()
        category = self._category_combo.currentText().lower()
        self._worker = PodFindForMeWorker(
            product_type=product_type,
            competition_level=competition_level,
            category=category,
        )
        self._worker.status.connect(self._progress.set_status)
        self._worker.progress.connect(self._progress.set_progress)
        self._worker.log.connect(self._progress.set_status)
        self._worker.finished_with_result.connect(self._on_discovery_finished)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()
    
    def _on_discovery_finished(self, results):
        self._progress.finish(f"Found {len(results)} profitable niches!")
        self._find_btn.setEnabled(True)
        self._results = results
        
        if results:
            text = "<h3>Top Profitable Niches:</h3><ul>"
            for i, niche in enumerate(results[:10], 1):
                text += f"<li><b>{niche.get('niche', '')}</b> - Score: {niche.get('global_score', 0):.2f}</li>"
            text += "</ul>"
            self._results_label.setText(text)
            self._results_label.setStyleSheet("padding: 20px;")
            self._analyze_btn.setEnabled(True)
        else:
            self._results_label.setText("No profitable niches found. Try different parameters.")
        
        self._worker = None
    
    def _analyze_selected(self):
        # Placeholder - will navigate to niche analyzer
        if self._results:
            niche = self._results[0].get('niche', '')
            QMessageBox.information(self, "Analyze", f"Will analyze: {niche}")
    
    def _cancel_worker(self):
        if self._worker:
            self._worker.cancel()
    
    def _on_worker_error(self, error_msg):
        self._progress.finish(f"Error: {error_msg}")
        self._find_btn.setEnabled(True)
        self._worker = None
