import pandas as pd
import re
import numpy as np
from PyQt6.QtWidgets import (QDialog, QFormLayout, QSpinBox, QDialogButtonBox, 
                             QTabWidget, QWidget, QVBoxLayout, QFileDialog, QMessageBox, QLabel)

# --- KÖZÖS SEGÉDFÜGGVÉNYEK ---

def szuper_tisztito(s):
    """
    PÁROSÍTÓ KULCS: Csak a HU utáni rész első 15 tiszta karakterét nézi.
    Ez küszöböli ki a 'Slachta Mar' vs 'Slachta Marg' típusú eltéréseket.
    """
    s = str(s).upper()
    if "HU" in s:
        s = s.split("HU")[-1]
    # Csak betűk és számok maradnak
    tiszta = re.sub(r'[^A-Z0-9]', '', s).strip()
    # Csak az elejét nézzük (prefix match) a biztos összevonáshoz
    return tiszta[:15]

def megjelenitesre_vago(s):
    """Házszámig vágja a szöveget a listákban való megjelenítéshez."""
    s = str(s).replace('\n', ' ').strip()
    match = re.search(r'\d{4}', s) # Irányítószám keresése
    if match:
        idx = match.start()
        resz = s[idx:]
        hazszam = re.search(r'\d+', resz[5:]) # Első szám az IRSZ után
        if hazszam:
            vago_pont = idx + 5 + hazszam.end()
            return s[:vago_pont].strip().replace(',', '')
        return s[:idx + 20].strip().replace(',', '') # Ha nincs házszám, vágjunk fixen
    return s[:50]

def suly_szamolo(t):
    """
    Meghatározza a tétel típusát és kiszámolja a súlyt a szöveges leírás alapján.
    Visszatérési érték: (típus_neve, összsúly)
    """
    t = str(t).upper().strip()
    if not t or t == 'NAN':
        return "ISMERETLEN", 0

    # Darabszám kinyerése (keressük a '2 DB' formátumot, vagy csak egy számot)
    db_match = re.search(r'(\d+)\s*DB', t)
    if not db_match:
        db_match = re.search(r'(\d+)', t)
    darab = int(db_match.group(1)) if db_match else 1

    # Egységnyi súly meghatározása (kg/db)
    egyseg_suly = 0
    tipus = "EGYÉB"

    # Speciális konténerek és kódok ellenőrzése (ezek az erősebb szabályok)
    if "IBC" in t:
        tipus, egyseg_suly = "IBC", 1000
    elif any(x in t for x in ["K-K20DB", "K-PALMA"]):
        tipus, egyseg_suly = "K-K20", 20
    elif any(x in t for x in ["K-K10", "KSPEC", "K-P10"]):
        tipus, egyseg_suly = "K-K10/P10", 10
    elif "K-P5" in t:
        tipus, egyseg_suly = "K-P5", 5
    
    # Általános kategóriák (ha a fenti kódok nem találtak egyezést)
    elif any(x in t for x in ["HSO", "HASZNÁLT SÜTŐOLAJ", "OLAJ"]):
        tipus, egyseg_suly = "HSO", 60
    elif any(x in t for x in ["ÉH", "ÉTKEZÉSI", "ÉLELMISZER", "ÉTELHULLADÉK"]):
        tipus, egyseg_suly = "ÉH", 60
    elif any(x in t for x in ["ZSÍR", "ZSIRADÉK", "VIZES ZSÍR"]):
        tipus, egyseg_suly = "ZSÍR", 60
    else:
        # Alapértelmezett, ha felismerhető a szöveg, de nincs benne kód
        tipus, egyseg_suly = "HSO", 60

    return tipus, darab * egyseg_suly

# --- KONFIGURÁCIÓS FÜGGVÉNY ---

def indit_konfiguracio(parent):
    dialog = ExcelKonfigDialog(parent)
    if not dialog.exec(): return
    
    # Oszlopok mentése
    parent.r_cols = {'t': dialog.r_tura.value(), 'd': dialog.r_datum.value(), 'p': dialog.r_partner.value(), 'f': dialog.r_tetel.value()}
    parent.u_cols = {'c': dialog.u_cim.value(), 'f': dialog.u_tetel.value()}

    r_path, _ = QFileDialog.getOpenFileName(parent, "Régi Excel", "", "Excel (*.xlsx *.xlsb)")
    u_path, _ = QFileDialog.getOpenFileName(parent, "Új Excel", "", "Excel (*.xlsx)")
    
    if r_path and u_path:
        try:
            parent.df_regi_raw = pd.read_excel(r_path)
            parent.df_uj_raw = pd.read_excel(u_path)
            QMessageBox.information(parent, "Siker", "Adatok betöltve! Most már megnyithatja a listákat.")
            parent.status_label.setText("✓ Adatok a memóriában.")
        except Exception as e:
            QMessageBox.critical(parent, "Hiba", f"Beolvasási hiba: {str(e)}")

class ExcelKonfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Excel Oszlopok")
        l = QVBoxLayout(self); self.tabs = QTabWidget()
        self.t1 = QWidget(); l1 = QFormLayout(self.t1)
        self.r_tura=QSpinBox(); self.r_tura.setValue(0); l1.addRow("Túra:", self.r_tura)
        self.r_datum=QSpinBox(); self.r_datum.setValue(1); l1.addRow("Dátum:", self.r_datum)
        self.r_partner=QSpinBox(); self.r_partner.setValue(3); l1.addRow("Partner:", self.r_partner)
        self.r_tetel=QSpinBox(); self.r_tetel.setValue(5); l1.addRow("Tétel:", self.r_tetel)
        self.t2 = QWidget(); l2 = QFormLayout(self.t2)
        self.u_cim=QSpinBox(); self.u_cim.setValue(2); l2.addRow("Cím:", self.u_cim)
        self.u_tetel=QSpinBox(); self.u_tetel.setValue(5); l2.addRow("Tétel:", self.u_tetel)
        self.tabs.addTab(self.t1, "Régi"); self.tabs.addTab(self.t2, "Új"); l.addWidget(self.tabs)
        b = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        b.accepted.connect(self.accept); b.rejected.connect(self.reject); l.addWidget(b)
