# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

a = Analysis(
    ['app/main.py'],
    pathex=['app'],
    binaries=[],
    datas=[
        ('config.txt', '.'),
        ('icon.ico', '.'),
    ],
    hiddenimports=[
        'sympy', 'sympy.parsing.sympy_parser', 'sympy.parsing.sympy_parser.transformations',
        'numpy',
        'matplotlib', 'matplotlib.backends.backend_tkagg', 'matplotlib.backends._tkagg',
        'matplotlib.backends._backend_tk', 'matplotlib.figure', 'matplotlib.pyplot',
        'tkinter', 'PIL', 'pix2text', 'ollama', 'torch', 'torchvision', 'torchaudio',
        'algebra', 'plotting', 'ai_methods', 'utils',
        'sympy.core', 'sympy.functions', 'sympy.solvers',
    ],
    hookspath=[],
    hooksconfig={
        "matplotlib": {"backends": ["TkAgg"]},   # ← это остаётся
    },
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# ← УБРАЛИ ВСЁ РУЧНОЕ СОБИРАНИЕ matplotlib (это и ломало)
# PyInstaller теперь использует свой встроенный hook — он работает корректно

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SmartCalculator',
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
    icon='icon.ico',
)