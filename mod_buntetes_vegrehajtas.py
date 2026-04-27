import json
import os
from PyQt6.QtWidgets import (QPushButton, QDialog, QVBoxLayout, QHBoxLayout, 
                             QLabel, QMessageBox, QLineEdit, QComboBox, 
                             QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt

class ModulInit:
    def __init__(self, main_app):
        self.main = main_app
        self.adat_fajl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bv_adatbazis.json")
        self.napok = ["Hétfő", "Kedd", "Szerda", "Csütörtök", "Péntek", "Szombat", "Vasárnap"]
        self.betölt_adatok()
        self.init_gomb()

    def betölt_adatok(self):
        if os.path.exists(self.adat_fajl):
            try:
                with open(self.adat_fajl, "r", encoding="utf-8") as f:
                    self.bv_lista = json.load(f)
            except: self.bv_lista = []
        else: self.bv_lista = []

    def mentes_adatok(self):
        with open(self.adat_fajl, "w", encoding="utf-8") as f:
            json.dump(self.bv_lista, f, ensure_ascii=False, indent=4)

    def init_gomb(self):
        if hasattr(self.main, 'bv_btn_obj'): return
        self.main.bv_btn_obj = QPushButton("⚖️ BÜNTETÉS VÉGREHAJTÁS")
        self.main.bv_btn_obj.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold; padding: 6px; border-radius: 4px;")
        self.main.bv_btn_obj.clicked.connect(self.megjelenites)
        if hasattr(self.main, 'left_tree'):
            self.main.left_tree.parent().layout().insertWidget(1, self.main.bv_btn_obj)

    def megjelenites(self):
        self.dialog = QDialog(self.main)
        self.dialog.setWindowTitle("BV Intézmények - Letisztult Nyilvántartás")
        self.dialog.setMinimumSize(1000, 650)
        layout = QVBoxLayout(self.dialog)

        self.tablazat = QTableWidget(0, 6)
        self.tablazat.setHorizontalHeaderLabels(["Intézmény", "Cím", "Típus", "Üres kint", "Elhozandó", "Napok"])
        self.tablazat.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tablazat.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tablazat.itemDoubleClicked.connect(self.adat_betoltese_szerkesztesre)
        layout.addWidget(self.tablazat)
        self.frissit_tablazat()

        # 1. sor: Alapadatok
        l1 = QHBoxLayout()
        self.nev_in = QLineEdit(); self.nev_in.setPlaceholderText("Börtön neve")
        self.cim_in = QLineEdit(); self.cim_in.setPlaceholderText("Város, utca")
        self.tipus_in = QComboBox(); self.tipus_in.addItems(["ÉH", "HSO", "ÉH+HSO"])
        l1.addWidget(self.nev_in, 2); l1.addWidget(self.cim_in, 3); l1.addWidget(self.tipus_in, 1)
        layout.addLayout(l1)

        # 2. sor: Mennyiségek lenyílóval
        l2 = QHBoxLayout()
        l2.addWidget(QLabel("<b>Üres kint:</b>"))
        self.u_db = QLineEdit(); self.u_db.setPlaceholderText("db"); self.u_db.setFixedWidth(50)
        self.u_meret = QComboBox(); self.u_meret.addItems(["30 L", "60 L"])
        l2.addWidget(self.u_db); l2.addWidget(self.u_meret)
        
        l2.addSpacing(30)
        l2.addWidget(QLabel("<b>Elhozandó:</b>"))
        self.e_db = QLineEdit(); self.e_db.setPlaceholderText("db"); self.e_db.setFixedWidth(50)
        self.e_meret = QComboBox(); self.e_meret.addItems(["30 L", "60 L"])
        l2.addWidget(self.e_db); l2.addWidget(self.e_meret)
        l2.addStretch()
        layout.addLayout(l2)

        # Napok
        napok_l = QHBoxLayout()
        self.nap_boxok = {n: QCheckBox(n) for n in self.napok}
        for cb in self.nap_boxok.values(): napok_l.addWidget(cb)
        layout.addLayout(napok_l)

        # Gombok
        btn_l = QHBoxLayout()
        ment_btn = QPushButton("➕ Mentés / Frissítés"); ment_btn.setStyleSheet("height: 35px; font-weight: bold;")
        ment_btn.clicked.connect(self.adat_hozzaadas)
        torl_btn = QPushButton("🗑️ Törlés"); torl_btn.clicked.connect(self.adat_torles)
        ell_btn = QPushButton("🔍 ELLENŐRZÉS"); ell_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; height: 35px; padding: 0 20px;")
        ell_btn.clicked.connect(self.ellenorzes)
        btn_l.addWidget(ment_btn); btn_l.addWidget(torl_btn); btn_l.addStretch(); btn_l.addWidget(ell_btn)
        layout.addLayout(btn_l)

        self.dialog.exec()

    def frissit_tablazat(self):
        self.tablazat.setRowCount(0)
        for i, ad in enumerate(self.bv_lista):
            self.tablazat.insertRow(i)
            self.tablazat.setItem(i, 0, QTableWidgetItem(ad['nev']))
            self.tablazat.setItem(i, 1, QTableWidgetItem(ad['cim']))
            self.tablazat.setItem(i, 2, QTableWidgetItem(ad['tipus']))
            self.tablazat.setItem(i, 3, QTableWidgetItem(f"{ad.get('u_db',0)} x {ad.get('u_m','30 L')}"))
            # Súly kijelzése az elhozandónál
            suly = int(ad.get('e_db',0)) * (29 if ad.get('e_m') == "30 L" else 57)
            self.tablazat.setItem(i, 4, QTableWidgetItem(f"{ad.get('e_db',0)} x {ad.get('e_m','30 L')} ({suly} kg)"))
            self.tablazat.setItem(i, 5, QTableWidgetItem(", ".join(ad['napok'])))

    def adat_hozzaadas(self):
        nev = self.nev_in.text().strip()
        if not nev: return
        uj = {
            "nev": nev, "cim": self.cim_in.text().strip(), "tipus": self.tipus_in.currentText(),
            "u_db": self.u_db.text() or "0", "u_m": self.u_meret.currentText(),
            "e_db": self.e_db.text() or "0", "e_m": self.e_meret.currentText(),
            "napok": [n for n, cb in self.nap_boxok.items() if cb.isChecked()]
        }
        idx = next((i for i, item in enumerate(self.bv_lista) if item["nev"] == nev), None)
        if idx is not None: self.bv_lista[idx] = uj
        else: self.bv_lista.append(uj)
        self.mentes_adatok(); self.frissit_tablazat()

    def adat_betoltese_szerkesztesre(self, item):
        ad = self.bv_lista[item.row()]
        self.nev_in.setText(ad['nev']); self.cim_in.setText(ad['cim'])
        self.tipus_in.setCurrentText(ad['tipus'])
        self.u_db.setText(ad.get('u_db','')); self.u_meret.setCurrentText(ad.get('u_m','30 L'))
        self.e_db.setText(ad.get('e_db','')); self.e_meret.setCurrentText(ad.get('e_m','30 L'))
        for n, cb in self.nap_boxok.items(): cb.setChecked(n in ad['napok'])

    def adat_torles(self):
        if self.tablazat.currentRow() >= 0:
            self.bv_lista.pop(self.tablazat.currentRow())
            self.mentes_adatok(); self.frissit_tablazat()

    def ellenorzes(self):
        from datetime import datetime
        nap_hu = {"Monday": "Hétfő", "Tuesday": "Kedd", "Wednesday": "Szerda", "Thursday": "Csütörtök", "Friday": "Péntek", "Saturday": "Szombat", "Sunday": "Vasárnap"}
        mai = nap_hu.get(datetime.now().strftime("%A"), "Hétfő")
        bent = [self.main.right_tree.topLevelItem(i).child(j).text(0).upper() for i in range(self.main.right_tree.topLevelItemCount()) for j in range(self.main.right_tree.topLevelItem(i).childCount())]
        hianyk = [f"🚨 {p['nev']} ({p['e_db']}x{p['u_m']})" for p in self.bv_lista if mai in p['napok'] and not any(p['nev'].upper() in b for b in bent)]
        if hianyk: QMessageBox.critical(self.dialog, "Hiányzó fuvarok", f"Ma ({mai}) elmaradt:\n\n" + "\n".join(hianyk))
        else: QMessageBox.information(self.dialog, "Rendben", "Minden mai BV fuvar betervezve!")
