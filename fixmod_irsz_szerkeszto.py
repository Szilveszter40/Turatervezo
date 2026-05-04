import pandas as pd
import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QLabel, QFileDialog, 
                             QTabWidget, QMessageBox, QComboBox, QHeaderView, QInputDialog)
from PyQt6.QtCore import Qt

class AthelyezoAblak(QDialog):
    def __init__(self, excel_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Irányítószám Szerkesztő és Ellenőrző")
        self.setMinimumSize(1100, 700)
        self.excel_data = excel_data
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        h_layout = QHBoxLayout()

        # --- BAL OLDAL ---
        v_bal = QVBoxLayout()
        self.combo_bal = QComboBox()
        self.combo_bal.addItems(self.excel_data.keys())
        self.combo_bal.currentTextChanged.connect(lambda: self.frissit_tablat('bal'))
        self.table_bal = QTableWidget()
        v_bal.addWidget(QLabel("<b>FORRÁS AUTÓ:</b>"))
        v_bal.addWidget(self.combo_bal)
        v_bal.addWidget(self.table_bal)

        # --- KÖZÉPSŐ GOMBOK ---
        v_kozep = QVBoxLayout()
        v_kozep.addStretch()
        
        self.btn_atrak = QPushButton("ÁTHELYEZÉS\n➡")
        self.btn_atrak.setFixedSize(120, 100)
        self.btn_atrak.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; border-radius: 10px;")
        self.btn_atrak.clicked.connect(self.atrak_muvelet)
        v_kozep.addWidget(self.btn_atrak)

        self.btn_torol = QPushButton("CELLA\nTÖRLÉSE\n🗑️")
        self.btn_torol.setFixedSize(120, 100)
        self.btn_torol.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; border-radius: 10px; margin-top: 20px;")
        self.btn_torol.clicked.connect(self.cella_torles)
        v_kozep.addWidget(self.btn_torol)
        
        v_kozep.addStretch()

        # --- JOBB OLDAL ---
        v_jobb = QVBoxLayout()
        self.combo_jobb = QComboBox()
        self.combo_jobb.addItems(self.excel_data.keys())
        if self.combo_jobb.count() > 1: self.combo_jobb.setCurrentIndex(1)
        self.combo_jobb.currentTextChanged.connect(lambda: self.frissit_tablat('jobb'))
        self.table_jobb = QTableWidget()
        v_jobb.addWidget(QLabel("<b>CÉL AUTÓ:</b>"))
        v_jobb.addWidget(self.combo_jobb)
        v_jobb.addWidget(self.table_jobb)

        h_layout.addLayout(v_bal)
        h_layout.addLayout(v_kozep)
        h_layout.addLayout(v_jobb)
        layout.addLayout(h_layout)

        btn_bezar = QPushButton("MÓDOSÍTÁSOK VÉGLEGESÍTÉSE")
        btn_bezar.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; height: 45px;")
        btn_bezar.clicked.connect(self.accept)
        layout.addWidget(btn_bezar)

        self.setLayout(layout)
        self.frissit_tablat('bal')
        self.frissit_tablat('jobb')

    def frissit_tablat(self, oldal):
        combo = self.combo_bal if oldal == 'bal' else self.combo_jobb
        table = self.table_bal if oldal == 'bal' else self.table_jobb
        auto_nev = combo.currentText()
        if auto_nev not in self.excel_data: return
        
        df = self.excel_data[auto_nev]
        table.setRowCount(len(df))
        table.setColumnCount(len(df.columns))
        table.setHorizontalHeaderLabels(df.columns)
        
        for i in range(len(df)):
            for j in range(len(df.columns)):
                val = str(df.iloc[i, j]).replace('.0', '') if pd.notnull(df.iloc[i, j]) else ""
                if val.lower() == 'nan': val = ""
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(i, j, item)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def cella_torles(self):
        for table in [self.table_bal, self.table_jobb]:
            item = table.currentItem()
            if item:
                item.setText("")

    def atrak_muvelet(self):
        item = self.table_bal.currentItem()
        if not item or not item.text().strip():
            QMessageBox.warning(self, "Figyelem", "Nincs kijelölt irányítószám!")
            return

        val = item.text()
        napok = [self.table_jobb.horizontalHeaderItem(c).text() for c in range(self.table_jobb.columnCount())]
        nap, ok = QInputDialog.getItem(self, "Cél nap", f"Melyik napra kerüljön: {val}?", napok, 0, False)
        
        if ok and nap:
            # Duplikáció ellenőrzés
            foglalt = [a for a, d in self.excel_data.items() if nap in d.columns and val in d[nap].values]
            if foglalt:
                q = QMessageBox.question(self, "Figyelem", f"Ez az IRSZ ({val}) már szerepel itt: {', '.join(foglalt)} ezen a napon ({nap}). Folytatja?")
                if q == QMessageBox.StandardButton.No: return

            cel_oszlop = napok.index(nap)
            sor = -1
            for r in range(self.table_jobb.rowCount()):
                c_item = self.table_jobb.item(r, cel_oszlop)
                if not c_item or not c_item.text().strip():
                    sor = r
                    break
            
            if sor == -1:
                sor = self.table_jobb.rowCount()
                self.table_jobb.insertRow(sor)
                for c in range(self.table_jobb.columnCount()): self.table_jobb.setItem(sor, c, QTableWidgetItem(""))

            new_item = QTableWidgetItem(val)
            new_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_jobb.setItem(sor, cel_oszlop, new_item)
            item.setText("")

class IrszSzerkeszto(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Irsz Szerkesztő")
        self.setMinimumSize(1000, 700)
        self.excel_data = {} 
        self.tabs = QTabWidget()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        top = QHBoxLayout()

        btn_load = QPushButton("📂 Excel Import (9 Autó)")
        btn_load.clicked.connect(self.beolvas)
        top.addWidget(btn_load)

        btn_mod = QPushButton("🔄 ÁTHELYEZÉS / MÓDOSÍTÁS")
        btn_mod.setStyleSheet("background-color: #8e44ad; color: white; font-weight: bold;")
        btn_mod.clicked.connect(self.megnyit_athelyezo)
        top.addWidget(btn_mod)

        btn_save = QPushButton("💾 EXCEL MENTÉSE")
        btn_save.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        btn_save.clicked.connect(self.mentes_excelbe)
        top.addWidget(btn_save)

        layout.addLayout(top)
        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def beolvas(self):
        path, _ = QFileDialog.getOpenFileName(self, "Beosztás megnyitása", "", "Excel (*.xlsx)")
        if path:
            self.excel_data = pd.read_excel(path, sheet_name=None, dtype=str)
            self.frissit_tabok()

    def frissit_tabok(self):
        self.tabs.clear()
        for name, df in self.excel_data.items():
            table = QTableWidget(len(df), len(df.columns))
            table.setHorizontalHeaderLabels(df.columns)
            for i in range(len(df)):
                for j in range(len(df.columns)):
                    val = str(df.iloc[i, j]).replace('.0', '') if pd.notnull(df.iloc[i, j]) else ""
                    item = QTableWidgetItem(val if val.lower() != 'nan' else "")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    table.setItem(i, j, item)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self.tabs.addTab(table, name)

    def szinkronizalas(self):
        for i in range(self.tabs.count()):
            name = self.tabs.tabText(i)
            table = self.tabs.widget(i)
            rows = []
            for r in range(table.rowCount()):
                rows.append([table.item(r, c).text() if table.item(r, c) else "" for c in range(table.columnCount())])
            self.excel_data[name] = pd.DataFrame(rows, columns=[table.horizontalHeaderItem(c).text() for c in range(table.columnCount())])

    def megnyit_athelyezo(self):
        if not self.excel_data: return
        self.szinkronizalas()
        if AthelyezoAblak(self.excel_data, self).exec():
            self.frissit_tabok()

    def mentes_excelbe(self):
        self.szinkronizalas()
        path, _ = QFileDialog.getSaveFileName(self, "Mentés", "Módosított_Beosztás.xlsx", "Excel (*.xlsx)")
        if path:
            with pd.ExcelWriter(path) as writer:
                for n, df in self.excel_data.items(): df.to_excel(writer, sheet_name=n, index=False)
            QMessageBox.information(self, "Kész", "Sikeres mentés!")

def indit_irsz_szerkeszto(parent):
    dialog = IrszSzerkeszto(parent)
    dialog.exec()
