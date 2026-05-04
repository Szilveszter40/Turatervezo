import os
import subprocess
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtGui import QTextDocument
from PyQt6.QtWidgets import QMessageBox

def elonezet_es_nyomtatas(table_widget):
    """
    PDF-et generál a táblázatból és megnyitja előnézetre.
    """
    if table_widget.rowCount() == 0:
        QMessageBox.warning(None, "Nyomtatás", "Nincs adat a táblázatban!")
        return

    # HTML dokumentum felépítése (stílusokkal)
    html = """
    <html>
    <head>
        <style>
            body { font-family: 'Segoe UI', Arial, sans-serif; }
            table { border-collapse: collapse; width: 100%; margin-top: 20px; }
            th, td { border: 1px solid #333; padding: 10px; text-align: left; font-size: 10pt; }
            th { background-color: #2c3e50; color: white; }
            h1 { text-align: center; color: #2c3e50; }
            .footer { text-align: right; font-size: 8pt; color: #7f8c8d; margin-top: 10px; }
        </style>
    </head>
    <body>
        <h1>TÚRA TERVEZET</h1>
        <table>
            <thead><tr>
    """

    # Fejlécek
    for j in range(table_widget.columnCount()):
        label = table_widget.horizontalHeaderItem(j).text()
        html += f"<th>{label}</th>"
    html += "</tr></thead><tbody>"

    # Adatok
    for i in range(table_widget.rowCount()):
        html += "<tr>"
        for j in range(table_widget.columnCount()):
            item = table_widget.item(i, j)
            html += f"<td>{item.text() if item else ''}</td>"
        html += "</tr>"

    html += "</tbody></table>"
    html += f"<div class='footer'>Generálva: {os.popen('date /t').read()}</div>"
    html += "</body></html>"

    # PDF generálása ideiglenes fájlba
    document = QTextDocument()
    document.setHtml(html)

    file_path = os.path.join(os.getcwd(), "tura_tervezet_elonezet.pdf")
    
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(file_path)
    printer.setPageMargins(QPrinter.pageLayout().margins())

    document.print_(printer)

    # PDF megnyitása az alapértelmezett nézegetővel
    if os.path.exists(file_path):
        os.startfile(file_path)
    else:
        QMessageBox.critical(None, "Hiba", "Nem sikerült létrehozni a PDF fájlt.")

