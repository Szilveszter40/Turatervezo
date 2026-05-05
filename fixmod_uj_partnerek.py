from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtGui import QColor
import pandas as pd
from fixmod_konfig import szuper_tisztito, megjelenitesre_vago, suly_szamolo

def betoltes_es_feldolgozas(parent):
    if not hasattr(parent, 'df_uj_raw') or not hasattr(parent, 'df_regi_raw'): return
    parent.right_table.setUpdatesEnabled(False)
    parent.right_table.setRowCount(0)
    parent.right_table.setColumnCount(6)
    parent.right_table.setHorizontalHeaderLabels(["Név (Régi)", "Cím (Új)", "Tétel", "Darab", "Súly", "Státusz"])
    
    # Régi partnerek szótára a 15 karakteres kulccsal
    regi_szotar = {} 
    c_r = parent.r_cols
    for _, row in parent.df_regi_raw.iterrows():
        v_n = megjelenitesre_vago(str(row.iloc[c_r['p']]))
        regi_szotar[szuper_tisztito(v_n)] = v_n

    # Új adatok csoportosítása a 15 karakteres kulccsal
    c_u = parent.u_cols
    uj_adatok = {} 
    for _, row in parent.df_uj_raw.iterrows():
        v_n = megjelenitesre_vago(str(row.iloc[c_u['c']]))
        kl = szuper_tisztito(v_n)
        if not kl: continue
        
        if kl not in uj_adatok:
            uj_adatok[kl] = {'v_n': v_n, 'db': 0, 'suly': 0, 't': "HSO"}
        
        t_szov = str(row.iloc[c_u['f']]) if len(row) > c_u['f'] else "HSO"
        t_nev, sl = suly_szamolo(t_szov)
        uj_adatok[kl]['db'] += 1
        uj_adatok[kl]['suly'] += sl
        uj_adatok[kl]['t'] = t_nev

    parent.right_table.setRowCount(len(uj_adatok))
    for i, (kl, ad) in enumerate(uj_adatok.items()):
        is_regi = kl in regi_szotar
        r_nev = regi_szotar[kl] if is_regi else "- ÚJ HELYSZÍN -"
        
        vals = [r_nev, ad['v_n'], ad['t'], f"{ad['db']} DB", f"{ad['suly']} kg", "MÁR PARTNER" if is_regi else "ÚJ"]
        for col, val in enumerate(vals):
            item = QTableWidgetItem(str(val))
            if is_regi: item.setBackground(QColor("#fff59d"))
            parent.right_table.setItem(i, col, item)
            
    parent.right_table.resizeColumnsToContents()
    parent.right_table.setUpdatesEnabled(True)
