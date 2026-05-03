import os
import shutil
import subprocess
import sys

# --- BEÁLLÍTÁSOK ---
FO_FAJL = "tervezo_stabil.py"
IKON = "szallitas.ico"
APP_NEV = "Turatervezo_App"
DIST_MAPPA = "dist"

def forditas():
    print("="*50)
    print(f"[{APP_NEV}] FORDÍTÁS: MINDEN EGY MAPÁBA (HORDOZHATÓ)")
    print("="*50)

    # 1. RÉGI FÁJLOK TÖRLÉSE
    for folder in ["dist", "build"]:
        if os.path.exists(folder):
            shutil.rmtree(folder)

    # 2. PYINSTALLER PARANCS
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--collect-all", "PyQt6",
        "--icon", IKON if os.path.exists(IKON) else "NONE",
        "--name", APP_NEV,
        "--hidden-import", "folium",
        "--hidden-import", "geopy",
        "--hidden-import", "geopy.geocoders.photon",
        "--hidden-import", "branca",
        "--hidden-import", "jinja2",
        "--hidden-import", "openpyxl",
        "--hidden-import", "pandas",
        "--hidden-import", "streamlit"
    ]

    # 3. MODULOK (.py) BEHELYEZÉSE AZ EXE-BE
    for f in os.listdir("."):
        if f.lower().startswith("mod_") and f.lower().endswith(".py"):
            if "másolata" not in f.lower():
                # A kódot beletesszük az EXE-be
                cmd.extend(["--add-data", f"{f};."])
                cmd.extend(["--hidden-import", f[:-3]])

    cmd.append(FO_FAJL)

    # 4. FORDÍTÁS
    subprocess.run(cmd)

    # 5. ADATOK MÁSOLÁSA AZ EXE MELLÉ
    print("\n[UTÓMUNKÁLATOK] Adatfájlok másolása a dist mappába...")
    adat_kiterjesztesek = (".json", ".txt", ".csv", ".kml", ".xlsx", ".xls")
    
    if os.path.exists(DIST_MAPPA):
        for f in os.listdir("."):
            if f.lower().endswith(adat_kiterjesztesek):
                shutil.copy2(f, os.path.join(DIST_MAPPA, f))
                print(f"  -> Másolva: {f}")

    print("\n" + "="*50)
    print("SIKER! A 'dist' mappában lévő fájlokat együtt kell mozgatnod.")
    print("="*50)

if __name__ == "__main__":
    forditas()
