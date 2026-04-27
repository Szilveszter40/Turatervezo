import json
import os
import datetime
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
        # Védett indítás
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

    def behelyez_tura_a_programba(self, tura_adat):
        """Továbbfejlesztett betöltő: Duplikáció szűréssel"""
        if not hasattr(self.main, 'add_tura_item') or not hasattr(self.main, 'right_tree'): return
        
        t_teljes_nev = f"🚛 {tura_adat['nev']}"
        
        # 1. ELLENŐRZÉS: Benne van-e már ez a túra?
        for i in range(self.main.right_tree.topLevelItemCount()):
            if self.main.right_tree.topLevelItem(i).text(0) == t_teljes_nev:
                # Ha már benne van, nem tesszük be újra, de a súlyokat frissíthetjük
                return 

        self.main.right_tree.blockSignals(True)
        try:
            ti = self.main.add_tura_item(t_teljes_nev)
            ti.setData(0, Qt.ItemDataRole.UserRole, "TURA")
            
            talalt_db = 0
            for p_nev in tura_adat['tagok']:
                adat = next((x for x in self.intezmenyek if x['nev'] == p_nev), None)
                if not adat: continue
                
                e_db = str(adat.get('e_db', '0'))
                s_val = int(e_db if e_db.isdigit() else 0) * (29 if adat.get('e_m') == "30 L" else 57)
                teljes_nev = f"{adat['nev']} ({adat.get('cim','')})"
                
                ex = QTreeWidgetItem(ti, [teljes_nev, "", adat['tipus'], e_db, str(s_val), "", ""])
                ex.setData(0, Qt.ItemDataRole.UserRole, "PARTNER")
                ex.setForeground(0, QColor("black"))
                
                # Tétel (pipa nélkül)
                c_new = QTreeWidgetItem(ex, ["", "", adat['tipus'], e_db, str(s_val), "", ""])
                c_new.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                talalt_db += 1
                
            ti.setExpanded(True)
            if talalt_db > 0 and hasattr(self.main, 'recalculate'):
                self.main.recalculate()
                
        finally:
            self.main.right_tree.blockSignals(False)

    def megjelenites(self):
        self.dialog = QDialog(self.main)
        self.dialog.setWindowTitle("BV Rendszer")
        self.dialog.setMinimumSize(1000, 700)
        layout = QVBoxLayout(self.dialog)
        tabs = QTabWidget()
        
        tab1 = QWidget(); l1 = QVBoxLayout(tab1)
        self.tablazat_int = QTableWidget(0, 5)
        self.tablazat_int.setHorizontalHeaderLabels(["Név", "Cím", "Típus", "Üres", "Elhozandó"])
        self.tablazat_int.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        l1.addWidget(self.tablazat_int)
        
        bev_l = QHBoxLayout()
        self.i_nev = QLineEdit(); self.i_nev.setPlaceholderText("Név")
        self.i_cim = QLineEdit(); self.i_cim.setPlaceholderText("Cím")
        self.i_tip = QComboBox(); self.i_tip.addItems(["ÉH", "HSO", "ÉH+HSO"])
        self.i_u_db = QLineEdit(); self.i_u_db.setPlaceholderText("Üres db")
        self.i_u_m = QComboBox(); self.i_u_m.addItems(["30 L", "60 L"])
        self.i_e_db = QLineEdit(); self.i_e_db.setPlaceholderText("Teli db")
        self.i_e_m = QComboBox(); self.i_e_m.addItems(["30 L", "60 L"])
        for w in [self.i_nev, self.i_cim, self.i_tip, self.i_u_db, self.i_u_m, self.i_e_db, self.i_e_m]: bev_l.addWidget(w)
        l1.addLayout(bev_l)
        
        i_btns = QHBoxLayout()
        m_btn = QPushButton("Mentés"); m_btn.clicked.connect(self.intezmeny_mentes)
        t_btn = QPushButton("Törlés"); t_btn.clicked.connect(self.intezmeny_torles)
        i_btns.addWidget(m_btn); i_btns.addWidget(t_btn); i_btns.addStretch(); l1.addLayout(i_btns)
        
        tab2 = QWidget(); l2 = QVBoxLayout(tab2)
        self.tablazat_tura = QTableWidget(0, 3)
        self.tablazat_tura.setHorizontalHeaderLabels(["Túra neve", "Napok", "Tagok"])
        self.tablazat_tura.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        l2.addWidget(self.tablazat_tura)
        
        t_form = QFrame(); tf_l = QVBoxLayout(t_form)
        self.t_nev = QLineEdit(); self.t_nev.setPlaceholderText("Túra neve")
        tf_l.addWidget(QLabel("Túra neve:")); tf_l.addWidget(self.t_nev)
        nap_l = QHBoxLayout()
        self.t_napok = {n: QCheckBox(n) for n in self.napok}
        for cb in self.t_napok.values(): nap_l.addWidget(cb)
        tf_l.addLayout(nap_l)
        
        p_sel = QHBoxLayout(); self.p_combo = QComboBox(); self.p_list = QListWidget(); p_add = QPushButton("Hozzáad")
        p_sel.addWidget(QLabel("Börtön:")); p_sel.addWidget(self.p_combo, 2); p_sel.addWidget(p_add); tf_l.addLayout(p_sel); tf_l.addWidget(self.p_list)
        p_add.clicked.connect(lambda: self.p_list.addItem(self.p_combo.currentText()) if self.p_combo.currentText() else None)
        
        t_btn_l = QHBoxLayout()
        tm_btn = QPushButton("Mentés"); tm_btn.clicked.connect(self.tura_mentes)
        tl_btn = QPushButton("Betöltés MOST"); tl_btn.setStyleSheet("background-color: #27ae60; color: white;")
        tl_btn.clicked.connect(self.manualis_inditas)
        t_btn_l.addWidget(tm_btn); t_btn_l.addStretch(); t_btn_l.addWidget(tl_btn); tf_l.addLayout(t_btn_l)
        l2.addWidget(t_form)

        tabs.addTab(tab1, "Intézmények"); tabs.addTab(tab2, "Fix Túrák")
        layout.addWidget(tabs); self.frissit_felulet(); self.dialog.exec()

    def frissit_felulet(self):
        self.tablazat_int.setRowCount(0); self.p_combo.clear()
        for i, ad in enumerate(self.intezmenyek):
            self.tablazat_int.insertRow(i)
            self.tablazat_int.setItem(i, 0, QTableWidgetItem(ad['nev']))
            self.tablazat_int.setItem(i, 1, QTableWidgetItem(ad['cim']))
            self.tablazat_int.setItem(i, 2, QTableWidgetItem(ad['tipus']))
            self.tablazat_int.setItem(i, 3, QTableWidgetItem(f"{ad['u_db']}x{ad['u_m']}"))
            self.tablazat_int.setItem(i, 4, QTableWidgetItem(f"{ad['e_db']}x{ad['e_m']}"))
            self.p_combo.addItem(ad['nev'])
        self.tablazat_tura.setRowCount(0)
        for i, t in enumerate(self.turak):
            self.tablazat_tura.insertRow(i)
            self.tablazat_tura.setItem(i, 0, QTableWidgetItem(t['nev']))
            self.tablazat_tura.setItem(i, 1, QTableWidgetItem(", ".join(t['napok'])))
            self.tablazat_tura.setItem(i, 2, QTableWidgetItem(str(len(t['tagok']))))

    def intezmeny_mentes(self):
        nev = self.i_nev.text().strip()
        if not nev: return
        uj = {"nev": nev, "cim": self.i_cim.text(), "tipus": self.i_tip.currentText(), "u_db": self.i_u_db.text() or "0", "u_m": self.i_u_m.currentText(), "e_db": self.i_e_db.text() or "0", "e_m": self.i_e_m.currentText()}
        idx = next((i for i, x in enumerate(self.intezmenyek) if x['nev'] == nev), None)
        if idx is not None: self.intezmenyek[idx] = uj
        else: self.intezmenyek.append(uj)
        self.mentes_minden_adat(); self.frissit_felulet()

    def tura_mentes(self):
        nev = self.t_nev.text().strip()
        if not nev: return
        uj_t = {"nev": nev, "napok": [n for n, cb in self.t_napok.items() if cb.isChecked()], "tagok": [self.p_list.item(i).text() for i in range(self.p_list.count())]}
        idx = next((i for i, x in enumerate(self.turak) if x['nev'] == nev), None)
        if idx is not None: self.turak[idx] = uj_t
        else: self.turak.append(uj_t)
        self.mentes_minden_adat(); self.frissit_felulet()

    def manualis_inditas(self):
        row = self.tablazat_tura.currentRow()
        if row >= 0:
            self.behelyez_tura_a_programba(self.turak[row])

    def automatikus_inditas(self):
        nap_hu = {"Monday":"Hétfő","Tuesday":"Kedd","Wednesday":"Szerda","Thursday":"Csütörtök","Friday":"Péntek","Saturday":"Szombat","Sunday":"Vasárnap"}
        holnap = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%A")
        mai_nap_nev = nap_hu.get(holnap, "Hétfő")
        for tura in self.turak:
            if mai_nap_nev in tura.get('napok', []):
                self.behelyez_tura_a_programba(tura)

    def intezmeny_torles(self):
        if self.tablazat_int.currentRow() >= 0:
            self.intezmenyek.pop(self.tablazat_int.currentRow()); self.mentes_minden_adat(); self.frissit_felulet()

    def tura_torles(self):
        if self.tablazat_tura.currentRow() >= 0:
            self.turak.pop(self.tablazat_tura.currentRow()); self.mentes_minden_adat(); self.frissit_felulet()
