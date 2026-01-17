# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Retagger
Builds a standalone executable for macOS and Windows
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect customtkinter data files (themes, assets)
ctk_datas = collect_data_files('customtkinter')

# Hidden imports that PyInstaller might miss
hidden_imports = collect_submodules('customtkinter')

# Platform-specific settings
if sys.platform == 'darwin':
    icon_path = 'assets/icon.icns' if os.path.exists('assets/icon.icns') else None
elif sys.platform == 'win32':
    icon_path = 'assets/icon.ico' if os.path.exists('assets/icon.ico') else None
else:
    icon_path = None

a = Analysis(
    ['src/retagger/gui.py'],
    pathex=['src'],
    binaries=[],
    datas=ctk_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

if sys.platform == 'darwin':
    # macOS: Use onedir mode with .app bundle
    exe = EXE(
        pyz,
        a.scripts,
        exclude_binaries=True,  # Required for COLLECT
        name='Retagger',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_path,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='Retagger',
    )
    app = BUNDLE(
        coll,
        name='Retagger.app',
        icon=icon_path,
        bundle_identifier='com.retagger.app',
        info_plist={
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleName': 'Retagger',
            'NSHighResolutionCapable': True,
        },
    )
else:
    # Windows: Use onefile mode
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='Retagger',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_path,
    )
