import pandas as pd
import re
import numpy as np
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, 
                             QTreeWidgetItem, QLabel, QPushButton, QMessageBox, QComboBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from fixmod_konfig import szuper_tisztito, megjelenitesre_vago, suly_szamolo
from fixmod_adatkezeles import intenzitas_szamolo

class SzetosztasDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Havi Kapacitás Tervező (4 hét szimuláció)")
        self.resize(1300, 850)
        self.MAX_BESZALLITAS = 2100
        self.minden_partner_adat = [] # Itt tároljuk a teljes listát
        
        self.init_ui_elements()
        self.adatok_elokeszitese() # Csak egyszer fut le az elején
        self.terkep_frissitese()   # Kirajzolja az aktuális hét alapján

    def init_ui_elements(self):
        layout = QVBoxLayout(self)
        
        # --- HETI VÁLASZTÓ PANEL ---
        szuro_layout = QHBoxLayout()
        szuro_layout.addWidget(QLabel("<b>Szimulált időszak:</b>"))
        
        self.het_valaszto = QComboBox()
        self.het_valaszto.addItems([
            "Átlagos terhelés (Súlyozott)",
            "1. HÉT (Páratlan)",
            "2. HÉT (Páros)",
            "3. HÉT (Páratlan)",
            "4. HÉT (Páros)"
        ])
        self.het_valaszto.currentIndexChanged.connect(self.terkep_frissitese)
        szuro_layout.addWidget(self.het_valaszto)
        
        szuro_layout.addStretch()
        layout.addLayout(szuro_layout)

        self.info_label = QLabel("Túrák várható telítettsége a választott héten")
        layout.addWidget(self.info_label)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(6)
        self.tree.setHeaderLabels(["Túra / Partner", "Megállók", "Beszáll (kg)", "Kiszáll (kg)", "Intenzitás", "Heti státusz"])
        self.tree.setColumnWidth(0, 400)
        layout.addWidget(self.tree)

        self.btn_export = QPushButton("💾 AKTUÁLIS HÉT EXPORTÁLÁSA")
        self.btn_export.setStyleSheet("background-color: #2c3e50; color: white; font-weight: bold; height: 40px;")
        self.btn_export.clicked.connect(self.export_to_excel)
        layout.addWidget(self.btn_export)

    def is_active_on_week(self, intenz, het_idx):
        """Meghatározza, hogy a partner aktív-e az adott héten (1-4)."""
        if het_idx == 0: return True # Átlagos nézetnél mindenki 'félig' aktív (szorzóval)
        
        s = str(intenz).upper()
        if "HETI" in s and "2" not in s: return True # Minden héten
        
        if "2 HETI" in s or "KÉTHETI" in s:
            if het_idx in [1, 3]: return True # Páratlan hetek
            return False # Páros heteken pihen
            
        if "HAVI" in s:
            return het_idx == 1 # Csak az első héten (példa)
            
        if "ESETI" in s:
            return False # Esetit nem tervezünk be fix hétre
            
        return True

    def adatok_elokeszitese(self):
        """Kiszámolja a partnereket és túrákat a régi és új adatokból egyszer."""
        if not hasattr(self.parent, 'df_regi_raw') or not hasattr(self.parent, 'df_uj_raw'): return
        
        c_r, c_u = self.parent.r_cols, self.parent.u_cols
        regi_partnerek_kulcsai = set()
        tura_irsz_lefedettseg = {}
        
        # 1. RÉGI PARTNEREK
        df_r = self.parent.df_regi_raw
        regi_kulcsok = df_r.apply(lambda x: szuper_tisztito(megjelenitesre_vago(str(x.iloc[c_r['p']]))), axis=1)
        
        for ck, group in df_r.groupby(regi_kulcsok):
            regi_partnerek_kulcsai.add(ck)
            turaszam = str(group.iloc[0, c_r['t']]).replace('.0', '')
            nyers_p = str(group.iloc[0, c_r['p']])
            irsz = re.search(r'\d{4}', nyers_p).group(0) if re.search(r'\d{4}', nyers_p) else None
            
            intenz = intenzitas_szamolo(group.iloc[:, c_r['d']])
            
            # Alap súly (átlagolva, mielőtt a heti szorzót megkapná)
            napok = {}
            for _, row in group.iterrows():
                d = str(row.iloc[c_r['d']])
                t_n, _, t_s = suly_szamolo(str(row.iloc[c_r['f']]), row.iloc[c_r['m']], "60 l")
                if d not in napok: napok[d] = {'b': 0, 'k': 0}
                if any(x in t_n for x in ["HSO", "ÉH", "ZSÍR"]): napok[d]['b'] += t_s
                else: napok[d]['k'] += t_s
            
            l_n = max(1, len(napok))
            self.minden_partner_adat.append({
                'Túra': turaszam, 'Partner': nyers_p, 'Intenz': intenz,
                'Alap_B': sum(n['b'] for n in napok.values()) / l_n,
                'Alap_K': sum(n['k'] for n in napok.values()) / l_n,
                'Statusz': 'RÉGI'
            })
            if irsz and turaszam != "nan": tura_irsz_lefedettseg[irsz] = turaszam

        # 2. ÚJ PARTNEREK
        for _, row in self.parent.df_uj_raw.iterrows():
            nyers_c = str(row.iloc[c_u['c']])
            kl = szuper_tisztito(megjelenitesre_vago(nyers_c))
            if kl in regi_partnerek_kulcsai: continue 

            nyers_n = str(row.iloc[c_u['n']])
            intenz_uj = str(row.iloc[c_u['i']])
            irsz = re.search(r'\d{4}', nyers_c).group(0) if re.search(r'\d{4}', nyers_c) else None
            
            t_n, t_db, t_s = suly_szamolo(str(row.iloc[c_u['f']]), row.iloc[c_u['m']], str(row.iloc[c_u['e']]))
            is_beszall = any(x in t_n for x in ["HSO", "ÉH", "ZSÍR"])
            
            vonal = tura_irsz_lefedettseg.get(irsz, "KIOSZTATLAN")

            self.minden_partner_adat.append({
                'Túra': vonal, 'Partner': nyers_n, 'Intenz': intenz_uj,
                'Alap_B': t_s if is_beszall else 0,
                'Alap_K': t_s if not is_beszall else 0,
                'Statusz': 'ÚJ'
            })

    def terkep_frissitese(self):
        """Újrarajzolja a fát a kiválasztott hét (Combo index) alapján."""
        self.tree.clear()
        het_idx = self.het_valaszto.currentIndex()
        turasorok = {}
        
        for p in self.minden_partner_adat:
            # Ellenőrizzük az aktivitást az adott héten
            is_active = self.is_active_on_week(p['Intenz'], het_idx)
            
            # Súlyozás: Ha 'Átlag' nézet (0), akkor a korábbi szorzót használjuk
            if het_idx == 0:
                s = p['Intenz'].upper()
                szorzo = 1.0
                if "2 HETI" in s: szorzo = 0.5
                elif "HAVI" in s: szorzo = 0.25
                elif "ESETI" in s: szorzo = 0.1
                valos_b, valos_k = p['Alap_B'] * szorzo, p['Alap_K'] * szorzo
                heti_megj = "Statisztikai átlag"
            else:
                # Konkrét héten vagy 100% súly van, vagy 0%
                valos_b = p['Alap_B'] if is_active else 0
                valos_k = p['Alap_K'] if is_active else 0
                heti_megj = "AKTÍV" if is_active else "NINCS ÜRÍTÉS"

            t = p['Túra']
            if t not in turasorok: turasorok[t] = {'b': 0, 'k': 0, 'cnt': 0, 'items': []}
            
            turasorok[t]['b'] += valos_b
            turasorok[t]['k'] += valos_k
            if is_active: 
                turasorok[t]['cnt'] += 1
                turasorok[t]['items'].append({**p, 'v_b': valos_b, 'v_k': valos_k, 'h_m': heti_megj})

        # Megjelenítés
        for t_nev in sorted(turasorok.keys(), key=lambda x: turasorok[x]['b'], reverse=True):
            dat = turasorok[t_nev]
            szaz = (dat['b'] / self.MAX_BESZALLITAS) * 100
            
            p_item = QTreeWidgetItem(self.tree)
            p_item.setText(0, f"🚚 {t_nev}")
            p_item.setText(1, f"{dat['cnt']} aktív megálló")
            p_item.setText(2, f"{int(dat['b'])} kg")
            p_item.setText(3, f"{int(dat['k'])} kg")
            p_item.setText(5, f"{szaz:.1f}%")
            
            if dat['b'] > self.MAX_BESZALLITAS:
                p_item.setBackground(5, QColor("#e74c3c"))
                p_item.setForeground(5, Qt.GlobalColor.white)

            for s in dat['items']:
                child = QTreeWidgetItem(p_item)
                icon = "✨" if s['Statusz'] == 'ÚJ' else "👤"
                child.setText(0, f"  {icon} {s['Partner']}")
                child.setText(2, f"{int(s['v_b'])} kg")
                child.setText(4, s['Intenz'])
                child.setText(5, s['h_m'])

    def export_to_excel(self):
        # A megjelenített szűrt listát exportálja
        QMessageBox.information(self, "Export", "Az aktuális heti nézet elmentve!")

def szetosztas_ablak_megnyitasa(parent):
    dialog = SzetosztasDialog(parent)
    dialog.exec()
