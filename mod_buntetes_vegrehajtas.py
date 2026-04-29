import json
import os
import datetime
import re
from PyQt6.QtWidgets import (QPushButton, QDialog, QVBoxLayout, QHBoxLayout, 
                             QLabel, QMessageBox, QLineEdit, QComboBox, 
                             QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QTreeWidgetItem, QListWidget, QFrame, QTabWidget, QWidget)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

class ModulInit:
    def __init__(self, main_app):
        self.main = main_app
        self.mappa = os.path.dirname(os.path.abspath(__file__))
        self.bv_adat_fajl = os.path.join(self.mappa, "bv_intezmenyek.json")
        self.bv_tura_fajl = os.path.join(self.mappa, "bv_fix_turak.json")
        self.napok = ["Hétfő", "Kedd", "Szerda", "Csütörtök", "Péntek", "Szombat", "Vasárnap"]
        
        self.betolt_minden_adatot()
        self.init_gomb()
        QTimer.singleShot(3500, self.automatikus_inditas)

    def betolt_minden_adatot(self):
        try:
            if os.path.exists(self.bv_adat_fajl):
                with open(self.bv_adat_fajl, "r", encoding="utf-8") as f: self.intezmenyek = json.load(f)
            else: self.intezmenyek = []
        except: self.intezmenyek = []
        try:
            if os.path.exists(self.bv_tura_fajl):
                with open(self.bv_tura_fajl, "r", encoding="utf-8") as f: self.turak = json.load(f)
            else: self.turak = []
        except: self.turak = []

    def mentes_minden_adat(self):
        with open(self.bv_adat_fajl, "w", encoding="utf-8") as f: json.dump(self.intezmenyek, f, indent=4)
        with open(self.bv_tura_fajl, "w", encoding="utf-8") as f: json.dump(self.turak, f, indent=4)

    def init_gomb(self):
        if hasattr(self.main, 'bv_btn_obj'): return
        self.main.bv_btn_obj = QPushButton("⚖️ BV KEZELŐ")
        self.main.bv_btn_obj.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold; padding: 6px; border-radius: 4px;")
        self.main.bv_btn_obj.clicked.connect(self.megjelenites)
        if hasattr(self.main, 'left_tree'):
            self.main.left_tree.parent().layout().insertWidget(1, self.main.bv_btn_obj)

    def frissit_felulet(self):
        self.tablazat_int.setRowCount(0)
        for i, ad in enumerate(self.intezmenyek):
            self.tablazat_int.insertRow(i)
            self.tablazat_int.setItem(i, 0, QTableWidgetItem(ad['nev']))
            self.tablazat_int.setItem(i, 1, QTableWidgetItem(ad['cim']))
            self.tablazat_int.setItem(i, 2, QTableWidgetItem(ad['tipus']))
            self.tablazat_int.setItem(i, 3, QTableWidgetItem(f"{ad['u_db']}x{ad['u_m']}"))
            self.tablazat_int.setItem(i, 4, QTableWidgetItem(f"{ad['e_db']}x{ad['e_m']}"))
        
        self.tablazat_tura.setRowCount(0)
        for i, t in enumerate(self.turak):
            self.tablazat_tura.insertRow(i)
            self.tablazat_tura.setItem(i, 0, QTableWidgetItem(t['nev']))
            self.tablazat_tura.setItem(i, 1, QTableWidgetItem(", ".join(t['napok'])))
            self.tablazat_tura.setItem(i, 2, QTableWidgetItem(f"{len(t['tagok'])} cím"))
        self.combo_szures()

    def combo_szures(self):
        """GLOBÁLIS SZŰRÉS: Csak azokat mutatja, amik SEMMILYEN túrában nincsenek benne"""
        self.p_combo.clear()
        
        # 1. Összegyűjtjük az összes nevet, ami bármelyik elmentett túrában benne van
        osszes_beosztott_nev = set()
        for tura in self.turak:
            # Ha éppen szerkesztünk egy túrát, annak a régi tagjait ne vegyük be a tiltólistába,
            # különben nem tudnánk visszatenni őket ugyanabba a túrába szerkesztéskor.
            if tura['nev'] != self.t_nev.text().strip():
                for tag in tura['tagok']:
                    osszes_beosztott_nev.add(tag)
        
        # 2. Hozzáadjuk azokat is, amik az aktuális szerkesztési listában (p_list) vannak
        for i in range(self.p_list.count()):
            osszes_beosztott_nev.add(self.p_list.item(i).text())
        
        # 3. Csak a maradékot rakjuk a lenyílóba
        for ad in self.intezmenyek:
            if ad['nev'] not in osszes_beosztott_nev:
                self.p_combo.addItem(ad['nev'])

    def borton_hozzaad(self):
        nev = self.p_combo.currentText()
        if nev:
            self.p_list.addItem(nev)
            self.combo_szures()

    def borton_eltavolit(self, item):
        self.p_list.takeItem(self.p_list.row(item))
        self.combo_szures()

    def betolt_intezmeny_szerkesztesre(self, row, col):
        ad = self.intezmenyek[row]
        self.i_nev.setText(ad['nev'])
        self.i_cim.setText(ad['cim'])
        self.i_tip.setCurrentText(ad['tipus'])
        self.i_u_db.setText(ad['u_db'])
        self.i_u_m.setCurrentText(ad['u_m'])
        self.i_e_db.setText(ad['e_db'])
        self.i_e_m.setCurrentText(ad['e_m'])

    def betolt_tura_szerkesztesre(self, row, col):
        t_nev = self.tablazat_tura.item(row, 0).text()
        tura = next((t for t in self.turak if t['nev'] == t_nev), None)
        if tura:
            self.t_nev.setText(tura['nev'])
            for nap, cb in self.t_napok.items():
                cb.setChecked(nap in tura['napok'])
            self.p_list.clear()
            self.p_list.addItems(tura['tagok'])
            self.combo_szures()

    def intezmeny_mentes(self):
        nev = self.i_nev.text().strip()
        if not nev: return
        uj = {"nev": nev, "cim": self.i_cim.text(), "tipus": self.i_tip.currentText(), 
              "u_db": self.i_u_db.text() or "0", "u_m": self.i_u_m.currentText(), 
              "e_db": self.i_e_db.text() or "0", "e_m": self.i_e_m.currentText()}
        idx = next((i for i, x in enumerate(self.intezmenyek) if x['nev'] == nev), None)
        if idx is not None: self.intezmenyek[idx] = uj
        else: self.intezmenyek.append(uj)
        self.mentes_minden_adat(); self.frissit_felulet()
        for w in [self.i_nev, self.i_cim, self.i_u_db, self.i_e_db]: w.clear()

    def tura_mentes(self):
        nev = self.t_nev.text().strip()
        tagok = [self.p_list.item(i).text() for i in range(self.p_list.count())]
        if not nev or not tagok: return
        uj_t = {"nev": nev, "napok": [n for n, cb in self.t_napok.items() if cb.isChecked()], "tagok": tagok}
        idx = next((i for i, x in enumerate(self.turak) if x['nev'] == nev), None)
        if idx is not None: self.turak[idx] = uj_t
        else: self.turak.append(uj_t)
        self.mentes_minden_adat(); self.frissit_felulet()
        self.t_nev.clear(); self.p_list.clear(); self.combo_szures()
        for cb in self.t_napok.values(): cb.setChecked(False)

    def tura_torles(self):
        row = self.tablazat_tura.currentRow()
        if row >= 0:
            if QMessageBox.question(self.dialog, "Törlés", "Biztosan törlöd a túrát?") == QMessageBox.StandardButton.Yes:
                self.turak.pop(row); self.mentes_minden_adat(); self.frissit_felulet()
                self.t_nev.clear(); self.p_list.clear(); self.combo_szures()

    def manualis_inditas(self):
        row = self.tablazat_tura.currentRow()
        if row >= 0:
            self.behelyez_tura_a_programba(self.turak[row])
            self.dialog.accept()

    def automatikus_inditas(self):
        nap_hu = {"Monday":"Hétfő","Tuesday":"Kedd","Wednesday":"Szerda","Thursday":"Csütörtök","Friday":"Péntek","Saturday":"Szombat","Sunday":"Vasárnap"}
        holnap = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%A")
        mai_nap_nev = nap_hu.get(holnap, "Hétfő")
        for tura in self.turak:
            if mai_nap_nev in tura.get('napok', []):
                self.behelyez_tura_a_programba(tura)

    def intezmeny_torles(self):
        row = self.tablazat_int.currentRow()
        if row >= 0:
            if QMessageBox.question(self.dialog, "Törlés", "Biztosan törlöd?") == QMessageBox.StandardButton.Yes:
                self.intezmenyek.pop(row); self.mentes_minden_adat(); self.frissit_felulet()

    def behelyez_tura_a_programba(self, tura_adat):
        if not hasattr(self.main, 'add_tura_item'): return
        t_teljes_nev = f"🚛 {tura_adat['nev']}"
        ti = self.main.add_tura_item(t_teljes_nev)
        for p_nev in tura_adat['tagok']:
            adat = next((x for x in self.intezmenyek if x['nev'] == p_nev), None)
            if not adat: continue
            e_db = int(adat['e_db']) if adat['e_db'].isdigit() else 0
            suly = e_db * (29 if adat['e_m'] == "30 L" else 57)
            p_item = QTreeWidgetItem(ti, [f"{adat['nev']} ({adat['cim']})", "", "", str(e_db), f"{suly} kg", "", ""])
            p_item.setData(0, Qt.ItemDataRole.UserRole, "PARTNER")
            QTreeWidgetItem(p_item, ["", adat['tipus'], "", str(e_db), f"{suly} kg", "", ""])
        if hasattr(self.main, 'recalculate'): self.main.recalculate()

    def megjelenites(self):
        self.dialog = QDialog(self.main)
        self.dialog.setWindowTitle("BV Rendszer")
        self.dialog.setMinimumSize(1000, 700)
        self.dialog.setStyleSheet("""
            QTableWidget { selection-background-color: #d5f5e3; selection-color: black; }
            QListWidget { selection-background-color: #d5f5e3; selection-color: black; }
            QPushButton#SaveBtn { background-color: #27ae60; color: white; font-weight: bold; border-radius: 4px; padding: 5px; }
            QPushButton#DelBtn { background-color: #e74c3c; color: white; font-weight: bold; border-radius: 4px; padding: 5px; }
            QPushButton#AddBtn { background-color: #3498db; color: white; font-weight: bold; border-radius: 4px; }
            QPushButton#LoadBtn { background-color: #f39c12; color: white; font-weight: bold; border-radius: 4px; padding: 8px; }
        """)
        
        layout = QVBoxLayout(self.dialog)
        tabs = QTabWidget()
        
        # TAB 1 - Intézmények
        tab1 = QWidget(); l1 = QVBoxLayout(tab1)
        self.tablazat_int = QTableWidget(0, 5)
        self.tablazat_int.setHorizontalHeaderLabels(["Név", "Cím", "Típus", "Üres", "Elhozandó"])
        self.tablazat_int.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tablazat_int.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tablazat_int.cellClicked.connect(self.betolt_intezmeny_szerkesztesre)
        l1.addWidget(self.tablazat_int)
        
        bev_l = QHBoxLayout()
        self.i_nev = QLineEdit(); self.i_cim = QLineEdit(); self.i_tip = QComboBox()
        self.i_tip.addItems(["ÉH", "HSO", "ÉH+HSO"])
        self.i_u_db = QLineEdit(); self.i_u_m = QComboBox(); self.i_u_m.addItems(["30 L", "60 L"])
        self.i_e_db = QLineEdit(); self.i_e_m = QComboBox(); self.i_e_m.addItems(["30 L", "60 L"])
        for w in [self.i_nev, self.i_cim, self.i_tip, self.i_u_db, self.i_u_m, self.i_e_db, self.i_e_m]: bev_l.addWidget(w)
        l1.addLayout(bev_l)
        
        i_btns = QHBoxLayout()
        m_btn = QPushButton("💾 MENTÉS / MÓDOSÍTÁS"); m_btn.setObjectName("SaveBtn"); m_btn.clicked.connect(self.intezmeny_mentes)
        t_btn = QPushButton("🗑️ TÖRLÉS"); t_btn.setObjectName("DelBtn"); t_btn.clicked.connect(self.intezmeny_torles)
        i_btns.addWidget(m_btn); i_btns.addWidget(t_btn); l1.addLayout(i_btns)
        
        # TAB 2 - Fix Túrák
        tab2 = QWidget(); l2 = QVBoxLayout(tab2)
        self.tablazat_tura = QTableWidget(0, 3)
        self.tablazat_tura.setHorizontalHeaderLabels(["Túra neve", "Napok", "Tagok"])
        self.tablazat_tura.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tablazat_tura.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tablazat_tura.cellClicked.connect(self.betolt_tura_szerkesztesre)
        l2.addWidget(self.tablazat_tura)
        
        t_form = QFrame(); tf_l = QVBoxLayout(t_form)
        self.t_nev = QLineEdit()
        # Ha átírjuk a túra nevét gépeléskor, frissítsük a listát (fontos a globális szűréshez)
        self.t_nev.textChanged.connect(self.combo_szures)
        tf_l.addWidget(QLabel("Túra neve:")); tf_l.addWidget(self.t_nev)
        
        nap_l = QHBoxLayout()
        self.t_napok = {n: QCheckBox(n) for n in self.napok}
        for cb in self.t_napok.values(): nap_l.addWidget(cb)
        tf_l.addLayout(nap_l)
        
        p_sel = QHBoxLayout(); self.p_combo = QComboBox(); self.p_list = QListWidget(); p_add = QPushButton("➕ HOZZÁAD")
        p_add.setObjectName("AddBtn"); p_add.setFixedHeight(28)
        p_sel.addWidget(QLabel("Börtön:")); p_sel.addWidget(self.p_combo, 2); p_sel.addWidget(p_add); tf_l.addLayout(p_sel)
        tf_l.addWidget(self.p_list)
        p_add.clicked.connect(self.borton_hozzaad)
        self.p_list.itemDoubleClicked.connect(self.borton_eltavolit)
        
        t_btn_l = QHBoxLayout()
        tm_btn = QPushButton("💾 TÚRA MENTÉSE"); tm_btn.setObjectName("SaveBtn"); tm_btn.clicked.connect(self.tura_mentes)
        tt_btn = QPushButton("🗑️ TÚRA TÖRLÉSE"); tt_btn.setObjectName("DelBtn"); tt_btn.clicked.connect(self.tura_torles)
        tl_btn = QPushButton("🚀 BETÖLTÉS A TERVEZŐBE"); tl_btn.setObjectName("LoadBtn"); tl_btn.clicked.connect(self.manualis_inditas)
        t_btn_l.addWidget(tm_btn); t_btn_l.addWidget(tt_btn); t_btn_l.addStretch(); t_btn_l.addWidget(tl_btn)
        tf_l.addLayout(t_btn_l); l2.addWidget(t_form)

        tabs.addTab(tab1, "Intézmények"); tabs.addTab(tab2, "Fix Túrák")
        layout.addWidget(tabs); self.frissit_felulet(); self.dialog.exec()
