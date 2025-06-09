# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['bhrm_npc_editor.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'numpy', 'numpy.core._methods', 'numpy.lib.format',
        'matplotlib', 'matplotlib.pyplot', 'pyvista', 'pyvistaqt',
        'qtpy', 'qtpy.QtWidgets', 'qtpy.QtCore'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='bhrm_npc_editor',
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
    icon=['RBRM5_-_Logo_of_PLATINUM_FIVE.ico'],
)
