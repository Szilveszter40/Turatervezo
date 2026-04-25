import os
import json
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QHeaderView, QMessageBox)
from PyQt6.QtCore import Qt

class TablazatosSzerkeszto(QDialog):
    def __init__(self, cim, fajl_utvonal, main_app, ket_oszlopos=False):
        super().__init__(main_app)
        self.main = main_app
        self.fajl_utvonal = fajl_utvonal
        self.ket_oszlopos = ket_oszlopos
        self.tipus_adat_utvonal = fajl_utvonal.replace(".txt", "_tipusok.json")
        self.setWindowTitle(f"{cim} adatbázis karbantartása")
        self.setMinimumSize(500, 550)
        
        layout = QVBoxLayout(self)
        self.table = QTableWidget()
        
        if self.ket_oszlopos:
            self.table.setColumnCount(2)
            self.table.setHorizontalHeaderLabels(["Rendszám", "Autó típusa (csak info)"])
        else:
            self.table.setColumnCount(1)
            self.table.setHorizontalHeaderLabels([cim])
            
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        
        self.adatok_betoltese()
        layout.addWidget(self.table)

        gomb_layout = QHBoxLayout()
        uj_gomb = QPushButton("+ ÚJ SOR")
        uj_gomb.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; height: 35px;")
        uj_gomb.clicked.connect(self.sor_hozzaadas)
        
        del_gomb = QPushButton("- TÖRLÉS")
        del_gomb.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold; height: 35px;")
        del_gomb.clicked.connect(self.sor_torlese)
        
        mentes_gomb = QPushButton("MENTÉS ÉS FRISSÍTÉS")
        mentes_gomb.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; height: 35px;")
        mentes_gomb.clicked.connect(self.mentes)

        gomb_layout.addWidget(uj_gomb)
        gomb_layout.addWidget(del_gomb)
        gomb_layout.addStretch()
        gomb_layout.addWidget(mentes_gomb)
        layout.addLayout(gomb_layout)

    def adatok_betoltese(self):
        rendszamok = []
        if os.path.exists(self.fajl_utvonal):
            with open(self.fajl_utvonal, "r", encoding="utf-8") as f:
                rendszamok = [l.strip() for l in f if l.strip()]
        
        tipusok = {}
        if self.ket_oszlopos and os.path.exists(self.tipus_adat_utvonal):
            with open(self.tipus_adat_utvonal, "r", encoding="utf-8") as f:
                tipusok = json.load(f)
        
        self.table.setRowCount(len(rendszamok))
        for i, rsz in enumerate(rendszamok):
            self.table.setItem(i, 0, QTableWidgetItem(rsz))
            if self.ket_oszlopos:
                tipus = tipusok.get(rsz, "")
                self.table.setItem(i, 1, QTableWidgetItem(tipus))

    def sor_hozzaadas(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(""))
        if self.ket_oszlopos:
            self.table.setItem(row, 1, QTableWidgetItem(""))
        self.table.scrollToBottom()

    def sor_torlese(self):
        current = self.table.currentRow()
        if current >= 0:
            self.table.removeRow(current)

    def mentes(self):
        uj_rendszamok = []
        tipus_map = {}
        
        for i in range(self.table.rowCount()):
            rsz_item = self.table.item(i, 0)
            rsz = rsz_item.text().strip() if rsz_item else ""
            
            if rsz:
                uj_rendszamok.append(rsz)
                if self.ket_oszlopos:
                    tip_item = self.table.item(i, 1)
                    tipus_map[rsz] = tip_item.text().strip() if tip_item else ""
        
        uj_rendszamok.sort()
        try:
            # Csak a rendszámokat mentjük a TXT-be
            with open(self.fajl_utvonal, "w", encoding="utf-8") as f:
                f.write("\n".join(uj_rendszamok))
            
            # A típusokat elmentjük a háttérben egy JSON fájlba
            if self.ket_oszlopos:
                with open(self.tipus_adat_utvonal, "w", encoding="utf-8") as f:
                    json.dump(tipus_map, f, ensure_ascii=False, indent=4)
            
            self.main.frissit_cb()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Hiba", f"Mentési hiba: {e}")

class ModulInit:
    def __init__(self, main_app):
        self.main = main_app
        self.atiras()

    def atiras(self):
        for action in self.main.mod_menu.actions():
            if "Rendszámok" in action.text():
                try: action.triggered.disconnect()
                except: pass
                action.triggered.connect(lambda: TablazatosSzerkeszto("Gépjármű", self.main.autok_p, self.main, ket_oszlopos=True).exec())
            elif "Sofőrök" in action.text():
                try: action.triggered.disconnect()
                except: pass
                action.triggered.connect(lambda: TablazatosSzerkeszto("Sofőr", self.main.sofor_p, self.main, ket_oszlopos=False).exec())
