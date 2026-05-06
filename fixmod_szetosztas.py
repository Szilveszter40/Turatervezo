import pandas as pd
import re
import json
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, 
                             QTreeWidgetItem, QLabel, QPushButton, QMessageBox, QComboBox, QFileDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from fixmod_konfig import szuper_tisztito, megjelenitesre_vago, suly_szamolo
from fixmod_adatkezeles import intenzitas_szamolo

class SzetosztasDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Kapacitás Tervező")
        self.resize(1450, 850)
        self.MAX_BESZALLITAS = 2100
        self.MAX_CIM = 25
        self.minden_partner_adat = []
        
        # Tanult adatok
        self.tura_irsz_lefedettseg = {} 
        self.uj_auto_lefedettseg = self.iranyitoszamok_betoltese()

        self.init_ui_elements()
        self.adatok_elokeszitese() 
        self.terkep_frissitese()

    def irsz_kinyeres(self, szoveg):
        """A GitHub-os kódod egyszerű és biztos módszere: az első 4 jegyű szám."""
        match = re.search(r'\d{4}', str(szoveg))
        return match.group(0) if match else None

    def iranyitoszamok_betoltese(self):
        lefedettseg = {} 
        fajl = "iranyitoszamok.xlsx"
        if not os.path.exists(fajl): return {}
        try:
            xls = pd.ExcelFile(fajl)
            for sheet in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet, dtype=str)
                for col in df.columns:
                    for irsz in df[col].dropna():
                        s = self.irsz_kinyeres(irsz)
                        if s:
                            if s not in lefedettseg: lefedettseg[s] = {}
                            if sheet not in lefedettseg[s]: lefedettseg[s][sheet] = []
                            lefedettseg[s][sheet].append(col)
            return lefedettseg
        except: return {}

    def adatok_elokeszitese(self):
        if not hasattr(self.parent, 'df_regi_raw'): return
        c_r = self.parent.r_cols
        c_u = getattr(self.parent, 'u_cols', {})
        regi_p_kulcsok = set()

        df_r = self.parent.df_regi_raw
        # 1. LÉPÉS: Tanulás a régi adatokból (A GitHub-os logikával)
        for _, row in df_r.iterrows():
            p_nev = str(row.iloc[c_r['p']])
            turaszam = str(row.iloc[c_r['t']]).replace('.0', '').strip()
            irsz = self.irsz_kinyeres(p_nev)
            if irsz and turaszam and turaszam != "nan":
                if irsz not in self.tura_irsz_lefedettseg:
                    self.tura_irsz_lefedettseg[irsz] = turaszam

        # 2. LÉPÉS: Régi partnerek betöltése
        for ck, group in df_r.groupby(df_r.apply(lambda x: szuper_tisztito(megjelenitesre_vago(str(x.iloc[c_r['p']]))), axis=1)):
            nyers_p = str(group.iloc[0, c_r['p']])
            turaszam = str(group.iloc[0, c_r['t']]).replace('.0', '').strip()
            regi_p_kulcsok.add(ck)
            
            alkalmak = max(1, group.iloc[:, c_r['d']].nunique())
            p_b, temp_t = 0, {}
            for _, row in group.iterrows():
                t_n, t_db, t_s = suly_szamolo(str(row.iloc[c_r['f']]), row.iloc[c_r['m']], "60 l")
                if t_n not in temp_t: temp_t[t_n] = {'db': 0, 'e': t_s/t_db if t_db>0 else t_s}
                temp_t[t_n]['db'] += t_db
            
            tetelek = []
            for n, a in temp_t.items():
                k_db = int((a['db']/alkalmak) + 0.5) if (a['db']/alkalmak) >= 1 else 1
                tetelek.append({'nev': n, 'db': k_db, 'suly': k_db * a['e']})
                if any(x in n for x in ["HSO", "ÉH", "ZSÍR"]): p_b += (k_db * a['e'])
            
            self.minden_partner_adat.append({
                'Túra': turaszam, 'Partner': nyers_p, 'Statusz': 'RÉGI',
                'Intenz': intenzitas_szamolo(group.iloc[:, c_r['d']]), 'Alap_B': p_b, 'Tetel': tetelek
            })

        # 3. LÉPÉS: Új partnerek besorolása
        if hasattr(self.parent, 'df_uj_raw'):
            for _, row in self.parent.df_uj_raw.iterrows():
                nyers_n = str(row.iloc[c_u['n']])
                nyers_c = str(row.iloc[c_u['c']])
                if szuper_tisztito(megjelenitesre_vago(nyers_c)) in regi_p_kulcsok: continue 
                
                irsz = self.irsz_kinyeres(nyers_c) or self.irsz_kinyeres(nyers_n)
                vonal = self.tura_irsz_lefedettseg.get(irsz, "KIOSZTATLAN")
                
                t_n, t_db, t_s = suly_szamolo(str(row.iloc[c_u['f']]), row.iloc[c_u['m']], str(row.iloc[c_u['e']]))
                self.minden_partner_adat.append({
                    'Túra': vonal, 'Partner': nyers_n, 'Cim': nyers_c, 'Statusz': 'ÚJ', 
                    'Intenz': str(row.iloc[c_u['i']]), 'Alap_B': t_s, 'IRSZ': irsz, 
                    'Tetel': [{'nev': t_n, 'db': t_db, 'suly': t_s}]
                })

    def is_active_on_week(self, intenz, het_idx):
        if het_idx == 0: return True
        s = str(intenz).upper()
        if "HETI" in s and "2" not in s: return True
        p = het_idx in [1, 3]
        if "2 HETI" in s or "KÉTHETI" in s:
            return p if ("PÁRATLAN" in s or "1" in s) else not p
        if "HAVI" in s: return het_idx == 1
        return False

    def terkep_frissitese(self):
        self.tree.clear()
        het_idx = self.het_valaszto.currentIndex()
        turasorok = {}
        
        for p in sorted(self.minden_partner_adat, key=lambda x: x['Statusz'] == 'ÚJ'):
            if not self.is_active_on_week(p['Intenz'], het_idx): continue
            
            vonal = p['Túra']
            irsz = p.get('IRSZ')

            if p['Statusz'] == 'ÚJ':
                # Ha nincs túra, vagy tele van a jelenlegi
                if vonal == "KIOSZTATLAN" or (vonal in turasorok and (turasorok[vonal]['b'] + p['Alap_B'] > self.MAX_BESZALLITAS)):
                    if irsz in self.uj_auto_lefedettseg:
                        found = False
                        for auto, napok in self.uj_auto_lefedettseg[irsz].items():
                            for nap in napok:
                                proba = f"{auto} - {nap}"
                                if proba not in turasorok or (turasorok[proba]['b'] + p['Alap_B'] <= self.MAX_BESZALLITAS):
                                    vonal = proba; found = True; break
                            if found: break
                    elif irsz in self.tura_irsz_lefedettseg:
                        vonal = self.tura_irsz_lefedettseg[irsz]
                    else:
                        vonal = f"❓ ISMERETLEN ({irsz})"

            if vonal not in turasorok: turasorok[vonal] = {'b': 0, 'cnt': 0, 'items': []}
            turasorok[vonal]['b'] += p['Alap_B']; turasorok[vonal]['cnt'] += 1; turasorok[vonal]['items'].append(p)

        for t_nev in sorted(turasorok.keys()):
            dat = turasorok[t_nev]
            p_item = QTreeWidgetItem(self.tree)
            p_item.setText(0, f"🚚 {t_nev}"); p_item.setText(1, f"{dat['cnt']} megálló"); p_item.setText(2, f"{int(dat['b'])} kg")
            for s in dat['items']:
                child = QTreeWidgetItem(p_item)
                prefix = f"✨ [ÚJ] {s['Partner']}" if s['Statusz'] == 'ÚJ' else f"👤 {s['Partner']}"
                child.setText(0, f"  {prefix}"); child.setText(2, f"{int(s['Alap_B'])} kg")
                if s['Statusz'] == 'ÚJ': child.setForeground(0, QColor("#3498db"))

    def init_ui_elements(self):
        layout = QVBoxLayout(self)
        felső_gombok = QHBoxLayout()
        self.btn_kezi = QPushButton("📝 KÉZI SZERKESZTÉS")
        self.btn_kezi.setStyleSheet("""
            background-color: #f39c12; 
            color: white; 
            font-weight: bold; 
            height: 40px; 
            margin-bottom: 10px;
            border-radius: 5px;
        """)
        self.btn_kezi.clicked.connect(self.megnyit_kezi_szerkeszto)
        felső_gombok.addWidget(self.btn_kezi)
        layout.addLayout(felső_gombok)
        self.het_valaszto = QComboBox(); self.het_valaszto.addItems(["Átlag", "1. Hét", "2. Hét", "3. Hét", "4. Hét"])
        self.het_valaszto.currentIndexChanged.connect(self.terkep_frissitese); layout.addWidget(self.het_valaszto)
        self.tree = QTreeWidget(); self.tree.setColumnCount(3); self.tree.setHeaderLabels(["Túra", "Címek", "Súly"]); layout.addWidget(self.tree)
        self.tree.setColumnWidth(0, 600)
        btns = QHBoxLayout(); btn_e = QPushButton("EXPORT"); btn_i = QPushButton("IMPORT")
        btns.addWidget(btn_e); btns.addWidget(btn_i); layout.addLayout(btns)
        btn_e.clicked.connect(self.export_to_excel); btn_i.clicked.connect(self.excel_beolvasas)

    def megnyit_kezi_szerkeszto(self):
        """Bezárja a szétosztást és elmenti az adatokat a főablakba a szerkesztőnek."""
        try:
            import fixmod_szerkesztes
            
            # KRITIKUS LÉPÉS: Átadjuk a listát a főablaknak, hogy a szerkesztő megtalálja
            self.parent.minden_partner_adat = self.minden_partner_adat
            
            # Bezárjuk a szétosztás ablakot
            self.accept() 

            # Elindítjuk az új szerkesztő ablakot
            dialog = fixmod_szerkesztes.KeziszerkesztoAblak(self.parent)
            dialog.exec()
                
        except Exception as e:
            QMessageBox.critical(self, "Hiba", f"Hiba a szerkesztő megnyitásakor: {str(e)}")

   

    def export_to_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "Mentés", "", "Excel (*.xlsx)")
        if path:
            df = pd.DataFrame(self.minden_partner_adat)
            df['Tetel_JSON'] = df['Tetel'].apply(json.dumps)
            df.drop(columns=['Tetel']).to_excel(path, index=False)

    def excel_beolvasas(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import", "", "Excel (*.xlsx)")
        if path:
            df = pd.read_excel(path)
            if 'Tetel_JSON' in df.columns: df['Tetel'] = df['Tetel_JSON'].apply(json.loads)
            self.minden_partner_adat = df.to_dict('records'); self.terkep_frissitese()

def szetosztas_ablak_megnyitasa(parent):
    dialog = SzetosztasDialog(parent); dialog.exec()
