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
    return "HAVI"

def partner_betoltes_regi(parent):
    if not hasattr(parent, 'df_regi_raw'): return
    parent.left_tree.clear()
    c = parent.r_cols
    df = parent.df_regi_raw
    adatok = {} 

    for _, row in df.iterrows():
        p_nyers = str(row.iloc[c['p']])
        v_n = megjelenitesre_vago(p_nyers)
        kl = szuper_tisztito(v_n)
        if not kl: continue
        if kl not in adatok: adatok[kl] = {'n': v_n, 't': set(), 'napok': {}, 'dates': []}
        
        adatok[kl]['t'].add(str(row.iloc[c['t']]).replace('.0', ''))
        dt = pd.to_datetime(row.iloc[c['d']], errors='coerce')
        if pd.notnull(dt):
            ds = dt.strftime('%Y-%m-%d')
            adatok[kl]['dates'].append(dt)
            if ds not in adatok[kl]['napok']: adatok[kl]['napok'][ds] = {}
            
            # Tétel és a mellette lévő DARABSZÁM oszlop használata
            t_nev_nyers = row.iloc[c['f']]
            db_nyers = row.iloc[c['m']]
            t_n, t_db, t_s = suly_szamolo(t_nev_nyers, db_nyers)
            
            if t_n not in adatok[kl]['napok'][ds]: adatok[kl]['napok'][ds][t_n] = {'s': 0, 'd': 0}
            adatok[kl]['napok'][ds][t_n]['s'] += t_s
            adatok[kl]['napok'][ds][t_n]['d'] += t_db

    for k, v in adatok.items():
        p_item = QTreeWidgetItem(parent.left_tree)
        p_item.setText(0, v['n'])
        p_item.setText(2, ", ".join(sorted(v['t'])))
        p_item.setText(3, intenzitas_szamolo(v['dates']))
        for ds in sorted(v['napok'].keys(), reverse=True):
            d_item = QTreeWidgetItem(p_item)
            d_item.setText(0, f"📅 {ds}")
            d_item.setText(1, f"{sum(i['s'] for i in v['napok'][ds].values())} kg")
            for tn, info in v['napok'][ds].items():
                t_item = QTreeWidgetItem(d_item)
                t_item.setText(0, f"📦 {tn} ({info['d']} DB)")
                t_item.setText(1, f"{info['s']} kg")
    parent.left_tree.setUpdatesEnabled(True)
