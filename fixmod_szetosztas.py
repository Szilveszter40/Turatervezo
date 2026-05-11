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
        # het_idx: 0 = Mind, 1 = Páratlan, 2 = Páros
        if het_idx == 0: return True
    
        s = str(intenz).upper()
    
        # 1. HETI szállítás: minden héten ott van
        if "HETI" in s and "2" not in s and "KÉTHETI" not in s: 
           return True
    
        # 2. PÁRATLAN hét (a ComboBox 1-es indexe)
        if het_idx == 1:
           # Akkor aktív, ha a névben benne van a PÁRATLAN, az 1-es, vagy az 1+3
           return any(x in s for x in ["PÁRATLAN", "1", "1+3"])
    
        # 3. PÁROS hét (a ComboBox 2-es indexe)
        if het_idx == 2:
           # Akkor aktív, ha a névben benne van a PÁROS, a 2-es, vagy a 2+4
           return any(x in s for x in ["PÁROS", "2", "2+4"])
    
        # Havi szállítás: döntsd el, melyik héten jelenjen meg (pl. mindig a páratlanon)
        if "HAVI" in s: 
           return het_idx == 1

        return False


    def terkep_frissitese(self):
        from PyQt6.QtGui import QColor
        self.tree.clear()
        het_idx = self.het_valaszto.currentIndex()
        
        rendszerezett = {} 
        egyeb = {}        

        # 1. Tanulás a már meglévő adatokból
        for p in self.minden_partner_adat:
            v_tmp = str(p.get('Túra', ''))
            i_tmp = str(p.get('IRSZ', '')).split('.')[0].strip()
            if i_tmp and v_tmp and v_tmp not in ["KIOSZTATLAN", "nan"] and "ISMERETLEN" not in v_tmp:
                self.tura_irsz_lefedettseg[i_tmp] = v_tmp

        # 2. Partnerek feldolgozása és kiosztása
        for p in sorted(self.minden_partner_adat, key=lambda x: x['Statusz'] == 'ÚJ'):
            if not self.is_active_on_week(p['Intenz'], het_idx): continue
            
            vonal = str(p.get('Túra', 'KIOSZTATLAN'))
            irsz = str(p.get('IRSZ', '')).split('.')[0].strip()

            if p['Statusz'] == 'ÚJ' and (vonal == 'KIOSZTATLAN' or "ISMERETLEN" in vonal):
                found = False
                if irsz in self.uj_auto_lefedettseg:
                    for auto, napok in self.uj_auto_lefedettseg[irsz].items():
                        for nap in napok:
                            vonal = f"{auto} - {nap}"
                            found = True
                            break
                        if found: break
                
                if not found and irsz in self.tura_irsz_lefedettseg:
                    vonal = self.tura_irsz_lefedettseg[irsz]
                    found = True
                
                if not found:
                    vonal = f"❓ ISMERETLEN ({irsz})"
            
            p['Túra'] = vonal

            # CSOPORTOSÍTÁS
            if len(vonal) > 0 and vonal[0].isdigit() and " - " in vonal:
                reszek = vonal.split(" - ", 1)
                auto_nev = reszek[0]
                nap_nev = reszek[1]
                
                if auto_nev not in rendszerezett: rendszerezett[auto_nev] = {}
                if nap_nev not in rendszerezett[auto_nev]:
                    rendszerezett[auto_nev][nap_nev] = {'suly': 0, 'db': 0, 'lista': []}
                
                target = rendszerezett[auto_nev][nap_nev]
                target['suly'] += p['Alap_B']
                target['db'] += 1
                target['lista'].append(p)
            else:
                if vonal not in egyeb: egyeb[vonal] = {'suly': 0, 'db': 0, 'lista': []}
                egyeb[vonal]['suly'] += p['Alap_B']
                egyeb[vonal]['db'] += 1
                egyeb[vonal]['lista'].append(p)

        # 3. MEGJELENÍTÉS - SZÁMMAL KEZDŐDŐK (Hierarchia: Autó -> Nap -> Partner)
        for auto in sorted(rendszerezett.keys()):
            auto_item = QTreeWidgetItem(self.tree)
            auto_suly = sum(n['suly'] for n in rendszerezett[auto].values())
            auto_item.setText(0, f"🚚 {auto}")
            auto_item.setText(2, f"{int(auto_suly)} kg össz.")
            auto_item.setBackground(0, QColor("#dfe6e9")) 

            for nap in sorted(rendszerezett[auto].keys()):
                dat = rendszerezett[auto][nap]
                nap_item = QTreeWidgetItem(auto_item)
                nap_item.setText(0, f"  📅 {nap}")
                nap_item.setText(1, f"{dat['db']} megálló")
                nap_item.setText(2, f"{int(dat['suly'])} kg")
                
                for s in dat['lista']:
                    child = QTreeWidgetItem(nap_item) 
                    partner_cim = s.get('Cim') or s.get('Cím') or ""
                    cim_text = f" | {partner_cim}" if partner_cim else ""
                    
                    if s['Statusz'] == 'ÚJ':
                        prefix = f"✨ [ÚJ] {s['Partner']}{cim_text}"
                        child.setForeground(0, QColor("#3498db"))
                    else:
                        prefix = f"👤 {s['Partner']}{cim_text}"
                    
                    child.setText(0, f"    {prefix}")
                    child.setText(2, f"{int(s['Alap_B'])} kg")

        # 4. MEGJELENÍTÉS - EGYÉB TÚRÁK (Hierarchia: Túra -> Partner)
        for t_nev in sorted(egyeb.keys()):
            dat = egyeb[t_nev]
            root_item = QTreeWidgetItem(self.tree)
            root_item.setText(0, f"🚚 {t_nev}")
            root_item.setText(1, f"{dat['db']} megálló")
            root_item.setText(2, f"{int(dat['suly'])} kg")
            root_item.setBackground(0, QColor("#dfe6e9"))
            
            for s in dat['lista']:
                child = QTreeWidgetItem(root_item)
                partner_cim = s.get('Cim') or s.get('Cím') or ""
                cim_text = f" | {partner_cim}" if partner_cim else ""
                
                if s['Statusz'] == 'ÚJ':
                    prefix = f"✨ [ÚJ] {s['Partner']}{cim_text}"
                    child.setForeground(0, QColor("#3498db"))
                else:
                    prefix = f"👤 {s['Partner']}{cim_text}"
                    
                child.setText(0, f"  {prefix}")
                child.setText(2, f"{int(s['Alap_B'])} kg")


    def init_ui_elements(self):
        layout = QVBoxLayout(self)

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

    def export_to_excel(self):
        # --- 1. LÉPÉS: ADATOK FRISSÍTÉSE A LISTÁBAN ---
        # Lefuttatjuk a frissítést, ami most már beleírja a p['Túra']-t a listába
        self.terkep_frissitese() 

        # --- 2. LÉPÉS: MENTÉS ---
        path, _ = QFileDialog.getSaveFileName(self, "Mentés", "Tura_Terv.xlsx", "Excel (*.xlsx)")
        if path:
            try:
                # Készítünk egy DataFrame-et a frissített listából
                df_to_save = pd.DataFrame(self.minden_partner_adat)
                
                # JSON fix a tételeknek
                if 'Tetel' in df_to_save.columns:
                    df_to_save['Tetel_JSON_FIX'] = df_to_save['Tetel'].apply(lambda x: json.dumps(x) if x else "[]")
                    df_to_save = df_to_save.drop(columns=['Tetel'])
                
                # Mentés az Excelbe
                df_to_save.to_excel(path, index=False, sheet_name='TuraTerv')
                
                QMessageBox.information(self, "Siker", "A szétosztott túrák mentése megtörtént!")
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
