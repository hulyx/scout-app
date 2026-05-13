import os
import csv
from typing import Optional, Tuple


def get_export_path(
    parent, default_name: str = "export.csv", title: str = "Export"
) -> Tuple[Optional[str], Optional[str]]:
    """Open a save dialog with CSV and TXT filters.

    Returns (filepath, delimiter) where delimiter is ',' for CSV or '\\t' for TXT.
    Returns (None, None) if the user cancels.
    """
    from PyQt6.QtWidgets import QFileDialog

    filters = "CSV Files (*.csv);;Text Files (*.txt)"
    filepath, selected_filter = QFileDialog.getSaveFileName(
        parent, title, default_name, filters
    )
    if not filepath:
        return None, None

    ext = os.path.splitext(filepath)[1].lower()
    delimiter = "\t" if ext == ".txt" else ","
    # Ensure the extension matches the delimiter choice
    if delimiter == "\t" and ext != ".txt":
        filepath += ".txt"
    elif delimiter == "," and ext != ".csv":
        filepath += ".csv"

    return filepath, delimiter
