import json
import os
import datetime
from PyQt6.QtWidgets import (QPushButton, QMenu, QMessageBox, QInputDialog, 
                             QTreeWidgetItem, QVBoxLayout, QHBoxLayout, QWidget, 
                             QDialog, QListWidget, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont

class ModulInit:
    def __init__(self, main_app):
        self.main = main_app
        if not hasattr(self.main, 'fix_tura_storage'):
            self.main.fix_tura_storage = []
        self.main.fix_tura_storage.append(self)
        
        self.sablon_utvonal = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fix_turak_napi.json")
        QTimer.singleShot(1200, self.init_gombok)

    def takaritas(self):
        """Eltávolítja a régi gombokat és konténereket a duplázódás elkerülésére"""
        old_objs = ['fix_tura_btn_obj', 'holnap_btn_obj', 'fix_kontener_obj', 'gomb_sor_kontener']
        for obj_name in old_objs:
            if hasattr(self.main, obj_name):
                obj = getattr(self.main, obj_name)
                try:
                    obj.setParent(None)
                    obj.deleteLater()
                except: pass
                delattr(self.main, obj_name)

    def init_gombok(self):
        # 1. RÉGI GOMBOK TÖRLÉSE
        self.takaritas()

        # 2. ÚJ KÖZÖS KONTÉNER LÉTREHOZÁSA
        self.main.gomb_sor_kontener = QWidget()
        layout = QHBoxLayout(self.main.gomb_sor_kontener)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4) # Pici szünet a gombok között

        # --- SABLON GOMB (33%) ---
        self.main.fix_tura_btn_obj = QPushButton("📋 SABLON")
        self.main.fix_tura_btn_obj.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold; padding: 6px; border-radius: 3px;")
        self.main.fix_tura_btn_obj.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.menu = QMenu(self.main.fix_tura_btn_obj)
        self.menu.addAction("📅 Visszakeresés").triggered.connect(self.kezi_valasztas_ablak)
        self.menu.addAction("💾 Mentés sablonként").triggered.connect(self.mentes_aktualis_kijelolt)
        self.main.fix_tura_btn_obj.setMenu(self.menu)

        # --- HOLNAP GOMB (33%) ---
        self.main.holnap_btn_obj = QPushButton("🚚 HOLNAP")
        self.main.holnap_btn_obj.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 6px; border-radius: 3px;")
        self.main.holnap_btn_obj.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.main.holnap_btn_obj.clicked.connect(self.holnapi_inditas_fix)

        # --- TÉRKÉP GOMB (33%) ---
        # Ha a térkép modul már létrehozta, áthelyezzük, ha nem, létrehozzuk ideiglenesen
        if hasattr(self.main, 'terkep_btn_obj'):
            self.terkep_btn = self.main.terkep_btn_obj
        else:
            self.terkep_btn = QPushButton("🗺️ TÉRKÉP")
            self.terkep_btn.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; padding: 6px; border-radius: 3px;")
            self.main.terkep_btn_obj = self.terkep_btn # Referencia a másik modulnak
        
        self.terkep_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # 3. HOZZÁADÁS A LAYOUT-HOZ EGYENLŐ ARÁNYBAN (1:1:1)
        layout.addWidget(self.main.fix_tura_btn_obj, 1)
        layout.addWidget(self.main.holnap_btn_obj, 1)
        layout.addWidget(self.terkep_btn, 1)

        # 4. BEILLESZTÉS A FŐABLAKBA
        try:
            target = self.main.right_tree.parent().layout()
            # Az 1-es index a fa (lista) fölé rakja közvetlenül
            target.insertWidget(1, self.main.gomb_sor_kontener)
        except: pass

    def suly_ellenorzes(self):
        if not hasattr(self.main, 'right_tree'): return
        self.main.right_tree.blockSignals(True)
        bold_f = QFont(); bold_f.setBold(True)
        try:
            for i in range(self.main.right_tree.topLevelItemCount()):
                it = self.main.right_tree.topLevelItem(i)
                if it.data(0, Qt.ItemDataRole.UserRole) == "TURA":
                    try:
                        s_txt = "".join(c for c in it.text(4) if c.isdigit() or c in ".,")
                        s_txt = s_txt.replace(",", ".")
                        s = float(s_txt) if s_txt else 0.0
                        it.setFont(4, bold_f)
                        it.setForeground(4, QColor("red") if s > 2000 else QColor("black"))
                    except: pass
        finally:
            self.main.right_tree.blockSignals(False)

    def holnapi_inditas_fix(self):
        try:
            holnap = datetime.datetime.now() + datetime.timedelta(days=1)
            napok = ["Hétfő", "Kedd", "Szerda", "Csütörtök", "Péntek", "Szombat", "Vasárnap"]
            h_nap = napok[holnap.weekday()]
            h_szam = holnap.isocalendar()[1]
            h_het = "Páros hét" if h_szam % 2 == 0 else "Páratlan hét"
            self.napi_osszes_betoltese(h_het, h_nap)
        except Exception as e: print(f"Dátum hiba: {e}")

    def napi_osszes_betoltese(self, het_pref, nap_pref):
        if not os.path.exists(self.sablon_utvonal): return
        with open(self.sablon_utvonal, "r", encoding="utf-8") as f: ad = json.load(f)
        t_terv = ad.get(het_pref, {}).get(nap_pref, {}).copy()
        if "Minden héten" in ad: t_terv.update(ad["Minden héten"].get(nap_pref, {}))
        if not t_terv:
            QMessageBox.information(self.main, "Infó", f"Nincs mentett adat: {nap_pref}")
            return
        self.main.right_tree.blockSignals(True)
        try:
            bal_oldal = {self.main.left_tree.topLevelItem(i).text(0).split('(')[0].strip().upper(): self.main.left_tree.topLevelItem(i) 
                         for i in range(self.main.left_tree.topLevelItemCount())}
            for t_nev, p_nevek in t_terv.items():
                if t_nev == "_mentve": continue
                ti = self.main.add_tura_item(f"🚛 {t_nev}")
                ti.setData(0, Qt.ItemDataRole.UserRole, "TURA")
                for p_mentett in p_nevek:
                    p_clean = p_mentett.split('(')[0].strip().upper()
                    if p_clean in bal_oldal:
                        lp = bal_oldal[p_clean]
                        uj_p = QTreeWidgetItem(ti)
                        uj_p.setText(0, lp.text(0)); uj_p.setText(3, lp.text(2)); uj_p.setText(4, lp.text(3))
                        uj_p.setData(0, Qt.ItemDataRole.UserRole, "PARTNER")
                        for k in range(lp.childCount()):
                            c_old = lp.child(k); c_uj = QTreeWidgetItem(uj_p)
                            t_n = c_old.text(1)
                            if t_n.startswith("K-"): c_uj.setText(1, t_n)
                            else: c_uj.setText(2, t_n)
                            c_uj.setText(3, c_old.text(2)); c_uj.setText(4, c_old.text(3))
                        idx = self.main.left_tree.indexOfTopLevelItem(lp)
                        if idx != -1: self.main.left_tree.takeTopLevelItem(idx)
            if hasattr(self.main, 'recalculate'): self.main.recalculate()
        finally:
            self.main.right_tree.blockSignals(False)
            self.suly_ellenorzes()

    def kezi_valasztas_ablak(self):
        if not os.path.exists(self.sablon_utvonal): return
        with open(self.sablon_utvonal, "r", encoding="utf-8") as f: ad = json.load(f)
        d = QDialog(self.main); d.setWindowTitle("Betöltés"); l = QVBoxLayout(d); lw = QListWidget()
        for h in sorted(ad.keys()):
            if isinstance(ad[h], dict):
                for n in sorted(ad[h].keys()): lw.addItem(f"{h} - {n}")
        l.addWidget(lw)
        def b():
            if lw.currentItem():
                txt = lw.currentItem().text().split(" - ")
                d.accept(); self.napi_osszes_betoltese(txt[0], txt[1])
        btn = QPushButton("Betöltés"); btn.clicked.connect(b); l.addWidget(btn); d.exec()

    def mentes_aktualis_kijelolt(self):
        it = self.main.right_tree.currentItem()
        if not it: return
        while it.parent(): it = it.parent()
        if it.data(0, Qt.ItemDataRole.UserRole) == "TURA":
            h, ok1 = QInputDialog.getItem(self.main, "Mentés", "Hét:", ["Páros hét", "Páratlan hét", "Minden héten"], 2, False)
            n, ok2 = QInputDialog.getItem(self.main, "Mentés", "Nap:", ["Hétfő", "Kedd", "Szerda", "Csütörtök", "Péntek", "Szombat", "Vasárnap"], 0, False)
            if ok1 and ok2:
                try:
                    with open(self.sablon_utvonal, "r", encoding="utf-8") as f: ad = json.load(f)
                except: ad = {}
                t_n = it.text(0).replace("🚛 ", "")
                if h not in ad: ad[h] = {}
                if n not in ad[h]: ad[h][n] = {}
                ad[h][n][t_n] = [it.child(i).text(0) for i in range(it.childCount())]
                with open(self.sablon_utvonal, "w", encoding="utf-8") as f: json.dump(ad, f, indent=4, ensure_ascii=False)

    def auto_mentes_esemeny(self, item, column):
        if self.main.right_tree.signalsBlocked(): return
        if hasattr(self.main, 'recalculate'):
            self.main.right_tree.blockSignals(True)
            try: self.main.recalculate(); self.suly_ellenorzes()
            finally: self.main.right_tree.blockSignals(False)
