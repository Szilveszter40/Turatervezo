import os
from datetime import datetime
from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt6.QtGui import QTextDocument, QPageLayout, QPageSize
from PyQt6.QtCore import QMarginsF, Qt
from PyQt6.QtWidgets import QMessageBox, QTableWidget, QTreeWidget

def modul_nyomtatas(aktualis_modul_widget):
    """
    Kiválasztja a modul aktív adatforrását, felépíti a kompakt HTML-t 
    fekvő formátumban, oldaltörésekkel, majd megnyitja a nyomtatási képet.
    """
    tree_widget = None

    # 1. Aktív fa (QTreeWidget) kiválasztása
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

    # 2. Dinamikus címkezelés
    ablak_cim = aktualis_modul_widget.windowTitle()
    ablak_cim = ablak_cim.upper() if ablak_cim else "KIMUTATÁS"

    # 3. HTML alapstruktúra kompakt stílusokkal (Kisebb betűk, fekvő elrendezés optimalizálás)
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #333; margin: 0; padding: 0; }}
            
            /* Oldaltörés szabály: minden ezzel a osztállyal rendelkező elem ÚJ OLDALRA kerül */
            .oldal-tores {{ page-break-before: always; }}
            /* Az első oldalon ne legyen felesleges üres lap */
            .oldal-tores:first-of-type {{ page-break-before: avoid; }}
            
            table {{ border-collapse: collapse; width: 100%; margin-top: 10px; margin-bottom: 20px; }}
            th, td {{ border: 1px solid #b2bec3; padding: 4px 6px; text-align: left; font-size: 8pt; line-height: 1.2; }}
            th {{ background-color: #34495e; color: white; font-weight: bold; font-size: 8.5pt; }}
            .szulo-sor {{ background-color: #dfe6e9; font-weight: bold; color: #2c3e50; font-size: 9pt; }}
            .gyermek-sor {{ padding-left: 20px; color: #444; }}
            h1 {{ text-align: center; color: #34495e; letter-spacing: 2px; font-size: 14pt; margin-bottom: 5px; margin-top: 10px; }}
            h2 {{ color: #2c3e50; font-size: 11pt; margin-top: 5px; margin-bottom: 5px; border-bottom: 2px solid #34495e; padding-bottom: 3px; }}
            .footer {{ text-align: right; font-size: 7.5pt; color: #7f8c8d; margin-top: 15px; border-top: 1px solid #ccc; padding-top: 3px; }}
        </style>
    </head>
    <body>
    """

    # --- A: HA TÁBLÁZATOT NYOMTATUNK ---
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

    # --- B: HA FA STRUKTÚRÁT NYOMTATUNK (TÚRÁK ÉS PARTNEREK) ---
    elif tree_widget:
        # Minden szülőt (túrát) külön blokként kezelünk, hogy az oldaltörést rá tudjuk tenni
        for i in range(tree_widget.topLevelItemCount()):
            parent_item = tree_widget.topLevelItem(i)
            
            # Konténer az oldaltörésnek
            html += "<div class='oldal-tores'>"
            html += f"<h1>{ablak_cim}</h1>"
            html += f"<h2>Túra: {parent_item.text(0)} {parent_item.text(1)} {parent_item.text(2)}</h2>"
            
            html += "<table><thead><tr>"
            # Fejlécek kiírása a fának megfelelően
            for j in range(tree_widget.columnCount()):
                label = tree_widget.headerItem().text(j)
                html += f"<th>{label}</th>"
            html += "</tr></thead><tbody>"

            # Csak a hozzá tartozó gyermekeket (partnereket) tesszük a táblázatba
            if parent_item.childCount() == 0:
                html += f"<tr><td colspan='{tree_widget.columnCount()}' style='text-align:center; font-style:italic; color:#7f8c8d;'>Nincsenek partnerek ezen a túrán.</td></tr>"
            else:
                for k in range(parent_item.childCount()):
                    child_item = parent_item.child(k)
                    html += "<tr>"
                    for j in range(tree_widget.columnCount()):
                        indent_style = " class='gyermek-sor'" if j == 0 else ""
                        html += f"<td{indent_style}>{child_item.text(j)}</td>"
                    html += "</tr>"

            aktualis_datum = datetime.now().strftime("%Y.%m.%d. %H:%M")
            html += "</tbody></table>"
            html += f"<div class='footer'>Generálva: {aktualis_datum} | Oldal: {i+1}</div>"
            html += "</div>" # .oldal-tores vége

    html += "</body></html>"

    # 4. Nyomtatás előkészítése TEXT_DOCUMENT-be
    document = QTextDocument()
    document.setHtml(html)

    # 5. Printer beállítása FEKVŐ TÁJOLÁSRA (Orientation.Landscape)
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    layout = QPageLayout(
        QPageSize(QPageSize.PageSizeId.A4), 
        QPageLayout.Orientation.Landscape,  # <--- FEKVŐ MÓD BEÁLLÍTÁSA
        QMarginsF(12, 12, 12, 12)           # Kisebb margók (12mm), hogy még több adat férjen el
    )
    printer.setPageLayout(layout)

    # 6. Preview ablak megnyitása
    preview = QPrintPreviewDialog(printer, aktualis_modul_widget)
    preview.paintRequested.connect(lambda p: document.print(p))
    preview.resize(1200, 850) # Szélesebb ablak a fekvő nézet miatt
    preview.exec()
