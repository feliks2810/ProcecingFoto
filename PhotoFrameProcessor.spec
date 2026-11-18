# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys
import customtkinter

block_cipher = None

# Dapatkan direktori instalasi customtkinter untuk menyertakan file tema dan aset font
ctk_dir = Path(customtkinter.__file__).parent

datas = [
    ('assets', 'assets'),
    (str(ctk_dir), 'customtkinter'),
]

hiddenimports = [
    'customtkinter',
    'darkdetect',
    'PIL',
    'PIL.Image',
    'PIL.ImageOps',
    'PIL.ImageDraw',
    'PIL.ImageTk',
    'pydantic',
    'psutil',
    'src',
    'src.config',
    'src.config.settings',
    'src.config.models',
    'src.config.persistence',
    'src.core',
    'src.core.validator',
    'src.core.exif_handler',
    'src.core.transform',
    'src.core.compositor',
    'src.core.hole_detector',
    'src.core.writer',
    'src.core.processor',
    'src.pipeline',
    'src.pipeline.scanner',
    'src.pipeline.reporter',
    'src.pipeline.runner',
    'src.gui',
    'src.gui.app',
    'src.gui.components',
    'src.gui.components.placement_editor',
    'src.gui.components.batch_card',
    'src.gui.components.preview_modal',
    'src.gui.components.progress_panel',
    'src.gui.components.log_console',
    'src.gui.controllers',
    'src.gui.controllers.main_controller',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
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
    name='PhotoFrameProcessor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Desktop GUI tanpa jendela terminal
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PhotoFrameProcessor',
)
