from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtGui import QColor
import pandas as pd
from fixmod_konfig import szuper_tisztito, megjelenitesre_vago, suly_szamolo

def betoltes_es_feldolgozas(parent):
    if not hasattr(parent, 'df_uj_raw') or not hasattr(parent, 'df_regi_raw'): return
    parent.right_table.setRowCount(0)
    parent.right_table.setColumnCount(6)
    parent.right_table.setHorizontalHeaderLabels(["Név", "Cím", "Tétel", "Összsúly", "Intenzitás", "Státusz"])
    
    from fixmod_adatkezeles import intenzitas_szamolo
    c_r = parent.r_cols
    regi_info = {}
    for kl, group in parent.df_regi_raw.groupby(parent.df_regi_raw.iloc[:, c_r['p']].apply(lambda x: szuper_tisztito(megjelenitesre_vago(x)))):
        regi_info[kl] = {'n': megjelenitesre_vago(str(group.iloc[0, c_r['p']])), 'i': intenzitas_szamolo(group.iloc[:, c_r['d']])}

    uj_adatok = {} 
    c_u = parent.u_cols
    for _, row in parent.df_uj_raw.iterrows():
        v_n = megjelenitesre_vago(str(row.iloc[c_u['c']]))
        kl = szuper_tisztito(v_n)
        if not kl: continue
        if kl not in uj_adatok: uj_adatok[kl] = {'v_n': v_n, 'tetelek': {}, 'i_u': str(row.iloc[c_u['i']])}
        
        # Tétel és a mellette lévő DARABSZÁM oszlop
        tn, t_db, sl = suly_szamolo(row.iloc[c_u['f']], row.iloc[c_u['m']])
        if tn not in uj_adatok[kl]['tetelek']: uj_adatok[kl]['tetelek'][tn] = {'s': 0, 'd': 0}
        uj_adatok[kl]['tetelek'][tn]['s'] += sl
        uj_adatok[kl]['tetelek'][tn]['d'] += t_db

    parent.right_table.setRowCount(len(uj_adatok))
    for i, (kl, ad) in enumerate(uj_adatok.items()):
        ir = kl in regi_info
        rn = regi_info[kl]['n'] if ir else "- ÚJ HELYSZÍN -"
        tl = ", ".join([f"{n}({inf['d']})" for n, inf in ad['tetelek'].items()])
        os = sum(inf['s'] for inf in ad['tetelek'].values())
        mi = regi_info[kl]['i'] if ir else ad['i_u']

        vals = [rn, ad['v_n'], tl, f"{os} kg", mi, "MÁR PARTNER" if ir else "ÚJ"]
        for col, val in enumerate(vals):
            item = QTableWidgetItem(str(val))
            if ir: item.setBackground(QColor("#fff59d"))
            parent.right_table.setItem(i, col, item)
    parent.right_table.resizeColumnsToContents()
