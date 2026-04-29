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
    print(f"[{APP_NEV}] FORDÍTÁS: MINDEN AZ EXE-BE + KÜLSŐ EXCEL")
    print("="*50)

    # 1. TAKARÍTÁS
    for folder in ["dist", "build"]:
        if os.path.exists(folder):
            shutil.rmtree(folder)

    # 2. PARANCS ÖSSZEÁLLÍTÁSA
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",           # Mindent egy fájlba
        "--windowed",          # Nincs fekete ablak
        "--collect-all", "PyQt6",
        "--icon", IKON if os.path.exists(IKON) else "NONE",
        "--name", APP_NEV
    ]

    # 3. MODULOK ÉS ADATOK HOZZÁADÁSA (Bele az EXE-be)
    for f in os.listdir("."):
        if f.lower().endswith((".json", ".txt", ".csv", ".kml")):
            cmd.extend(["--add-data", f"{f};."])
        
        if f.lower().startswith("mod_") and f.lower().endswith(".py"):
            if "másolata" not in f.lower():
                cmd.extend(["--add-data", f"{f};."])
                cmd.extend(["--hidden-import", f[:-3]])

    # AZ EXCELT IS BELETESSZÜK BELSŐ TARTALÉKNAK
    if os.path.exists("iranyitoszamok.xlsx"):
        cmd.extend(["--add-data", "iranyitoszamok.xlsx;."])

    cmd.append(FO_FAJL)

    # 4. FORDÍTÁS INDÍTÁSA
    subprocess.run(cmd)

    # 5. A KRITIKUS LÉPÉS: EXCEL KIMÁSOLÁSA AZ EXE MELLÉ
    # Ha a programod nem találja meg belül, akkor kívülről fogja beolvasni.
    print("\n[UTÓMUNKÁLATOK] Excel fájl elhelyezése az EXE mellé...")
    exe_helye = os.path.join(DIST_MAPPA, f"{APP_NEV}.exe")
    excel_cel = os.path.join(DIST_MAPPA, "iranyitoszamok.xlsx")
    
    if os.path.exists("iranyitoszamok.xlsx"):
        shutil.copy2("iranyitoszamok.xlsx", excel_cel)
        print(f"  -> SIKER: Az 'iranyitoszamok.xlsx' most már ott van a '{APP_NEV}.exe' mellett!")

    print("\n" + "="*50)
    print("KÉSZ! Próbáld ki a dist mappában lévő programot.")
    print("MINDIG tartsd az Excel fájlt az EXE mellett!")
    print("="*50)

if __name__ == "__main__":
    forditas()
