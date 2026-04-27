import json
import os
import pandas as pd
from PyQt6.QtWidgets import (QPushButton, QDialog, QVBoxLayout, QHBoxLayout, 
                             QLabel, QMessageBox, QLineEdit, QComboBox, 
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QTreeWidgetItem, QListWidget, QFrame, QTabWidget, QWidget, QFileDialog)
from PyQt6.QtCore import Qt, QTimer

class ModulInit:
    def __init__(self, main_app):
        self.main = main_app
        self.mappa = os.path.dirname(os.path.abspath(__file__))
        
        # Elérési utak
        self.adat_fajl = os.path.join(self.mappa, "tervezo_partnerek.json")
        self.tura_adatok_fajl = os.path.join(self.mappa, "tervezo_turak_mentese.json")
        # A főprogram Turanevek.txt fájlja (feltételezve, hogy a főkönyvtárban van)
        self.turanevek_txt = os.path.join(os.getcwd(), "Turanevek.txt")
        
        self.betolt_adatok()
        QTimer.singleShot(800, self.init_gomb)

    def betolt_adatok(self):
        # Partnerek betöltése
        try:
            if os.path.exists(self.adat_fajl):
                with open(self.adat_fajl, "r", encoding="utf-8") as f: self.partnerek = json.load(f)
            else: self.partnerek = []
        except: self.partnerek = []
        
        # Túrákhoz rendelt partnerek betöltése (összeosztás mentése)
        try:
            if os.path.exists(self.tura_adatok_fajl):
                with open(self.tura_adatok_fajl, "r", encoding="utf-8") as f: self.tura_kapcsolatok = json.load(f)
            else: self.tura_kapcsolatok = {}
        except: self.tura_kapcsolatok = {}

    def get_turanevek_list(self):
        """Beolvassa a neveket a Turanevek.txt fájlból"""
        if os.path.exists(self.turanevek_txt):
            try:
                with open(self.turanevek_txt, "r", encoding="utf-8") as f:
                    return [line.strip() for line in f if line.strip()]
            except:
                return ["Hiba a beolvasáskor"]
        return ["Turanevek.txt nem található"]

    def mentes_adatok(self):
        with open(self.adat_fajl, "w", encoding="utf-8") as f: 
            json.dump(self.partnerek, f, indent=4)
        with open(self.tura_adatok_fajl, "w", encoding="utf-8") as f: 
            json.dump(self.tura_kapcsolatok, f, indent=4)

    def init_gomb(self):
        if hasattr(self.main, 'tervezo_btn_obj'): return
        self.main.tervezo_btn_obj = QPushButton("🏗️ TERVEZŐ")
        self.main.tervezo_btn_obj.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold; padding: 6px; border-radius: 4px;")
        self.main.tervezo_btn_obj.clicked.connect(self.megjelenites)
        if hasattr(self.main, 'left_tree'):
            # Elhelyezés a Statisztika gomb alá
            self.main.left_tree.parent().layout().insertWidget(2, self.main.tervezo_btn_obj)

    def megjelenites(self):
        self.dialog = QDialog(self.main)
        self.dialog.setWindowTitle("Tervező - Partner-Túra Összeosztás")
        self.dialog.setMinimumSize(1100, 750)
        layout = QVBoxLayout(self.dialog)
        tabs = QTabWidget()
        
        # --- 1. TAB: PARTNER IMPORT ---
        tab1 = QWidget(); l1 = QVBoxLayout(tab1)
        import_btn = QPushButton("📂 Új Partnerbázis Importálása (Excel)")
        import_btn.setStyleSheet("background-color: #34495e; color: white; padding: 10px; font-weight: bold;")
        import_btn.clicked.connect(self.excel_import)
        l1.addWidget(import_btn)

        self.tabla_p = QTableWidget(0, 4)
        self.tabla_p.setHorizontalHeaderLabels(["Név", "Város/Cím", "Típus", "Súly (kg)"])
        self.tabla_p.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        l1.addWidget(self.tabla_p)
        
        # --- 2. TAB: ÖSSZEOSZTÁS ---
        tab2 = QWidget(); l2 = QHBoxLayout(tab2)
        
        # Bal: Új partnerek
        p_vaz = QVBoxLayout()
        p_vaz.addWidget(QLabel("<b>Választható Partnerek:</b>"))
        self.p_selector = QListWidget()
        p_vaz.addWidget(self.p_selector)
        l2.addLayout(p_vaz, 1)

        # Közép: Gombok
        m_vaz = QVBoxLayout()
        m_vaz.addStretch()
        add_btn = QPushButton("👉"); add_btn.setFixedSize(40, 40)
        add_btn.clicked.connect(self.partner_turahoz_rendel)
        del_btn = QPushButton("🗑️"); del_btn.setFixedSize(40, 40)
        del_btn.clicked.connect(self.partner_eltavolit)
        m_vaz.addWidget(add_btn); m_vaz.addWidget(del_btn)
        m_vaz.addStretch()
        l2.addLayout(m_vaz)

        # Jobb: Cél Túrák (Turanevek.txt-ből)
        t_vaz = QVBoxLayout()
        t_vaz.addWidget(QLabel("<b>Cél Túrák (Turanevek.txt):</b>"))
        self.t_selector = QComboBox()
        # Feltöltés a TXT-ből
        self.t_selector.addItems(self.get_turanevek_list())
        t_vaz.addWidget(self.t_selector)
        
        self.t_tartalom = QListWidget()
        t_vaz.addWidget(self.t_tartalom)
        self.t_selector.currentTextChanged.connect(self.tura_tartalom_mutat)
        l2.addLayout(t_vaz, 1)

        tabs.addTab(tab1, "Adatbázis"); tabs.addTab(tab2, "Túra Összeosztás")
        layout.addWidget(tabs)
        self.frissit_felulet()
        self.dialog.exec()

    def excel_import(self):
        from openpyxl import load_workbook
        fajl, _ = QFileDialog.getOpenFileName(self.dialog, "Excel megnyitása", "", "Excel fájlok (*.xlsx *.xls)")
        if not fajl: return
        
        try:
            wb = load_workbook(fajl, data_only=True)
            ws = wb.active
            volt_uj = 0
            
            # Ugyanaz a ciklus és indexelés, mint a tervezo_stabil.py-ban
            # A főprogramod a 2. sorról indul (row 2), mert az 1. a fejléc
            for row in range(2, ws.max_row + 1):
                # A tervezo_stabil.py logikája szerint:
                # C oszlop (3): Név
                # D oszlop (4): Kirendeltség / Cím
                # I oszlop (9): Súly (például)
                
                nev = str(ws.cell(row=row, column=3).value or "").strip()
                cím = str(ws.cell(row=row, column=4).value or "").strip()
                suly = str(ws.cell(row=row, column=9).value or "0").strip() # Ha nálad máshol van, módosítsd!
                
                if nev and nev != "None":
                    uj = {
                        "nev": nev,
                        "cim": cím,
                        "tipus": "IMPORTÁLT",
                        "suly": suly
                    }
                    
                    # Ellenőrizzük a duplikációt az adatbázisban
                    if not any(p['nev'] == uj['nev'] for p in self.partnerek):
                        self.partnerek.append(uj)
                        volt_uj += 1
            
            if volt_uj > 0:
                self.mentes_adatok()
                self.frissit_felulet()
                QMessageBox.information(self.dialog, "Siker", f"{volt_uj} új partner sikeresen betöltve!")
            else:
                QMessageBox.warning(self.dialog, "Figyelem", "Nem találtam új partnert a C oszlopban (3. oszlop).")
                    
        except Exception as e:
            QMessageBox.critical(self.dialog, "Import hiba", f"Hiba az openpyxl beolvasásakor: {str(e)}")

    def frissit_felulet(self):
        self.tabla_p.setRowCount(0); self.p_selector.clear()
        for i, p in enumerate(self.partnerek):
            self.tabla_p.insertRow(i)
            self.tabla_p.setItem(i, 0, QTableWidgetItem(p['nev']))
            self.tabla_p.setItem(i, 1, QTableWidgetItem(p['cim']))
            self.tabla_p.setItem(i, 2, QTableWidgetItem(p['tipus']))
            self.tabla_p.setItem(i, 3, QTableWidgetItem(str(p['suly'])))
            self.p_selector.addItem(p['nev'])
        self.tura_tartalom_mutat(self.t_selector.currentText())

    def tura_tartalom_mutat(self, t_nev):
        self.t_tartalom.clear()
        if t_nev in self.tura_kapcsolatok:
            self.t_tartalom.addItems(self.tura_kapcsolatok[t_nev])

    def partner_turahoz_rendel(self):
        p_item = self.p_selector.currentItem()
        t_nev = self.t_selector.currentText()
        if not p_item or not t_nev: return
        
        if t_nev not in self.tura_kapcsolatok: self.tura_kapcsolatok[t_nev] = []
        if p_item.text() not in self.tura_kapcsolatok[t_nev]:
            self.tura_kapcsolatok[t_nev].append(p_item.text())
            self.mentes_adatok(); self.tura_tartalom_mutat(t_nev)

    def partner_eltavolit(self):
        p_item = self.t_tartalom.currentItem()
        t_nev = self.t_selector.currentText()
        if p_item and t_nev in self.tura_kapcsolatok:
            self.tura_kapcsolatok[t_nev].remove(p_item.text())
            self.mentes_adatok(); self.tura_tartalom_mutat(t_nev)
