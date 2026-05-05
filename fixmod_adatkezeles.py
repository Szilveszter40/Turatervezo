import pandas as pd
import re
import numpy as np
from PyQt6.QtWidgets import QFileDialog, QTreeWidgetItem, QMessageBox, QHeaderView
from PyQt6.QtCore import Qt

# --- KÖZÖS SEGÉDFÜGGVÉNYEK ---

def csak_utcanevig_vago(szoveg):
    val = str(szoveg).replace('\n', ' ').strip()
    if not val or val.lower() == 'nan': return "Ismeretlen"
    irsz_match = re.search(r'\d{4}', val)
    if not irsz_match: return val.strip()
    alap_index = irsz_match.start()
    resz = val[alap_index:]
    hazszam_match = re.search(r'\d+', resz[4:])
    if hazszam_match:
        vago_pont = alap_index + 4 + hazszam_match.start()
        vegso = val[:vago_pont].strip()
    else:
        vegso = val.strip()
    vegso = vegso.replace(',', ' ')
    vegso = re.sub(r'\s+', ' ', vegso).strip()
    return vegso

def szuper_tisztito_kulcs(szoveg):
    vago_szoveg = csak_utcanevig_vago(szoveg)
    val = vago_szoveg.upper()
    val = re.sub(r'[^A-Z0-9]', '', val)
    return val if val else "ISMERETLEN"

def suly_es_adat_kinyer(tetel_nyers):
    t = str(tetel_nyers).strip().upper()
    if not t or t == 'NAN': return "ISMERETLEN", 0, 0
    db_match = re.search(r'(\d+)\s*DB', t)
    darab = int(db_match.group(1)) if db_match else 1
    s = 0
    if any(x in t for x in ["HSO", "HASZNÁLT SÜTŐOLAJ"]): s, t_nev = 60, "HSO"
    elif any(x in t for x in ["ÉH", "ÉTKEZÉSI", "ÉLELMISZER", "ÉTELHULLADÉK"]): 
        s, t_nev = 60, "ÉH"  # Mostantól "ÉH" néven fut 60 kg-mal
    elif any(x in t for x in ["VIZES ZSÍR"]): s, t_nev = 60, "ZSÍR"
    elif "K-K20" in t: s, t_nev = 20, "K-K20DB"
    elif "K-K10" in t: s, t_nev = 10, "K-K10DB"
    elif "K-SPEC" in t: s, t_nev = 10, "K-SPECDB"
    elif "K-P5" in t: s, t_nev = 5, "K-P5DB"
    elif "K-P10" in t: s, t_nev = 10, "K-P10DB"
    elif "K-PALMA" in t: s, t_nev = 20, "K-PALMADB"
    elif "IBC" in t: s, t_nev = 1000, "IBC"
    else: s, t_nev = 0, t[:20]
    return t_nev, darab, darab * s

def intenzitas_szamolo(datumok):
    d_series = pd.to_datetime(datumok, errors='coerce').dropna()
    d = sorted(d_series.dt.date.unique())
    if len(d) < 2: return "ESETI"
    diffs = [(d[i+1] - d[i]).days for i in range(len(d)-1)]
    m = np.median(diffs)
    if 2 <= m <= 10: return "HETI"
    if 11 <= m <= 22: return "2 HETI"
    return "HAVI" if m > 22 else "RENDSZERTELEN"

# --- FŐ FÜGGVÉNY ---

def partner_betoltes_regi(parent):
    path, _ = QFileDialog.getOpenFileName(parent, "Régi partnerek", "", "Excel (*.xlsx *.xlsb)")
    if not path: return
    try:
        parent.status_label.setText("⏳ Feldolgozás...")
        df = pd.read_excel(path, usecols=[0, 1, 3, 5], header=0)
        df.columns = ['Túra', 'Dátum', 'Partner', 'Tétel']
        df['Dátum'] = pd.to_datetime(df['Dátum'], errors='coerce')
        df = df.dropna(subset=['Dátum', 'Partner'])
        
        df['P_MEGJELENIK'] = df['Partner'].apply(csak_utcanevig_vago)
        df['CK'] = df['Partner'].apply(szuper_tisztito_kulcs)

        parent.left_tree.setUpdatesEnabled(False)
        parent.left_tree.clear()
        
        parent.regi_kapcsok = set(df['CK'].unique())
        parent.regi_nev_tar = df.drop_duplicates('CK').set_index('CK')['P_MEGJELENIK'].to_dict()

        grouped = df.groupby('CK')
        for ck, p_data in grouped:
            megjelenitett_nev = p_data['P_MEGJELENIK'].iloc[0]
            egyedi_turak = p_data['Túra'].dropna().unique()
            tura_szoveg = ", ".join(sorted([str(t).replace('.0', '') for t in egyedi_turak]))
            
            p_item = QTreeWidgetItem(parent.left_tree)
            p_item.setText(0, megjelenitett_nev)
            p_item.setText(2, tura_szoveg)
            p_item.setText(3, intenzitas_szamolo(p_data['Dátum']))
            
            d_grouped = p_data.groupby(p_data['Dátum'].dt.date)
            for d_date, d_data in sorted(d_grouped, key=lambda x: x[0], reverse=True):
                d_item = QTreeWidgetItem(p_item)
                d_item.setText(0, f"📅 {d_date}")
                
                napi_osszesito = {}
                napi_teljes_suly = 0
                
                for f_val in d_data['Tétel']:
                    t_n, db, s = suly_es_adat_kinyer(f_val)
                    if t_n in napi_osszesito:
                        napi_osszesito[t_n][0] += db
                        napi_osszesito[t_n][1] += s
                    else:
                        napi_osszesito[t_n] = [db, s]
                    napi_teljes_suly += s
                
                for t_nev, adatok in napi_osszesito.items():
                    t_item = QTreeWidgetItem(d_item)
                    t_item.setText(0, f"📦 {t_nev} ({adatok[0]} DB)")
                    t_item.setText(1, f"{adatok[1]} kg")
                
                d_item.setText(1, f"{napi_teljes_suly} kg")

        parent.left_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        parent.left_tree.setColumnWidth(0, 400)
        parent.left_tree.setUpdatesEnabled(True)
        parent.status_label.setText(f"✓ {len(grouped)} partner kész.")
    except Exception as e:
        if hasattr(parent, 'left_tree'): parent.left_tree.setUpdatesEnabled(True)
        QMessageBox.critical(parent, "Hiba", str(e))
