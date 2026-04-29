import os
import json
import re
import datetime
import pandas as pd
from PyQt6.QtWidgets import (QPushButton, QDialog, QVBoxLayout, QHBoxLayout, 
                             QLabel, QMessageBox, QComboBox, QTreeWidgetItem, 
                             QListWidget, QWidget, QInputDialog)
from PyQt6.QtCore import Qt, QTimer, QSize

class ModulInit:
    def __init__(self, main_app):
        self.main = main_app
        self.excel_path = "iranyitoszamok.xlsx"
        self.napok = ["Hétfő", "Kedd", "Szerda", "Csütörtök", "Péntek"]
        
        if not hasattr(self.main, 'active_modules'):
            self.main.active_modules = []
        if self not in self.main.active_modules:
            self.main.active_modules.append(self)

        QTimer.singleShot(2000, self.init_ui)

    def init_ui(self):
        if hasattr(self.main, 'auto_szetoszto_btn'): return
        self.container = QWidget()
        l = QHBoxLayout(self.container)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(5)

        gomb_stilus = "QPushButton { color: white; font-weight: bold; padding: 4px; border-radius: 4px; height: 22px; }"
        
        self.main.auto_szetoszto_btn = QPushButton("🚀 SZÉTOSZTÁS")
        self.main.auto_szetoszto_btn.setStyleSheet(gomb_stilus + "QPushButton { background-color: #27ae60; }")
        self.main.auto_szetoszto_btn.clicked.connect(self.nap_valaszto_ablak)
        
        self.edit_btn = QPushButton("⚙️ IRSZ SZERKESZTÉS")
        self.edit_btn.setStyleSheet(gomb_stilus + "QPushButton { background-color: #2980b9; }")
        self.edit_btn.clicked.connect(self.szerkeszto_ablak)

        l.addWidget(self.main.auto_szetoszto_btn, 1)
        l.addWidget(self.edit_btn, 1)

        if hasattr(self.main, 'left_tree'):
            layout = self.main.left_tree.parent().layout()
            layout.insertWidget(2, self.container)

    def szerkeszto_ablak(self):
        if not os.path.exists(self.excel_path):
            QMessageBox.warning(self.main, "Hiba", "Nincs meg az iranyitoszamok.xlsx!")
            return

        self.s_diag = QDialog(self.main)
        self.s_diag.setWindowTitle("Irányítószámok kezelése")
        self.s_diag.setMinimumSize(950, 700)
        layout = QVBoxLayout(self.s_diag)

        self.s_diag.setStyleSheet("""
            QListWidget#irszLista { background-color: white; outline: none; border: 1px solid #ddd; }
            QListWidget#irszLista::item {
                background-color: #f8f9fa; border: 1px solid #ccc; border-radius: 5px;
                color: black; font-weight: bold; font-size: 14px; margin: 5px;
                min-width: 95px; max-width: 95px; min-height: 45px; max-height: 45px;
            }
            QListWidget#irszLista::item:selected { background-color: #d5f5e3; border: 2px solid #27ae60; color: black; }
        """)

        h_top = QHBoxLayout()
        h_top.addWidget(QLabel("<b>Választott nap:</b>"))
        self.s_nap_combo = QComboBox()
        self.s_nap_combo.addItems(self.napok)
        self.s_nap_combo.currentTextChanged.connect(self.szerkeszto_adat_frissites)
        h_top.addWidget(self.s_nap_combo)
        layout.addLayout(h_top)

        lists_h = QHBoxLayout()
        v_auto = QVBoxLayout()
        v_auto.addWidget(QLabel("Autók:"))
        self.auto_list = QListWidget()
        for i in range(1, 10): self.auto_list.addItem(f"{i}. autó")
        self.auto_list.currentRowChanged.connect(self.szerkeszto_adat_frissites)
        v_auto.addWidget(self.auto_list)
        lists_h.addLayout(v_auto, 1)

        v_irsz = QVBoxLayout()
        v_irsz.addWidget(QLabel("Hozzárendelt irányítószámok:"))
        self.irsz_list = QListWidget()
        self.irsz_list.setObjectName("irszLista")
        self.irsz_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.irsz_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.irsz_list.setMovement(QListWidget.Movement.Static)
        self.irsz_list.setSpacing(10)
        v_irsz.addWidget(self.irsz_list)
        lists_h.addLayout(v_irsz, 4)
        layout.addLayout(lists_h)

        b_layout = QHBoxLayout()
        btn_add = QPushButton("➕ Új IRSZ"); btn_add.clicked.connect(self.irsz_hozzaadas)
        btn_del = QPushButton("🗑️ Törlés"); btn_del.clicked.connect(self.irsz_torles)
        btn_move = QPushButton("🔃 Áthelyezés"); btn_move.clicked.connect(self.irsz_atrakas)
        for b in [btn_add, btn_del, btn_move]: b.setFixedHeight(35); b_layout.addWidget(b)
        layout.addLayout(b_layout)

        save_btn = QPushButton("💾 MENTÉS AZ EXCELBE")
        save_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; height: 45px; border-radius: 5px;")
        save_btn.clicked.connect(self.excel_mentes)
        layout.addWidget(save_btn)

        try:
            xl = pd.ExcelFile(self.excel_path)
            self.temp_db = {sheet.strip(): xl.parse(sheet) for sheet in xl.sheet_names}
            self.auto_list.setCurrentRow(0)
        except Exception as e:
            QMessageBox.critical(self.main, "Hiba", f"Excel betöltési hiba: {e}")

        self.s_diag.exec()

    def szerkeszto_adat_frissites(self):
        if self.auto_list.currentItem() is None: return
        self.irsz_list.clear()
        auto = self.auto_list.currentItem().text().strip()
        nap = self.s_nap_combo.currentText()
        if auto in self.temp_db:
            df = self.temp_db[auto]
            if nap in df.columns:
                irszek = df[nap].dropna().astype(str).tolist()
                for i in irszek:
                    tiszta = i.split('.')[0]
                    item = self.irsz_list.addItem(tiszta)
                    self.irsz_list.item(self.irsz_list.count()-1).setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    def irsz_hozzaadas(self):
        uj, ok = QInputDialog.getText(self.s_diag, "Új IRSZ", "Irányítószám:")
        if ok and uj.strip():
            self.irsz_list.addItem(uj.strip())
            self.irsz_list.item(self.irsz_list.count()-1).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.ideiglenes_memoria_frissites()

    def irsz_torles(self):
        row = self.irsz_list.currentRow()
        if row >= 0:
            self.irsz_list.takeItem(row)
            self.ideiglenes_memoria_frissites()

    def irsz_atrakas(self):
        curr = self.irsz_list.currentItem()
        if not curr: return
        irsz = curr.text()
        cel_auto, ok = QInputDialog.getItem(self.s_diag, "Áthelyezés", f"Hova kerüljön: {irsz}?", [f"{i}. autó" for i in range(1, 10)], 0, False)
        if ok:
            # 1. Törlés a jelenlegiből
            self.irsz_list.takeItem(self.irsz_list.row(curr))
            self.ideiglenes_memoria_frissites()
            
            # 2. Hozzáadás az újhoz
            nap = self.s_nap_combo.currentText()
            df_cel = self.temp_db[cel_auto.strip()]
            
            # Crash biztos hozzáadás: új DataFrame sor összefűzése
            uj_adat = pd.DataFrame({nap: [irsz]})
            self.temp_db[cel_auto.strip()] = pd.concat([df_cel, uj_adat], ignore_index=True)
            
            QMessageBox.information(self.s_diag, "Siker", f"{irsz} átrakva ide: {cel_auto}")
            self.szerkeszto_adat_frissites()

    def ideiglenes_memoria_frissites(self):
        auto = self.auto_list.currentItem().text().strip()
        nap = self.s_nap_combo.currentText()
        uj_lista = [self.irsz_list.item(i).text() for i in range(self.irsz_list.count())]
        # Az adott oszlop frissítése az autónál
        self.temp_db[auto][nap] = pd.Series(uj_lista)

    def excel_mentes(self):
        try:
            with pd.ExcelWriter(self.excel_path) as writer:
                for auto, df in self.temp_db.items():
                    df.to_excel(writer, sheet_name=auto, index=False)
            QMessageBox.information(self.s_diag, "Siker", "Excel mentve!")
        except Exception as e:
            QMessageBox.critical(self.s_diag, "Hiba", f"Zárd be az Excelt!\n{e}")

    def nap_valaszto_ablak(self):
        if not os.path.exists(self.excel_path): return
        self.diag = QDialog(self.main)
        layout = QVBoxLayout(self.diag)
        layout.addWidget(QLabel("<b>Válassz napot a szétosztáshoz:</b>"))
        self.combo = QComboBox()
        self.combo.addItems(self.napok)
        layout.addWidget(self.combo)
        btn = QPushButton("SZÉTOSZTÁS")
        btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; height: 35px;")
        btn.clicked.connect(self.vegrehajtas)
        layout.addWidget(btn)
        self.diag.exec()

    def vegrehajtas(self):
        valasztott_nap = self.combo.currentText()
        rend = self.irsz_adatok_beolvasasa(valasztott_nap)
        if not rend: return
        
        talalt_db = 0
        self.main.right_tree.blockSignals(True)
        auto_targetek = {}

        for i in range(self.main.left_tree.topLevelItemCount() - 1, -1, -1):
            item = self.main.left_tree.topLevelItem(i)
            # Irányítószám kivágása (pl. "Név (6000 Város)")
            match = re.search(r'\((\d{4})', item.text(0))
            if match and match.group(1) in rend:
                cel_auto = rend[match.group(1)]
                t_nev = f"🚛 {cel_auto}"
                
                if cel_auto not in auto_targetek:
                    target = None
                    for j in range(self.main.right_tree.topLevelItemCount()):
                        if self.main.right_tree.topLevelItem(j).text(0) == t_nev:
                            target = self.main.right_tree.topLevelItem(j); break
                    if not target: target = self.main.add_tura_item(t_nev)
                    target.setExpanded(False)
                    auto_targetek[cel_auto] = target
                
                # Áthelyezés
                p = self.main.left_tree.takeTopLevelItem(i)
                uj_p = QTreeWidgetItem(auto_targetek[cel_auto], [p.text(0), "", "", p.text(2), p.text(3), p.text(4), "", ""])
                uj_p.setData(0, Qt.ItemDataRole.UserRole, "PARTNER")
                while p.childCount() > 0:
                    c = p.takeChild(0)
                    ki, be = (c.text(1), "") if c.text(1).startswith("K-") else ("", c.text(1))
                    QTreeWidgetItem(uj_p, ["", ki, be, c.text(2), c.text(3), "", "", ""])
                talalt_db += 1
        
        self.main.right_tree.blockSignals(False)
        if hasattr(self.main, 'recalculate'): self.main.recalculate()
        self.diag.accept()
        QMessageBox.information(self.main, "Kész", f"Szétosztva: {talalt_db} partner.")

    def irsz_adatok_beolvasasa(self, nap):
        try:
            xl = pd.ExcelFile(self.excel_path)
            rend = {}
            for sheet in xl.sheet_names:
                df = xl.parse(sheet)
                if nap in df.columns:
                    for irsz in df[nap].dropna().astype(str).tolist():
                        tiszta = irsz.split('.')[0]
                        rend[tiszta] = sheet.strip()
            return rend
        except: return None
