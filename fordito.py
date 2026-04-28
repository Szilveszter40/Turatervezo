import os
import shutil
import subprocess
import sys

# 1. Beállítások
FO_FAJL = "tervezo_stabil.py"
IKON = "szallitas.ico"
APP_NEV = "Turatervezo_App"
DIST_MAPPA = os.path.join("dist", APP_NEV)

def forditas():
    print("[1/4] Takarítás...")
    for folder in ["dist", "build"]:
        if os.path.exists(folder):
            shutil.rmtree(folder)

    print("[2/4] Fordítás (PyInstaller)...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--onedir", "--windowed",
        "--collect-all", "PyQt6",
        "--icon", IKON,
        "--name", APP_NEV,
        "--add-data", "mod_*.py;.", # EZT ADD HOZZÁ: Belerakja a modulokat az EXE gyökerébe
        FO_FAJL
    ]

    subprocess.run(cmd)

    print("[3/4] Modulok szűrése és másolása...")
    # Töröljük a PyInstaller által odarakott felesleges .py fájlokat
    for f in os.listdir(DIST_MAPPA):
        if f.endswith(".py"):
            os.remove(os.path.join(DIST_MAPPA, f))

    # Csak a tiszta mod_*.py fájlokat másoljuk át
    for f in os.listdir("."):
        if f.startswith("mod_") and f.endswith(".py"):
            if "másolata" not in f.lower(): # ÉKEZETES SZŰRÉS
                print(f"  -> Másolás: {f}")
                shutil.copy(f, DIST_MAPPA)

    # Ikon másolása
    if os.path.exists(IKON):
        shutil.copy(IKON, DIST_MAPPA)

    print("[4/4] INDITAS.bat létrehozása...")
    bat_content = f'@echo off\ncd /d "%~dp0"\nstart "" "{APP_NEV}.exe"'
    with open(os.path.join(DIST_MAPPA, "INDITAS.bat"), "w", encoding="cp1250") as f:
        f.write(bat_content)

    print("\n" + "="*40)
    print("KÉSZ! A program a dist/ mappában van.")
    print("FONTOS: Az INDITAS.bat fájllal indítsd!")
    print("="*40)

if __name__ == "__main__":
    forditas()
