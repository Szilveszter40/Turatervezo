import pandas as pd
import re
from PyQt6.QtWidgets import QFileDialog, QTableWidgetItem, QMessageBox, QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

# Importáljuk a vágó funkciót az adatkezelésből a konzisztencia miatt
import fixmod_adatkezeles

def betoltes_es_feldolgozas(parent):
    """
    Betölti az új partnereket, összevonja őket cím alapján, 
    és párosítja a régi nevekkel.
    """
    path, _ = QFileDialog.getOpenFileName(parent, "Új partnerek betöltése", "", "Excel (*.xlsx)")
    if not path:
        return

    try:
        # Beolvasás
        df_uj = pd.read_excel(path)
        
        # C oszlop (index 2) a cím - ezt használjuk kulcsnak
        # A beolvasáskor kényszerítjük a string típust a hibák ellen
        df_uj['CIM_NYERS'] = df_uj.iloc[:, 2].fillna("ISMERETLEN CÍM").astype(str)
        
        parent.right_table.setUpdatesEnabled(False)
        parent.right_table.clear()
        
        # Oszlopok: Név (Régi), Cím (Új), Tétel, Darab, Súly, Státusz
        parent.right_table.setColumnCount(6)
        parent.right_table.setHorizontalHeaderLabels([
            "Név (Régi adatbázis)", "Cím (Új táblázat)", 
            "Tétel", "Darabszám", "Összsúly", "Státusz"
        ])

        # Összesítés cím alapján (ha egy cím többször szerepel, összeadjuk)
        grouped = df_uj.groupby('CIM_NYERS')
        parent.right_table.setRowCount(len(grouped))

        # Adatok lekérése a parent-től (amit a régi partnerek betöltésekor mentettünk el)
        # Ha a régi partnerek nincsenek betöltve, üres értékekkel dolgozunk
        regi_kapcsok = getattr(parent, 'regi_kapcsok', set())
        regi_nev_tar = getattr(parent, 'regi_nev_tar', {})

        for i, (cim, data) in enumerate(grouped):
            darabszam = len(data) # Ahány sor, annyi darab HSO
            osszsuly = darabszam * 60
            
            # A párosításhoz ugyanazt a tisztító kulcsot használjuk, mint a régieknél
            tisztitott_kulcs = fixmod_adatkezeles.szuper_tisztito_kulcs(cim)
            
            # Megnézzük, megvan-e a régiek között
            regi_nev = regi_nev_tar.get(tisztitott_kulcs, "- ÚJ HELYSZÍN -")
            
            # Táblázat feltöltése
            parent.right_table.setItem(i, 0, QTableWidgetItem(str(regi_nev)))
            parent.right_table.setItem(i, 1, QTableWidgetItem(str(cim)))
            parent.right_table.setItem(i, 2, QTableWidgetItem("HSO"))
            parent.right_table.setItem(i, 3, QTableWidgetItem(f"{darabszam} DB"))
            parent.right_table.setItem(i, 4, QTableWidgetItem(f"{osszsuly} kg"))
            
            # Státusz és színezés
            status = "ÚJ"
            hatterszin = None
            
            if tisztitott_kulcs in regi_kapcsok:
                status = "MÁR PARTNER"
                hatterszin = QColor("#fff59d") # Halványsárga
            
            status_item = QTableWidgetItem(status)
            if hatterszin:
                status_item.setBackground(hatterszin)
                # Az egész sort besárgítjuk
                for j in range(5):
                    item = parent.right_table.item(i, j)
                    if not item: # Biztonsági mentés ha üres a cella
                        item = QTableWidgetItem("")
                        parent.right_table.setItem(i, j, item)
                    item.setBackground(hatterszin)
            
            parent.right_table.setItem(i, 5, status_item)

        parent.right_table.resizeColumnsToContents()
        parent.right_table.setUpdatesEnabled(True)
        parent.status_label.setText(f"✓ {len(grouped)} új helyszín feldolgozva és párosítva.")

    except Exception as e:
        parent.right_table.setUpdatesEnabled(True)
        QMessageBox.critical(parent, "Hiba az Új Partnereknél", f"Részletek: {str(e)}")
