import pandas as pd
import re
import json
import os
import copy
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, 
                             QTreeWidgetItem, QLabel, QPushButton, QMessageBox, 
                             QComboBox, QFileDialog, QHeaderView)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from fixmod_konfig import szuper_tisztito, megjelenitesre_vago, suly_szamolo
from fixmod_adatkezeles import intenzitas_szamolo

class SzetosztasDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Kapacitás Tervező és Szétosztás")
        self.resize(1450, 850)
        self.MAX_BESZALLITAS = 2100
        self.MAX_CIM = 25
        
        self.minden_partner_adat = []
        self.tura_statisztika = {} # Itt tároljuk a túrák múltbéli átlagait
        self.tura_irsz_lefedettseg = {} 
        self.uj_auto_lefedettseg = self.iranyitoszamok_betoltese()

        self.init_ui_elements()
        self.adatok_elokeszitese() 
        self.terkep_frissitese()

    def irsz_kinyeres_pontos(self, szoveg):
        if not szoveg or szoveg == "nan": return ""
        s = str(szoveg).strip()
        # 1. "HU " utáni 4 számjegy (pl. "Partner neve HU 1234")
        talalat = re.search(r'HU\s*(\d{4})', s)
        if talalat: return talalat.group(1)
        # 2. Ha az elején van 4 számjegy (pl. "1234 Budapest...")
        talalat = re.search(r'^(\d{4})', s)
        if talalat: return talalat.group(1)
        return ""

    def iranyitoszamok_betoltese(self):
        lefedettseg = {} 
        # Fix elérési út a biztonság kedvéért
        fajl_utvonal = os.path.join(os.path.dirname(__file__), "iranyitoszamok.xlsx")
        
        if not os.path.exists(fajl_utvonal):
            print(f"HIBA: Nem található a fájl: {fajl_utvonal}")
            return {}
            
        try:
            xls = pd.ExcelFile(fajl_utvonal)
            for sheet in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet, dtype=str)
                for col in df.columns:
                    for irsz_ertek in df[col].dropna():
                        # Szigorú tisztítás: HU és pontok eltávolítása
                        s = str(irsz_ertek).replace('HU', '').replace('.0', '').strip()
                        if s.isdigit() and len(s) == 4:
                            if s not in lefedettseg: lefedettseg[s] = {}
                            lefedettseg[s][str(sheet)] = str(col)
            return lefedettseg
        except Exception as e:
            print(f"Excel hiba: {e}")
            return {}


    def adatok_elokeszitese(self):
        if not hasattr(self.parent, 'df_regi_raw'): return
        self.minden_partner_adat = []
        self.tura_statisztika = {}
        self.tura_irsz_lefedettseg = {}
        c_r = self.parent.r_cols
        df_r = self.parent.df_regi_raw

        # --- 1. TÚRA STATISZTIKA (Napi összsúlyok átlagolása) ---
        # Csoportosítás túra és dátum szerint
        for (t_nev, datum), nap_adatok in df_r.groupby([df_r.columns[c_r['t']], df_r.columns[c_r['d']]]):
            t_nev = str(t_nev).replace('.0', '').strip()
            if not t_nev or t_nev == "nan": continue
            
            if t_nev not in self.tura_statisztika:
                self.tura_statisztika[t_nev] = {'napok': 0, 'napi_osszsulyok': [], 'napi_megallok': []}
           
            napi_suly = 0
            for _, sor in nap_adatok.iterrows():
                _, _, s = suly_szamolo(sor.iloc[c_r['f']], sor.iloc[c_r['m']])
                napi_suly += s
            
            self.tura_statisztika[t_nev]['napok'] += 1
            self.tura_statisztika[t_nev]['napi_osszsulyok'].append(napi_suly)
            self.tura_statisztika[t_nev]['napi_megallok'].append(nap_adatok.iloc[:, c_r['p']].nunique())

        # Átlagok véglegesítése: (Napi összsúlyok összege / Napok száma)
        for t in self.tura_statisztika:
            n = max(1, self.tura_statisztika[t]['napok'])
            self.tura_statisztika[t]['atlag_cim'] = round(sum(self.tura_statisztika[t]['napi_megallok']) / n)
            self.tura_statisztika[t]['atlag_suly'] = sum(self.tura_statisztika[t]['napi_osszsulyok']) / n

        # IRSZ TÉRKÉP FELTÖLTÉSE (Régiek alapján)
        self.tura_irsz_lefedettseg = {}
        group_cols = df_r.apply(lambda x: (
            szuper_tisztito(megjelenitesre_vago(str(x.iloc[c_r['p']]))), 
            str(x.iloc[c_r['t']]).replace('.0', '').strip()
        ), axis=1)

        for (p_nev, t_szam), group in df_r.groupby(group_cols):
            nyers_p = str(group.iloc[0, c_r['p']])
            irsz = self.irsz_kinyeres_pontos(nyers_p)
            if irsz and t_szam not in ["KIOSZTATLAN", "nan", ""]:
                self.tura_irsz_lefedettseg[str(irsz)] = str(t_szam)


            self.minden_partner_adat.append({
                'Túra': t_szam, 'Partner': nyers_p, 'Statusz': 'RÉGI',
                'Intenzitás': intenzitas_szamolo(group.iloc[:, c_r['d']]),
                'Alap_B': (sum([suly_szamolo(r.iloc[c_r['f']], r.iloc[c_r['m']])[2] for _, r in group.iterrows()]) / 
                           max(1, group.iloc[:, c_r['d']].nunique())),
                'IRSZ': irsz
            })

        # ÚJ PARTNEREK BEOLVASÁSA (Címmel együtt)
        if hasattr(self.parent, 'df_uj_raw'):
            df_u = self.parent.df_uj_raw
            c_u = self.parent.u_cols  # CSAK c_u-t használunk itt!
            
            for _, row in df_u.iterrows():
                # Biztonságos indexelés: ha nincs megadva, alapértelmezett indexeket használunk
                p_nev = str(row.iloc[c_u.get('p', 0)])
                p_cim = str(row.iloc[c_u.get('c', 1)]) if len(row) > 1 else ""
                
                # Súlyszámítás javítása: c_u-t használunk c_r helyett!
                f_val = row.iloc[c_u.get('f', 2)] if len(row) > 2 else ""
                m_val = row.iloc[c_u.get('m', 3)] if len(row) > 3 else 1
                
                _, _, s = suly_szamolo(f_val, m_val)

                # IRSZ kinyerése
                irsz = self.irsz_kinyeres_pontos(p_nev)
                if not irsz:
                    irsz = self.irsz_kinyeres_pontos(p_cim)

                self.minden_partner_adat.append({
                    'Túra': 'KIOSZTATLAN', 
                    'Partner': p_nev, 
                    'Cim': p_cim, 
                    'Statusz': 'ÚJ', 
                    'Intenzitás': 'HETI',
                    'Alap_B': s, 
                    'IRSZ': str(irsz)
                })

    def is_active_on_week(self, intenzitas, het_idx):
        if het_idx == 0: return True
        s = str(intenzitas).upper()
        if "HETI" in s and "2" not in s and "KÉTHETI" not in s: return True
        if het_idx in [1, 3]: return any(x in s for x in ["PÁRATLAN", "1", "1+3", "HAVI"])
        if het_idx in [2, 4]: return any(x in s for x in ["PÁROS", "2", "2+4"])
        return False

    def terkep_frissitese(self):
        self.tree.clear()
        aktualis_stat = copy.deepcopy(self.tura_statisztika)
        megjelenitendo_turak = {str(t): [] for t in self.tura_statisztika.keys()}
        megjelenitendo_turak["KIOSZTATLAN"] = []

        # --- 1. LÉPÉS: Kiosztás a RÉGI túrákba ---
        for p in self.minden_partner_adat:
            vonal = str(p.get('Túra', 'KIOSZTATLAN'))
            irsz = str(p.get('IRSZ', '')).strip()

            if p['Statusz'] == 'ÚJ' and (vonal == 'KIOSZTATLAN' or vonal == "nan"):
                if irsz in self.tura_irsz_lefedettseg:
                    cel = self.tura_irsz_lefedettseg[irsz]
                    if aktualis_stat.get(cel, {}).get('atlag_cim', 0) < self.MAX_CIM:
                        vonal = cel
                        aktualis_stat[vonal]['atlag_cim'] += 1
                        p['Túra'] = vonal

            if vonal not in megjelenitendo_turak: megjelenitendo_turak[vonal] = []
            megjelenitendo_turak[vonal].append(p)

        # --- 2. LÉPÉS: A maradék KIOSZTATLAN szétosztása az iranyitoszamok.xlsx alapján ---
        maradek = megjelenitendo_turak["KIOSZTATLAN"][:] # Másolat a maradékról
        megjelenitendo_turak["KIOSZTATLAN"] = [] # Kiürítjük, hogy újra töltsük

        for p in maradek:
            vonal = "KIOSZTATLAN"
            irsz = str(p.get('IRSZ', '')).strip()

            if irsz in self.uj_auto_lefedettseg:
                # Kivesszük az Autót és a Napot az Excelből
                auto_nev = list(self.uj_auto_lefedettseg[irsz].keys())[0]
                nap_nev = self.uj_auto_lefedettseg[irsz][auto_nev]
                cel_vonal = f"{auto_nev} | {nap_nev}"
                
                # Itt nem nézünk limitet (vagy magasabb limitet nézünk), hogy mindenképp bekerüljön
                if cel_vonal not in aktualis_stat:
                    aktualis_stat[cel_vonal] = {'atlag_cim': 0, 'atlag_suly': 0}
                
                vonal = cel_vonal
                aktualis_stat[vonal]['atlag_cim'] += 1
                p['Túra'] = vonal

            if vonal not in megjelenitendo_turak: megjelenitendo_turak[vonal] = []
            megjelenitendo_turak[vonal].append(p)

        # MEGJELENÍTÉS
        for t_nev in sorted(megjelenitendo_turak.keys()):
            stat = aktualis_stat.get(t_nev, {'atlag_cim': 0, 'atlag_suly': 0})
            root = QTreeWidgetItem(self.tree)
            
            # Túra neve (🚚 Régi név vagy 🚚 Autó | Nap)
            root.setText(0, f"🚚 {t_nev}")
            root.setText(1, f"Átlag: {int(round(stat['atlag_cim']))} megálló")
            root.setText(2, f"{int(stat['atlag_suly'])} kg")
            
            if round(stat['atlag_cim']) > self.MAX_CIM:
                root.setBackground(0, QColor("#ff7675"))

            for p_obj in megjelenitendo_turak[t_nev]:
                child = QTreeWidgetItem(root)
                prefix = "✨ [ÚJ]" if p_obj['Statusz'] == 'ÚJ' else "👤"
                irsz_str = f"({p_obj.get('IRSZ','')})"
                
                if p_obj['Statusz'] == 'ÚJ':
                    child.setText(0, f"  {prefix} {p_obj['Partner']} | {p_obj.get('Cim', '')} {irsz_str}")
                    child.setForeground(0, QColor("#3498db"))
                else:
                    child.setText(0, f"  {prefix} {p_obj['Partner']} {irsz_str}")
                
                child.setText(1, str(p_obj.get('Intenzitás', '')))
                child.setText(2, f"{int(p_obj.get('Alap_B', 0))} kg")

    def init_ui_elements(self):
        layout = QVBoxLayout(self)
        self.het_valaszto = QComboBox()
        self.het_valaszto.addItems(["Összesített Átlag", "1. Hét (Páratlan)", "2. Hét (Páros)", "3. Hét (Páratlan)", "4. Hét (Páros)"])
        self.het_valaszto.currentIndexChanged.connect(self.terkep_frissitese)
        layout.addWidget(QLabel("Válasszon hetet a tervezéshez:"))
        layout.addWidget(self.het_valaszto)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Túra / Partner", "Átlagos terhelés", "Súly (kg)"])
        self.tree.setColumnWidth(0, 600)
        layout.addWidget(self.tree)

        btns = QHBoxLayout()
        btn_e = QPushButton("💾 EXPORT"); btn_i = QPushButton("📂 IMPORT")
        btn_e.clicked.connect(self.export_to_excel); btn_i.clicked.connect(self.excel_beolvasas)
        btns.addWidget(btn_e); btns.addWidget(btn_i)
        layout.addLayout(btns)

    def export_to_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "Mentés", "Tura_Terv.xlsx", "Excel (*.xlsx)")
        if path:
            pd.DataFrame(self.minden_partner_adat).to_excel(path, index=False)
            QMessageBox.information(self, "Siker", "Excel mentve!")

    def excel_beolvasas(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import", "", "Excel (*.xlsx)")
        if path:
            try:
                df = pd.read_excel(path)
                self.minden_partner_adat = df.to_dict('records')
                self.terkep_frissitese()
            except Exception as e:
                QMessageBox.critical(self, "Hiba", str(e))

def szetosztas_ablak_megnyitasa(parent):
    dialog = SzetosztasDialog(parent)
    dialog.exec()
