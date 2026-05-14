# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Scout.

Build with:
    pip install pyinstaller
    pyinstaller scout_gui.spec

This produces a single .exe in dist/
"""

import os
import sys
from pathlib import Path

block_cipher = None

# Use SPECPATH (PyInstaller built-in) to resolve paths relative to spec file
# This ensures the icon is always found regardless of where the build is run from
qss_path = os.path.join(SPECPATH, 'gui', 'resources', 'style.qss')
ico_path = os.path.join(SPECPATH, 'gui', 'resources', 'kdpsy.ico')
svg_path = os.path.join(SPECPATH, 'gui', 'resources', 'kdpsy.svg')

a = Analysis(
    ['scout_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        (qss_path, os.path.join('scout', 'gui', 'resources')),
        (ico_path, os.path.join('scout', 'gui', 'resources')),
        (svg_path, os.path.join('scout', 'gui', 'resources')),
    ],
    hiddenimports=[
    "scout.collectors.goodreads",
    "scout.gui.pages.goodreads_explorer_page",
    "scout.gui.workers.goodreads_worker",
        'scout.gui',
        'scout.gui.pages',
        'scout.gui.pages.keywords_page',
        'scout.gui.pages.trending_page',
        'scout.gui.pages.competitors_page',
        'scout.gui.pages.ads_page',
        'scout.gui.pages.seeds_page',
        'scout.gui.pages.asin_lookup_page',
        'scout.gui.pages.automation_page',
        'scout.gui.pages.settings_page',
        'scout.gui.widgets',
        'scout.gui.workers',
        'scout.collectors',
        'scout.collectors.autocomplete',
        'scout.collectors.product_scraper',
        'scout.collectors.trending',
        'scout.collectors.dataforseo',
        'scout.collectors.bsr_model',
        'matplotlib.backends.backend_qtagg',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Scout',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    icon=ico_path,
    console=False,  # No console window (--windowed)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
