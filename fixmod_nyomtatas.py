import os
import re
from datetime import datetime
from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt6.QtGui import QTextDocument, QPageLayout, QPageSize
from PyQt6.QtCore import QMarginsF, Qt
from PyQt6.QtWidgets import QMessageBox, QTableWidget, QTreeWidget

def szamot_kivon(szoveg):
    """Segédfüggvény: kiszűri a számokat a szövegből (pl. '120 kg' -> 120.0 vagy '5 db' -> 5)"""
    if not szoveg:
        return 0.0
    # Csak a számokat, pontot és vesszőt tartja meg
    tisztitott = re.sub(r'[^\d.,]', '', szoveg).replace(',', '.')
    try:
        return float(tisztitott) if '.' in tisztitott else int(tisztitott)
    except ValueError:
        return 0.0

def modul_nyomtatas(aktualis_modul_widget):
    """
    Kompakt HTML-t generál egyedi oszlopszélességekkel és 
    automatikus összegzéssel a táblázat alján.
    """
    tree_widget = None

    # 1. Aktív fa kiválasztása
    if hasattr(aktualis_modul_widget, "tree_bal") and hasattr(aktualis_modul_widget, "tree_jobb"):
        if aktualis_modul_widget.tree_jobb.topLevelItemCount() > 0 and aktualis_modul_widget.tree_jobb.hasFocus():
            tree_widget = aktualis_modul_widget.tree_jobb
        elif aktualis_modul_widget.tree_bal.topLevelItemCount() > 0:
            tree_widget = aktualis_modul_widget.tree_bal
        else:
            tree_widget = aktualis_modul_widget.tree_jobb

    if not tree_widget:
        tree_widget = aktualis_modul_widget.findChild(QTreeWidget)
    
    table_widget = aktualis_modul_widget.findChild(QTableWidget)
    
    if not table_widget and (not tree_widget or tree_widget.topLevelItemCount() == 0):
        QMessageBox.warning(aktualis_modul_widget, "Nyomtatás", "Nincs megjelenített adat a táblázatban vagy a listában!")
        return

    ablak_cim = aktualis_modul_widget.windowTitle()
    ablak_cim = ablak_cim.upper() if ablak_cim else "KIMUTATÁS"

    # 3. HTML és CSS stílusok (Új: összesítő sor dizájn)
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #333; margin: 0; padding: 0; }}
            .oldal-tores {{ page-break-before: always; }}
            .oldal-tores:first-of-type {{ page-break-before: avoid; }}
            
            table {{ border-collapse: collapse; width: 100%; margin-top: 10px; margin-bottom: 10px; }}
            th, td {{ border: 1px solid #b2bec3; padding: 5px 8px; text-align: left; font-size: 8.5pt; line-height: 1.2; }}
            th {{ background-color: #34495e; color: white; font-weight: bold; font-size: 9pt; }}
            
            /* Jobbra igazítás a számokhoz */
            .szam-oszlop {{ text-align: right; }}
            
            /* Összegző sor egyedi stílusa */
            .osszesito-sor {{ background-color: #eaeded; font-weight: bold; border-top: 2px solid #2c3e50; }}
            .osszesito-sor td {{ font-size: 9pt; color: #2c3e50; }}
            
            .gyermek-sor {{ padding-left: 20px; color: #444; }}
            h1 {{ text-align: center; color: #34495e; letter-spacing: 2px; font-size: 14pt; margin-bottom: 5px; margin-top: 10px; }}
            h2 {{ color: #2c3e50; font-size: 11pt; margin-top: 5px; margin-bottom: 5px; border-bottom: 2px solid #34495e; padding-bottom: 3px; }}
            .footer {{ text-align: right; font-size: 7.5pt; color: #7f8c8d; margin-top: 10px; border-top: 1px solid #ccc; padding-top: 3px; }}
        </style>
    </head>
    <body>
    """

    # --- A: TÁBLÁZAT NYOMTATÁSA ---
    if table_widget:
        html += f"<h1>{ablak_cim}</h1><table><thead><tr>"
        for j in range(table_widget.columnCount()):
            header_item = table_widget.horizontalHeaderItem(j)
            label = header_item.text() if header_item else f"{j+1}. oszlop"
            html += f"<th>{label}</th>"
        html += "</tr></thead><tbody>"

        for i in range(table_widget.rowCount()):
            html += "<tr>"
            for j in range(table_widget.columnCount()):
                item = table_widget.item(i, j)
                html += f"<td>{item.text() if item else ''}</td>"
            html += "</tr>"
        
        aktualis_datum = datetime.now().strftime("%Y.%m.%d. %H:%M")
        html += f"</tbody></table><div class='footer'>Generálva: {aktualis_datum}</div>"

    # --- B: FA STRUKTÚRA NYOMTATÁSA (EGYEDI SZÉLESSÉG ÉS ÖSSZEGZÉS) ---
    elif tree_widget:
        for i in range(tree_widget.topLevelItemCount()):
            parent_item = tree_widget.topLevelItem(i)
            
            # Számlálók az összegzéshez
            ossz_db = 0
            ossz_suly = 0.0
            
            html += "<div class='oldal-tores'>"
            html += f"<h1>{ablak_cim}</h1>"
            html += f"<h2>Túra: {parent_item.text(0)} {parent_item.text(1)} {parent_item.text(2)}</h2>"
            
            html += "<table><thead><tr>"
            
            # Egyedi szélességek beállítása (%-ban kifejezve a fekvő laphoz)
            # Oszlop 0 (Név): 60% | Oszlop 1 (Db): 20% | Oszlop 2 (Súly): 20%
            szelessegek = ["width='60%'", "width='20%' class='szam-oszlop'", "width='20%' class='szam-oszlop'"]
            
            for j in range(tree_widget.columnCount()):
                label = tree_widget.headerItem().text(j)
                width_attr = szelessegek[j] if j < len(szelessegek) else ""
                html += f"<th {width_attr}>{label}</th>"
            html += "</tr></thead><tbody>"

            if parent_item.childCount() == 0:
                html += f"<tr><td colspan='{tree_widget.columnCount()}' style='text-align:center; font-style:italic; color:#7f8c8d;'>Nincsenek partnerek ezen a túrán.</td></tr>"
            else:
                for k in range(parent_item.childCount()):
                    child_item = parent_item.child(k)
                    
                    # Értékek beolvasása és matematikai összegzése
                    db_ertek = child_item.text(1)
                    suly_ertek = child_item.text(2)
                    
                    ossz_db += szamot_kivon(db_ertek)
                    ossz_suly += szamot_kivon(suly_ertek)
                    
                    html += "<tr>"
                    # Első oszlop: Partner neve (behúzással)
                    html += f"<td class='gyermek-sor'>{child_item.text(0)}</td>"
                    # Második oszlop: Intenzitás / Db (jobbra igazítva)
                    html += f"<td class='szam-oszlop'>{db_ertek}</td>"
                    # Harmadik oszlop: Súly (jobbra igazítva)
                    html += f"<td class='szam-oszlop'>{suly_ertek}</td>"
                    html += "</tr>"

                # ÖSSZEGZŐ SOR HOZZÁADÁSA A TÁBLÁZAT ALJÁRA
                # Ha az összeg egész szám, tizedesjegy nélkül jelenítjük meg (.0 elhagyása)
                suly_szoveg = f"{int(ossz_suly) if ossz_suly.is_integer() else round(ossz_suly, 2)} kg"
                db_szoveg = f"{int(ossz_db)} db"

                html += "<tr class='osszesito-sor'>"
                html += "<td>ÖSSZESEN TÚRÁRA:</td>"
                html += f"<td class='szam-oszlop'>{db_szoveg}</td>"
                html += f"<td class='szam-oszlop'>{suly_szoveg}</td>"
                html += "</tr>"

            aktualis_datum = datetime.now().strftime("%Y.%m.%d. %H:%M")
            html += "</tbody></table>"
            html += f"<div class='footer'>Generálva: {aktualis_datum} | Oldal: {i+1}</div>"
            html += "</div>"

    html += "</body></html>"

    # 4. Renderelés és nyomtatási kép indítása
    document = QTextDocument()
    document.setHtml(html)

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    layout = QPageLayout(QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Landscape, QMarginsF(12, 12, 12, 12))
    printer.setPageLayout(layout)

    preview = QPrintPreviewDialog(printer, aktualis_modul_widget)
    preview.paintRequested.connect(lambda p: document.print(p))
    preview.resize(1200, 850)
    preview.exec()
