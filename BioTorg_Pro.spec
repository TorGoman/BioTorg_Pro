# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

datas = [
    ('attendance_config.json', '.'),
    ('version.json', '.'),
]
if os.path.exists('app_icon.ico'):
    datas.append(('app_icon.ico', '.'))
if os.path.exists('assets'):
    datas.append(('assets', 'assets'))
if os.path.exists('AGL_001.TXT'):
    datas.append(('AGL_001.TXT', '.'))
if os.path.exists('GLG_001.TXT'):
    datas.append(('GLG_001.TXT', '.'))

datas += collect_data_files('customtkinter')

hiddenimports = [
    'customtkinter',
    'openpyxl',
    'pandas',
    'tkinter',
    'webbrowser',
    'urllib.request',
    'assets_data',
    'PIL',
    'PIL.Image',
] + collect_submodules('customtkinter')

a = Analysis(
    ['attendance_gui.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name='BioTorg_Pro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='BioTorg_Pro',
)
