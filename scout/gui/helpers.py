from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QDialog, QVBoxLayout, QTextEdit
from PyQt6.QtCore import Qt


_INFO_BTN_STYLE = """
    QPushButton {
        border: 1px solid #585b70;
        border-radius: 10px;
        color: #a6adc8;
        font-weight: bold;
        font-size: 11px;
        background: transparent;
        padding: 0px;
    }
    QPushButton:hover {
        border-color: #cba6f7;
        color: #cba6f7;
        background: #313244;
    }
"""


_DIALOG_STYLE = """
    background: #1e1e2e; color: #cdd6f4;
    QTextEdit { background: #181825; color: #cdd6f4; border: 1px solid #313244;
                border-radius: 6px; padding: 12px; font-size: 13px; }
    QPushButton { background: #313244; color: #cdd6f4; border: none;
                  border-radius: 6px; padding: 8px 24px; font-weight: bold; }
    QPushButton:hover { background: #45475a; }
"""


def _show_info_dialog(parent, description, title="About"):
    """Show a silent modal dialog with the given description text."""
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.resize(480, 280)
    dlg.setStyleSheet(_DIALOG_STYLE)

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)

    text = QTextEdit()
    text.setReadOnly(True)
    text.setPlainText(description)
    text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    layout.addWidget(text)

    close_btn = QPushButton("Close")
    close_btn.clicked.connect(dlg.accept)
    layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    dlg.exec()


def make_header(parent, layout, title_html, description, title_style=None):
    """Create a header row with a title label and a circled info button.

    Clicking the info button shows *description* in a silent modal dialog.
    Returns the header QLabel so callers can keep a reference if needed.
    """
    hlayout = QHBoxLayout()
    hlayout.setSpacing(6)

    header = QLabel(title_html)
    if title_style:
        header.setStyleSheet(title_style)
    hlayout.addWidget(header)

    btn = QPushButton("?")
    btn.setFixedSize(20, 20)
    btn.setStyleSheet(_INFO_BTN_STYLE)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setToolTip("About this tool")
    btn.clicked.connect(lambda: _show_info_dialog(parent, description))
    hlayout.addWidget(btn)

    hlayout.addStretch()
    layout.addLayout(hlayout)

    return header
