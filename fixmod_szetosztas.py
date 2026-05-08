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
        
        # Tanult adatok
        self.tura_irsz_lefedettseg = {} 
        self.uj_auto_lefedettseg = self.iranyitoszamok_betoltese()

        self.init_ui_elements()
        self.adatok_elokeszitese() 
        self.terkep_frissitese()

    def irsz_kinyeres(self, szoveg):
       if not szoveg: return ""
       import re
       #Keressünk 4 számjegyet
       talalat = re.search(r'(\d{4})', str(szoveg).replace('.0', ''))
       if talalat:
        return talalat.group(1)
       return ""


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
        for _, row in df_r.iterrows():
            p_nev = str(row.iloc[c_r['p']])
            turaszam = str(row.iloc[c_r['t']]).replace('.0', '').strip()
            
            # 1. JAVÍTÁS: Itt is tisztítjuk az irányítószámot a kinyerés előtt/alatt
            irsz = self.irsz_kinyeres(p_nev)
            if irsz:
                irsz = str(irsz).split('.')[0].strip() # Levágja a .0-át ha float-ként jönne
            
            if irsz and turaszam and turaszam != "nan":
                if irsz not in self.tura_irsz_lefedettseg:
                    self.tura_irsz_lefedettseg[irsz] = turaszam

        for ck, group in df_r.groupby(df_r.apply(lambda x: szuper_tisztito(megjelenitesre_vago(str(x.iloc[c_r['p']]))), axis=1)):
            nyers_p = str(group.iloc[0, c_r['p']])
            turaszam = str(group.iloc[0, c_r['t']]).replace('.0', '').strip()
            regi_p_kulcsok.add(ck)
            
            alkalmak = max(1, group.iloc[:, c_r['d']].nunique())
            p_b, temp_t = 0, {}
            for _, row in group.iterrows():
                t_n, t_db, t_s = suly_szamolo(str(row.iloc[c_r['f']]), row.iloc[c_r['m']], "60 l")
                if t_n not in temp_t: temp_t[t_n] = {'nev': t_n, 'db': 0, 'e': t_s/t_db if t_db>0 else t_s}
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

        if hasattr(self.parent, 'df_uj_raw'):
            for _, row in self.parent.df_uj_raw.iterrows():
                nyers_n = str(row.iloc[c_u['n']])
                nyers_c = str(row.iloc[c_u['c']])
                if szuper_tisztito(megjelenitesre_vago(nyers_c)) in regi_p_kulcsok: continue 
                
                # 2. JAVÍTÁS: Az új partnereknél is kényszerítjük a .0 levágását
                irsz_nyers = self.irsz_kinyeres(nyers_c) or self.irsz_kinyeres(nyers_n)
                irsz = str(irsz_nyers).split('.')[0].strip() if irsz_nyers else ""

                t_n, t_db, t_s = suly_szamolo(str(row.iloc[c_u['f']]), row.iloc[c_u['m']], str(row.iloc[c_u['e']]))
                self.minden_partner_adat.append({
                    'Túra': 'KIOSZTATLAN', 'Partner': nyers_n, 'Cim': nyers_c, 'Statusz': 'ÚJ', 
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
        # --- ÚJ RÉSZ: Lefedettség újratöltése a már meglévő adatokból ---
        for p in self.minden_partner_adat:
            vonal = str(p.get('Túra', ''))
            irsz = str(p.get('IRSZ', '')).split('.')[0].strip()
            # Ha van érvényes túrája és irányítószáma, mentsük el a szótárba
            if irsz and vonal and vonal not in ["KIOSZTATLAN", "nan", "None"] and "ISMERETLEN" not in vonal:
                self.tura_irsz_lefedettseg[irsz] = vonal
        # --- IDÁIG ---
        self.tree.clear()
        het_idx = self.het_valaszto.currentIndex()
        turasorok = {}
        
        for p in sorted(self.minden_partner_adat, key=lambda x: x['Statusz'] == 'ÚJ'):
            if not self.is_active_on_week(p['Intenz'], het_idx): continue
            
            vonal = p['Túra']
            irsz = p.get('IRSZ')

            if p['Statusz'] == 'ÚJ':
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
            p['Túra'] = vonal
            if vonal not in turasorok: turasorok[vonal] = {'b': 0, 'cnt': 0, 'items': []}
            turasorok[vonal]['b'] += p['Alap_B']; turasorok[vonal]['cnt'] += 1; turasorok[vonal]['items'].append(p)

        for t_nev in sorted(turasorok.keys()):
            dat = turasorok[t_nev]
            root_item = QTreeWidgetItem(self.tree)
            root_item.setText(0, f"🚚 {t_nev}"); root_item.setText(1, f"{dat['cnt']} megálló"); root_item.setText(2, f"{int(dat['b'])} kg")
            root_item.setBackground(0, QColor("#dfe6e9"))
            for s in dat['items']:
                child = QTreeWidgetItem(root_item)
                prefix = f"✨ [ÚJ] {s['Partner']}" if s['Statusz'] == 'ÚJ' else f"👤 {s['Partner']}"
                child.setText(0, f"  {prefix}"); child.setText(2, f"{int(s['Alap_B'])} kg")
                if s['Statusz'] == 'ÚJ': child.setForeground(0, QColor("#3498db"))

    def init_ui_elements(self):
        layout = QVBoxLayout(self)
        
        self.btn_kezi = QPushButton("📝 KÉZI SZERKESZTÉS ÉS SORREND")
        self.btn_kezi.setFixedHeight(45)
        self.btn_kezi.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold; border-radius: 5px;")
        self.btn_kezi.clicked.connect(self.megnyit_kezi_szerkeszto)
        layout.addWidget(self.btn_kezi)

        self.het_valaszto = QComboBox()
        self.het_valaszto.addItems(["Összesített Átlag", "1. Hét (Páratlan)", "2. Hét (Páros)", "3. Hét (Páratlan)", "4. Hét (Páros)"])
        self.het_valaszto.currentIndexChanged.connect(self.terkep_frissitese)
        layout.addWidget(self.het_valaszto)

        self.tree = QTreeWidget(); self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Túra / Partner", "Megállók / Intenzitás", "Súly (kg)"])
        self.tree.setColumnWidth(0, 600)
        layout.addWidget(self.tree)

        btns = QHBoxLayout()
        btn_e = QPushButton("💾 EXPORT EXCELBE"); btn_i = QPushButton("📂 IMPORT EXCELBŐL")
        btn_e.clicked.connect(self.export_to_excel); btn_i.clicked.connect(self.excel_beolvasas)
        btns.addWidget(btn_e); btns.addWidget(btn_i)
        layout.addLayout(btns)

    def megnyit_kezi_szerkeszto(self):
        try:
            import fixmod_szerkesztes
            het_idx = self.het_valaszto.currentIndex()
            turasulyok_ideiglenes = {}
            frissitett_adatok = []

            # 1. TÚRÁK ÁTVEZETÉSE AZ ADATOKBA
            for p in sorted(self.minden_partner_adat, key=lambda x: x['Statusz'] == 'ÚJ'):
                vonal = p.get('Túra', 'KIOSZTATLAN')
                irsz = p.get('IRSZ')

                if p['Statusz'] == 'ÚJ':
                    if vonal == "KIOSZTATLAN" or (vonal in turasulyok_ideiglenes and (turasulyok_ideiglenes[vonal] + p['Alap_B'] > self.MAX_BESZALLITAS)):
                        if irsz in self.uj_auto_lefedettseg:
                            found = False
                            for auto, napok in self.uj_auto_lefedettseg[irsz].items():
                                for nap in napok:
                                    proba = f"{auto} - {nap}"
                                    if proba not in turasulyok_ideiglenes or (turasulyok_ideiglenes[proba] + p['Alap_B'] <= self.MAX_BESZALLITAS):
                                        vonal = proba; found = True; break
                                if found: break
                        elif irsz in self.tura_irsz_lefedettseg:
                            vonal = self.tura_irsz_lefedettseg[irsz]
                        else:
                            vonal = f"ISMERETLEN ({irsz})"
                
                p['Túra'] = vonal
                if vonal not in turasulyok_ideiglenes: turasulyok_ideiglenes[vonal] = 0
                turasulyok_ideiglenes[vonal] += p['Alap_B']

                # Csak az aktuális hét partnereit visszük át (vagy mindenkit, ha átlag)
                if self.is_active_on_week(p['Intenz'], het_idx):
                    p_masolat = copy.deepcopy(p)
                    # JSON fix a szerkesztőnek
                    if 'Tetel' in p_masolat:
                        p_masolat['Tetel_JSON_FIX'] = json.dumps(p_masolat['Tetel'])
                    frissitett_adatok.append(p_masolat)

            self.parent.minden_partner_adat = frissitett_adatok
            self.accept() 

            dialog = fixmod_szerkesztes.KeziszerkesztoAblak(self.parent)
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Hiba", f"Szerkesztő hiba: {str(e)}")

    def export_to_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "Mentés", "Tura_Terv_Uj.xlsx", "Excel (*.xlsx)")
        if path:
            try:
                import os
                # Ha a fájl létezik, megpróbáljuk törölni, hogy ne maradjon benne régi adat
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        QMessageBox.warning(self, "Figyelem", "A fájl nyitva van valahol! Zárd be az Excelt!")
                        return

                df_to_save = pd.DataFrame(self.minden_partner_adat)
                
                # JSON mező generálása mentés előtt
                if 'Tetel' in df_to_save.columns:
                    df_to_save['Tetel_JSON_FIX'] = df_to_save['Tetel'].apply(lambda x: json.dumps(x) if x else "[]")
                    # Töröljük a komplex 'Tetel' oszlopot, amit az Excel nem szeret
                    df_to_save = df_to_save.drop(columns=['Tetel'])
                
                # Mentés
                with pd.ExcelWriter(path, engine='openpyxl') as writer:
                    df_to_save.to_excel(writer, index=False, sheet_name='TuraTerv')
                
                QMessageBox.information(self, "Siker", "A mentés valóban megtörtént!")
            except Exception as e:
                QMessageBox.critical(self, "Hiba", f"Hiba mentéskor: {e}")

    def excel_beolvasas(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import", "", "Excel (*.xlsx)")
        if path:
            
            try:
                import copy
                # 1. Beolvasás
                df = pd.read_excel(path, sheet_name='TuraTerv', engine='openpyxl')
                # A beolvasás után (df = pd.read_excel...):
                if 'IRSZ' in df.columns:
                    df['IRSZ'] = df['IRSZ'].apply(lambda x: str(x).replace('.0', '').strip() if pd.notnull(x) else "")

                # 2. JSON visszaalakítás
                if 'Tetel_JSON_FIX' in df.columns:
                    df['Tetel'] = df['Tetel_JSON_FIX'].apply(lambda x: json.loads(x) if isinstance(x, str) else [])
                else:
                    df['Tetel'] = [[] for _ in range(len(df))]

                # 3. Memória takarítás és betöltés
                self.minden_partner_adat = [] 
                self.minden_partner_adat = copy.deepcopy(df.to_dict('records'))
                
                # 4. Frissítés
                self.terkep_frissitese()
                
                QMessageBox.information(self, "Kész", f"Beöltve: {len(self.minden_partner_adat)} sor.")
            except Exception as e:
                import traceback
                print(traceback.format_exc()) # Kiírja a pontos hibát a konzolra
                QMessageBox.critical(self, "Hiba", f"Import hiba: {e}")


def szetosztas_ablak_megnyitasa(parent):
    dialog = SzetosztasDialog(parent); dialog.exec()
