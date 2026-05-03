# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('mod_buntetes_vegrehajtas.py', '.'), ('mod_fix_turak.py', '.'), ('mod_karbantartas.py', '.'), ('mod_terkep.py', '.'), ('mod_tervezo.py', '.'), ('mod_turak_excelbol.py', '.')]
binaries = []
hiddenimports = ['folium', 'geopy', 'geopy.geocoders.photon', 'branca', 'jinja2', 'openpyxl', 'pandas', 'streamlit', 'mod_buntetes_vegrehajtas', 'mod_fix_turak', 'mod_karbantartas', 'mod_terkep', 'mod_tervezo', 'mod_turak_excelbol']
tmp_ret = collect_all('PyQt6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['tervezo_stabil.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='Turatervezo_App',
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
    icon=['szallitas.ico'],
)
