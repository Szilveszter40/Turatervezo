import pandas as pd
import re
import numpy as np
from PyQt6.QtWidgets import (QDialog, QFormLayout, QSpinBox, QDialogButtonBox, 
                             QTabWidget, QWidget, QVBoxLayout, QFileDialog, QMessageBox)

# --- SEGÉDFÜGGVÉNYEK ---

def szuper_tisztito(s):
    s = str(s).upper()
    if "HU" in s: s = s.split("HU")[-1]
    return re.sub(r'[^A-Z0-9]', '', s).strip()[:15]

def megjelenitesre_vago(s):
    s = str(s).replace('\n', ' ').strip()
    match = re.search(r'\d{4}', s)
    if match:
        idx = match.start()
        resz = s[idx:idx+30]
        hazszam = re.search(r'\d+', resz[5:])
        if hazszam:
            return s[:idx + 5 + hazszam.end()].strip().replace(',', '')
    return s[:40]

def suly_szamolo(t, darab_ertek):
    """
    Kiszámolja a súlyt a megadott K- kódok és a külön oszlopból jövő darabszám alapján.
    """
    t = str(t).upper().strip()
    try:
        darab = int(float(darab_ertek)) if pd.notnull(darab_ertek) else 1
    except:
        darab = 1
    
    egyseg_suly = 60 # Alapértelmezett

    if "K-K20DB" in t: tipus, egyseg_suly = "K-K20DB", 20
    elif "K-KPALMADB" in t: tipus, egyseg_suly = "K-KPALMADB", 20
    elif "K-K10DB" in t: tipus, egyseg_suly = "K-K10DB", 10
    elif "K-P10DB" in t: tipus, egyseg_suly = "K-P10DB", 10
    elif "K-KSPECDB" in t: tipus, egyseg_suly = "K-KSPECDB", 10
    elif "K-P5DB" in t: tipus, egyseg_suly = "K-P5DB", 5
    elif "IBC" in t: tipus, egyseg_suly = "IBC", 1000
    elif any(x in t for x in ["HSO", "OLAJ"]): tipus, egyseg_suly = "HSO", 60
    elif any(x in t for x in ["ÉH", "ÉTKEZÉSI"]): tipus, egyseg_suly = "ÉH", 60
    elif any(x in t for x in ["ZSÍR", "ZSIRADÉK"]): tipus, egyseg_suly = "ZSÍR", 60
    else: tipus = t[:15]

    return tipus, darab, darab * egyseg_suly

# --- KONFIGURÁCIÓS FÜGGVÉNY ---

def indit_konfiguracio(parent):
    dialog = ExcelKonfigDialog(parent)
    if not dialog.exec(): return
    
    # Kimentjük az összes oszlopindexet
    parent.r_cols = {
        't': dialog.r_tura.value(), 'd': dialog.r_datum.value(), 
        'p': dialog.r_partner.value(), 'f': dialog.r_tetel.value(),
        'm': dialog.r_db.value() # Mennyiség oszlop
    }
    parent.u_cols = {
        'c': dialog.u_cim.value(), 'f': dialog.u_tetel.value(), 
        'i': dialog.u_intenz.value(), 'm': dialog.u_db.value() # Mennyiség oszlop
    }

    r_path, _ = QFileDialog.getOpenFileName(parent, "Régi Excel")
    u_path, _ = QFileDialog.getOpenFileName(parent, "Új Excel")
    
    if r_path and u_path:
        parent.df_regi_raw = pd.read_excel(r_path)
        parent.df_uj_raw = pd.read_excel(u_path)
        QMessageBox.information(parent, "Siker", "Adatok betöltve!")

class ExcelKonfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Oszlopok Beállítása")
        l = QVBoxLayout(self); self.tabs = QTabWidget()
        
        # Régi panel
        self.t1 = QWidget(); l1 = QFormLayout(self.t1)
        r = getattr(parent, 'r_cols', {'t':0,'d':1,'p':3,'f':5, 'm':6})
        self.r_tura=QSpinBox(); self.r_tura.setValue(r['t']); l1.addRow("Túra (A=0):", self.r_tura)
        self.r_datum=QSpinBox(); self.r_datum.setValue(r['d']); l1.addRow("Dátum (B=1):", self.r_datum)
        self.r_partner=QSpinBox(); self.r_partner.setValue(r['p']); l1.addRow("Partner (D=3):", self.r_partner)
        self.r_tetel=QSpinBox(); self.r_tetel.setValue(r['f']); l1.addRow("Tétel (F=5):", self.r_tetel)
        self.r_db=QSpinBox(); self.r_db.setValue(r['m']); l1.addRow("Darabszám (G=6):", self.r_db)
        
        # Új panel
        self.t2 = QWidget(); l2 = QFormLayout(self.t2)
        u = getattr(parent, 'u_cols', {'c':2,'f':5, 'i':1, 'm':6})
        self.u_cim=QSpinBox(); self.u_cim.setValue(u['c']); l2.addRow("Cím:", self.u_cim)
        self.u_tetel=QSpinBox(); self.u_tetel.setValue(u['f']); l2.addRow("Tétel:", self.u_tetel)
        self.u_db=QSpinBox(); self.u_db.setValue(u['m']); l2.addRow("Darabszám:", self.u_db)
        self.u_intenz=QSpinBox(); self.u_intenz.setValue(u['i']); l2.addRow("Intenzitás:", self.u_intenz)
        
        self.tabs.addTab(self.t1, "Régi"); self.tabs.addTab(self.t2, "Új"); l.addWidget(self.tabs)
        b = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        b.accepted.connect(self.accept); b.rejected.connect(self.reject); l.addWidget(b)
