from PyQt6.QtWidgets import QTreeWidgetItem
import pandas as pd
import numpy as np
from fixmod_konfig import szuper_tisztito, megjelenitesre_vago, suly_szamolo

def intenzitas_szamolo(datumok):
    d = sorted(list(set([pd.to_datetime(dt).date() for dt in datumok if pd.notnull(dt)])))
    if len(d) < 2: return "ESETI"
    diffs = [(d[i+1] - d[i]).days for i in range(len(d)-1)]
    m = np.median(diffs)
    if m <= 10: return "HETI"
    if m <= 22: return "2 HETI"
    if m <= 35: return "HAVI"
    return "RENDSZERTELEN"

def partner_betoltes_regi(parent):
    if not hasattr(parent, 'df_regi_raw'): return
    parent.left_tree.setUpdatesEnabled(False)
    parent.left_tree.clear()
    
    c = parent.r_cols
    df = parent.df_regi_raw
    adatok = {} 

    for _, row in df.iterrows():
        p_nyers = str(row.iloc[c['p']])
        v_nev = megjelenitesre_vago(p_nyers)
        kulcs = szuper_tisztito(v_nev) # Kulcs a vágott név elejéből
        
        if not kulcs: continue
        if kulcs not in adatok:
            adatok[kulcs] = {'nev': v_nev, 'turak': set(), 'napok': {}, 'd_list': []}
        
        adatok[kulcs]['turak'].add(str(row.iloc[c['t']]).replace('.0', ''))
        datum = pd.to_datetime(row.iloc[c['d']], errors='coerce')
        if pd.notnull(datum):
            d_str = datum.strftime('%Y-%m-%d')
            adatok[kulcs]['d_list'].append(datum)
            if d_str not in adatok[kulcs]['napok']: adatok[kulcs]['napok'][d_str] = []
            
            t_nev, t_suly = suly_szamolo(row.iloc[c['f']])
            adatok[kulcs]['napok'][d_str].append({'n': t_nev, 's': t_suly})

    for k, v in adatok.items():
        p_item = QTreeWidgetItem(parent.left_tree)
        p_item.setText(0, v['nev'])
        p_item.setText(2, ", ".join(sorted(v['turak'])))
        p_item.setText(3, intenzitas_szamolo(v['d_list']))
        
        for d_date in sorted(v['napok'].keys(), reverse=True):
            napi_suly = sum(item['s'] for item in v['napok'][d_date])
            d_item = QTreeWidgetItem(p_item)
            d_item.setText(0, f"📅 {d_date}")
            d_item.setText(1, f"{napi_suly} kg")
            
            for t in v['napok'][d_date]:
                t_item = QTreeWidgetItem(d_item)
                t_item.setText(0, f"📦 {t['n']}")
                t_item.setText(1, f"{t['s']} kg")

    parent.left_tree.setUpdatesEnabled(True)
