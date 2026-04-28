import os
import shutil
import subprocess
import sys

# --- BEÁLLÍTÁSOK ---
FO_FAJL = "tervezo_stabil.py"
IKON = "szallitas.ico"
APP_NEV = "Turatervezo_App"
DIST_MAPPA = os.path.join("dist", APP_NEV)

def forditas():
    print("[1/3] Takarítás...")
    for folder in ["dist", "build"]:
        if os.path.exists(folder):
            shutil.rmtree(folder)

    print("[2/3] Fájlok előkészítése a csomagoláshoz...")
    # Összegyűjtjük a parancsot a PyInstaller számára
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--onedir", "--windowed",
        "--collect-all", "PyQt6",
        "--icon", IKON,
        "--name", APP_NEV
    ]

    # Kikeressük az összes JSON, TXT és tiszta MOD fájlt a csomagoláshoz
    for f in os.listdir("."):
        f_lower = f.lower()
        if f_lower.endswith((".json", ".txt")):
            cmd.extend(["--add-data", f"{f};."])
            print(f"  + Adatfájl csomagolva: {f}")
        
        if f_lower.startswith("mod_") and f_lower.endswith(".py"):
            if "másolata" not in f_lower:
                cmd.extend(["--add-data", f"{f};."])
                print(f"  + Modul csomagolva: {f}")

    # Hozzáadjuk a fő fájlt a végén
    cmd.append(FO_FAJL)

    print("[3/3] Fordítás (Minden fájl az EXE belsejébe kerül)...")
    subprocess.run(cmd)

    # Létrehozzuk az INDITAS.bat fájlt a biztonság kedvéért
    bat_content = f'@echo off\ncd /d "%~dp0"\nstart "" "{APP_NEV}.exe"'
    with open(os.path.join(DIST_MAPPA, "INDITAS.bat"), "w", encoding="cp1250") as f:
        f.write(bat_content)

    print("\n" + "="*50)
    print("KÉSZ! Most már minden fájl az EXE belsejében van.")
    print("Próbáld ki a dist mappában a programot!")
    print("="*50)

if __name__ == "__main__":
    forditas()
