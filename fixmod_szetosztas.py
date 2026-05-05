import pandas as pd
import re
import numpy as np
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, 
                             QTreeWidgetItem, QLabel, QPushButton, QMessageBox, QFileDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from fixmod_konfig import szuper_tisztito, megjelenitesre_vago, suly_szamolo
from fixmod_adatkezeles import intenzitas_szamolo

class SzetosztasDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Stratégiai Kapacitástérkép - Intenzitás Súlyozással")
        self.resize(1300, 850)
        self.MAX_BESZALLITAS = 2100
        self.aktualis_terv = [] 
        
        self.init_ui_elements()
        self.terkep_generalasa()

    def intenzitas_szorzo(self, szoveg):
        """Visszaadja a valószínűségi szorzót."""
        s = str(szoveg).upper()
        if "HETI" in s and "2" not in s: return 1.0
        if "2 HETI" in s or "KÉTHETI" in s: return 0.5
        if "HAVI" in s: return 0.25
        if "ESETI" in s: return 0.1
        return 1.0

    def irsz_kinyer(self, szoveg):
        match = re.search(r'\d{4}', str(szoveg))
        return match.group(0) if match else None

    def irsz_auto_es_nap_adatbazis(self):
        mapping = {} 
        if not os.path.exists("iranyitoszamok.xlsx"): return mapping
        try:
            excel_file = pd.ExcelFile("iranyitoszamok.xlsx")
            for sheet_name in excel_file.sheet_names:
                if "autó" in sheet_name.lower():
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    for col in df.columns:
                        irsz_lista = df[col].dropna().astype(str).str.strip().tolist()
                        for irsz in irsz_lista:
                            mapping[irsz] = sheet_name
        except: pass
        return mapping

    def init_ui_elements(self):
        layout = QVBoxLayout(self)
        self.info_label = QLabel("<b>Szimuláció:</b> A súlyok az intenzitás (Heti/Havi stb.) alapján súlyozva értendők.")
        layout.addWidget(self.info_label)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(6)
        self.tree.setHeaderLabels(["Túra / Partner", "Össz / Átlag megálló", "Beszáll (Súlyozott kg)", "Kiszáll (kg)", "Intenzitás", "Besorolás"])
        self.tree.setColumnWidth(0, 400)
        self.tree.setColumnWidth(1, 150)
        layout.addWidget(self.tree)

        btn_layout = QHBoxLayout()
        self.btn_export = QPushButton("💾 TÉRKÉP EXPORTÁLÁSA (EXCEL)")
        self.btn_export.setStyleSheet("background-color: #2c3e50; color: white; font-weight: bold; height: 40px;")
        self.btn_export.clicked.connect(self.export_to_excel)
        layout.addLayout(btn_layout)

    def terkep_generalasa(self):
        if not hasattr(self.parent, 'df_regi_raw') or not hasattr(self.parent, 'df_uj_raw'): return
        c_r, c_u = self.parent.r_cols, self.parent.u_cols
        irsz_alapterkep = self.irsz_auto_es_nap_adatbazis()
        
        regi_partnerek_kulcsai = set()
        tura_irsz_lefedettseg = {} 
        szimulalt_terv = []
        
        # 1. RÉGI ADATBÁZIS
        df_r = self.parent.df_regi_raw
        regi_kulcsok = df_r.apply(lambda x: szuper_tisztito(megjelenitesre_vago(str(x.iloc[c_r['p']]))), axis=1)
        
        for ck, group in df_r.groupby(regi_kulcsok):
            regi_partnerek_kulcsai.add(ck)
            turaszam = str(group.iloc[0, c_r['t']]).replace('.0', '')
            nyers_p = str(group.iloc[0, c_r['p']])
            irsz = self.irsz_kinyer(nyers_p)
            
            # Intenzitás és szorzó
            intenz = intenzitas_szamolo(group.iloc[:, c_r['d']])
            szorzo = self.intenzitas_szorzo(intenz)
            
            napok = {}
            for _, row in group.iterrows():
                d = str(row.iloc[c_r['d']])
                t_n, _, t_s = suly_szamolo(str(row.iloc[c_r['f']]), row.iloc[c_r['m']], "60 l")
                if d not in napok: napok[d] = {'b': 0, 'k': 0}
                if any(x in t_n for x in ["HSO", "ÉH", "ZSÍR"]): napok[d]['b'] += t_s
                else: napok[d]['k'] += t_s
            
            l_nap = max(1, len(napok))
            # Súlyozott átlag (Intenzitás figyelembevételével)
            avg_b = (sum(n['b'] for n in napok.values()) / l_nap) * szorzo
            avg_k = (sum(n['k'] for n in napok.values()) / l_nap) * szorzo
            
            szimulalt_terv.append({
                'Túra': turaszam, 'Partner': nyers_p, 'Suly_B': avg_b, 'Suly_K': avg_k,
                'Intenz': intenz, 'Szorzo': szorzo, 'Statusz': 'RÉGI', 'Megj': 'ALAPTERHELÉS'
            })
            if irsz and turaszam != "nan": tura_irsz_lefedettseg[irsz] = turaszam

        # 2. ÚJ LISTA
        for _, row in self.parent.df_uj_raw.iterrows():
            nyers_c = str(row.iloc[c_u['c']])
            kl = szuper_tisztito(megjelenitesre_vago(nyers_c))
            if kl in regi_partnerek_kulcsai: continue 

            nyers_n = str(row.iloc[c_u['n']])
            intenz_uj = str(row.iloc[c_u['i']])
            szorzo = self.intenzitas_szorzo(intenz_uj)
            irsz = self.irsz_kinyer(nyers_c)
            
            edeny = str(row.iloc[c_u['e']]) if 'e' in c_u else "60 l"
            t_n, t_db, t_s = suly_szamolo(str(row.iloc[c_u['f']]), row.iloc[c_u['m']], edeny)
            is_beszall = any(x in t_n for x in ["HSO", "ÉH", "ZSÍR"])

            vonal = tura_irsz_lefedettseg.get(irsz) or irsz_alapterkep.get(irsz, "KIOSZTATLAN")

            szimulalt_terv.append({
                'Túra': vonal, 'Partner': nyers_n, 
                'Suly_B': (t_s if is_beszall else 0) * szorzo,
                'Suly_K': (t_s if not is_beszall else 0) * szorzo,
                'Intenz': intenz_uj, 'Szorzo': szorzo, 'Statusz': 'ÚJ', 'Megj': 'MEGBÍZÁS'
            })

        self.aktualis_terv = szimulalt_terv
        self.megjelenites()

    def megjelenites(self):
        self.tree.clear()
        turasorok = {}
        for s in self.aktualis_terv:
            t = str(s['Túra'])
            if t not in turasorok:
                turasorok[t] = {'b': 0, 'k': 0, 'total_c': 0, 'weighted_c': 0.0, 'items': []}
            turasorok[t]['b'] += s['Suly_B']
            turasorok[t]['k'] += s['Suly_K']
            turasorok[t]['total_c'] += 1
            turasorok[t]['weighted_c'] += s['Szorzo'] # Összeadjuk a valószínűségeket
            turasorok[t]['items'].append(s)

        for t_nev in sorted(turasorok.keys(), key=lambda x: turasorok[x]['b'], reverse=True):
            dat = turasorok[t_nev]
            szaz = (dat['b'] / self.MAX_BESZALLITAS) * 100
            
            p_item = QTreeWidgetItem(self.tree)
            p_item.setFont(0, QFont("Arial", 10, QFont.Weight.Bold))
            p_item.setText(0, f"🚚 {t_nev}")
            # Megmutatjuk a fizikai darabszámot és a súlyozott darabszámot is
            p_item.setText(1, f"{dat['total_c']} cím (avg: {round(dat['weighted_c'], 1)})")
            p_item.setText(2, f"{int(dat['b'])} kg")
            p_item.setText(3, f"{int(dat['k'])} kg")
            p_item.setText(4, "-")
            p_item.setText(5, f"{szaz:.1f}%")
            
            if dat['b'] > self.MAX_BESZALLITAS:
                p_item.setBackground(5, QColor("#e74c3c"))
                p_item.setForeground(5, Qt.GlobalColor.white)

            for s in dat['items']:
                child = QTreeWidgetItem(p_item)
                icon = "✨" if s['Statusz'] == 'ÚJ' else "👤"
                child.setText(0, f"  {icon} {s['Partner']}")
                child.setText(2, f"{int(s['Suly_B'])} kg")
                child.setText(3, f"{int(s['Suly_K'])} kg")
                child.setText(4, s['Intenz'])
                child.setText(5, s['Statusz'])
                if s['Statusz'] == 'ÚJ':
                    child.setForeground(0, QColor("#2980b9"))

    def export_to_excel(self):
        if not self.aktualis_terv: return
        pd.DataFrame(self.aktualis_terv).to_excel("stratégiai_kapacitas_terv.xlsx", index=False)
        QMessageBox.information(self, "Kész", "Exportálva!")

def szetosztas_ablak_megnyitasa(parent):
    dialog = SzetosztasDialog(parent)
    dialog.exec()
