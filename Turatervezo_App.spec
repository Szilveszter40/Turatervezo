# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('autok.txt', '.'), ('bv_adatbazis.json', '.'), ('bv_fix_turak.json', '.'), ('bv_intezmenyek.json', '.'), ('fix_turak_napi.json', '.'), ('mod_buntetes_vegrehajtas.py', '.'), ('mod_fix_turak.py', '.'), ('mod_karbantartas.py', '.'), ('mod_terkep.py', '.'), ('mod_tervezo.py', '.'), ('mod_turak_excelbol.py', '.'), ('soforok.txt', '.'), ('temp_excel_adatok.json', '.'), ('tervezo_partnerek.json', '.'), ('tervezo_turak.json', '.'), ('tervezo_turak_mentese.json', '.'), ('Turanevek.txt', '.')]
binaries = []
hiddenimports = []
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
    [],
    exclude_binaries=True,
    name='Turatervezo_App',
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
    icon=['szallitas.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Turatervezo_App',
)
