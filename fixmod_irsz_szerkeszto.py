import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QLabel, QHeaderView)
from PyQt6.QtCore import Qt

class IrszSzerkeszto(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Irányítószám Tartományok Szerkesztése")
        self.setMinimumSize(600, 400)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        label = QLabel("<b>Túra hozzárendelési szabályok (IRSZ tartományok)</b>")
        layout.addWidget(label)

        # Táblázat létrehozása: Tól | Ig | Túra neve
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["IRSZ Tól", "IRSZ Ig", "Túra Neve"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # Gombok
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("+ Új sor")
        self.btn_add.setFixedHeight(35)
        self.btn_add.clicked.connect(self.add_row)
        
        self.btn_save = QPushButton("💾 Szabályok Mentése")
        self.btn_save.setFixedHeight(35)
        self.btn_save.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        
        btn_layout.addWidget(self.btn_add)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(""))
        self.table.setItem(row, 1, QTableWidgetItem(""))
        self.table.setItem(row, 2, QTableWidgetItem("Új Túra"))

# --- EZ A FÜGGVÉNY HIÁNYZOTT VAGY EZT KERESI A FŐPROGRAM ---
def indit_irsz_szerkeszto(parent):
    dialog = IrszSzerkeszto(parent)
    dialog.exec()
