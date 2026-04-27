import json
import os
import datetime
from PyQt6.QtWidgets import (QPushButton, QMenu, QMessageBox, QInputDialog, 
                             QTreeWidgetItem, QVBoxLayout, QHBoxLayout, 
                             QAbstractItemView, QDialog, QListWidget, QLabel, QLineEdit, QComboBox)
from PyQt6.QtCore import Qt

class ModulInit:
    def __init__(self, main_app):
        self.main = main_app
        self.sablon_fajl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fix_turak_napi.json")
        self.napok = ["Hétfő", "Kedd", "Szerda", "Csütörtök", "Péntek", "Szombat", "Vasárnap"]
        self.het_tipusok = ["Páros hét", "Páratlan hét", "Minden héten"]
        self.init_gomb()

    def get_aktualis_het_tipus(self):
        try:
            het_szam = datetime.datetime.now().isocalendar()[1]
            return "Páros hét" if het_szam % 2 == 0 else "Páratlan hét"
        except: return "Minden héten"

    def init_gomb(self):
        # Egyedi név: fix_tura_btn_obj, a jobb oldalra helyezve
        self.main.fix_tura_btn_obj = QPushButton("📋 SABLONOK")
        self.main.fix_tura_btn_obj.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        
        uj_menu = QMenu(self.main.fix_tura_btn_obj)
        akt_het = self.get_aktualis_het_tipus()
        
        uj_menu.addAction(f"📂 MAI NAP betöltése ({akt_het})").triggered.connect(lambda: self.napi_osszes_betoltese(akt_het))
        uj_menu.addSeparator()
        uj_menu.addAction("📂 Választás kézzel...").triggered.connect(lambda: self.napi_osszes_betoltese(None))
        uj_menu.addAction("💾 Kijelölt mentése sablonként").triggered.connect(self.mentes_aktualis_kijelolt)
        uj_menu.addSeparator()
        uj_menu.addAction("✍️ ÚJ TÚRA összeállítása (Interaktív)").triggered.connect(self.interaktiv_szerkeszto_ablak)
        uj_menu.addSeparator()
        uj_menu.addAction("🗑️ MENTETT TÚRÁK (Törlés / Megtekintés)").triggered.connect(self.sablonok_kezelese)
        
        self.main.fix_tura_btn_obj.setMenu(uj_menu)

        try:
            if hasattr(self.main, 'right_tree'):
                jobb_layout = self.main.right_tree.parent().layout()
                if jobb_layout:
                    jobb_layout.insertWidget(1, self.main.fix_tura_btn_obj)
        except: pass

    def interaktiv_szerkeszto_ablak(self):
        dialog = QDialog(self.main)
        dialog.setWindowTitle("Interaktív Túra Összeállító")
        dialog.setMinimumSize(450, 550)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Túra neve:")); t_edit = QLineEdit(); layout.addWidget(t_edit)
        hl = QHBoxLayout()
        v1 = QVBoxLayout(); v1.addWidget(QLabel("Hét:")); h_c = QComboBox(); h_c.addItems(self.het_tipusok); v1.addWidget(h_c)
        v2 = QVBoxLayout(); v2.addWidget(QLabel("Nap:")); n_c = QComboBox(); n_c.addItems(self.napok); v2.addWidget(n_c)
        hl.addLayout(v1); hl.addLayout(v2); layout.addLayout(hl)
        layout.addWidget(QLabel("Partnerek (Húzd ide balról):")); pl = QListWidget(); pl.setAcceptDrops(True); layout.addWidget(pl)
        def mentes():
            if not t_edit.text().strip() or pl.count() == 0: return
            ad = self.adatok_beolvasasa(); h, n = h_c.currentText(), n_c.currentText()
            if h not in ad: ad[h] = {}
            if n not in ad[h]: ad[h][n] = {}
            ad[h][n][t_edit.text().strip()] = [pl.item(i).text() for i in range(pl.count())]
            with open(self.sablon_fajl, "w", encoding="utf-8") as f: json.dump(ad, f, ensure_ascii=False, indent=4)
            dialog.accept()
        sb = QPushButton("💾 SABLON MENTÉSE"); sb.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; height: 35px;")
        sb.clicked.connect(mentes); layout.addWidget(sb); dialog.exec()

    def adatok_beolvasasa(self):
        if not os.path.exists(self.sablon_fajl): return {}
        try:
            with open(self.sablon_fajl, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}

    def sablonok_kezelese(self):
        adatok = self.adatok_beolvasasa()
        if not adatok: return
        dialog = QDialog(self.main); dialog.setWindowTitle("Kezelés"); dialog.setMinimumSize(400, 400)
        l = QVBoxLayout(dialog); lw = QListWidget(); l.addWidget(lw)
        for h, ns in adatok.items():
            for n, ts in ns.items():
                for t in ts.keys():
                    lw.addItem(f"{h} | {n} | {t}"); lw.item(lw.count()-1).setData(Qt.ItemDataRole.UserRole, [h, n, t])
        def tor():
            c = lw.currentItem()
            if not c: return
            h, n, t = c.data(Qt.ItemDataRole.UserRole)
            del adatok[h][n][t]
            if not adatok[h][n]: del adatok[h][n]
            if not adatok[h]: del adatok[h]
            with open(self.sablon_fajl, "w", encoding="utf-8") as f: json.dump(adatok, f, ensure_ascii=False, indent=4)
            lw.takeItem(lw.row(c))
        btn = QPushButton("Törlés"); btn.clicked.connect(tor); l.addWidget(btn); dialog.exec()

    def mentes_aktualis_kijelolt(self):
        item = self.main.right_tree.currentItem()
        if item:
            while item.parent(): item = item.parent()
            if item.data(0, Qt.ItemDataRole.UserRole) == "TURA": self.sablon_mentese(item); return
        QMessageBox.warning(self.main, "Hiba", "Nincs kijelölt túra!")

    def sablon_mentese(self, tura_item):
        het, ok1 = QInputDialog.getItem(self.main, "Mentés", "Hét:", self.het_tipusok, 2, False)
        nap, ok2 = QInputDialog.getItem(self.main, "Mentés", "Nap:", self.napok, 0, False)
        if ok1 and ok2:
            p = [tura_item.child(i).text(0) for i in range(tura_item.childCount())]
            ad = self.adatok_beolvasasa()
            if het not in ad: ad[het] = {}
            if nap not in ad[het]: ad[het][nap] = {}
            ad[het][nap][str(tura_item.text(0))] = p
            with open(self.sablon_fajl, "w", encoding="utf-8") as f: json.dump(ad, f, ensure_ascii=False, indent=4)

    def napi_osszes_betoltese(self, het_pref=None):
        adatok = self.adatok_beolvasasa()
        if not adatok: return
        if het_pref is None:
            het_pref, ok = QInputDialog.getItem(self.main, "Betöltés", "Hét típusa:", list(adatok.keys()), 0, False)
            if not ok: return
        napok_ebben = list(adatok.get(het_pref, {}).keys())
        if not napok_ebben: return
        nap, ok = QInputDialog.getItem(self.main, "Betöltés", "Nap:", sorted(napok_ebben), 0, False)
        if not ok: return
        osszes_sablon = adatok.get(het_pref, {}).get(nap, {}).copy()
        if "Minden héten" in adatok: osszes_sablon.update(adatok["Minden héten"].get(nap, {}))
        for t_nev, p_nevek in osszes_sablon.items():
            talalt = []
            for i in range(self.main.left_tree.topLevelItemCount() - 1, -1, -1):
                lp = self.main.left_tree.topLevelItem(i)
                if lp.text(0) in p_nevek:
                    p_ad = {'n': lp.text(0), 'k': lp.text(3), 'm': lp.text(4), 't': []}
                    for j in range(lp.childCount()):
                        c = lp.child(j); suly = c.text(4) if c.text(4) and c.text(4).strip() else "0"
                        p_ad['t'].append({'n': c.text(1) or c.text(2), 'd': c.text(3), 'k': suly})
                    talalt.append(p_ad); self.main.left_tree.takeTopLevelItem(i)
            if talalt:
                ti = self.main.add_tura_item(t_nev)
                for p in talalt:
                    ex = QTreeWidgetItem(ti, [p['n'], "", "", "", p['k'], p['m'], "", ""])
                    ex.setData(0, Qt.ItemDataRole.UserRole, "PARTNER")
                    for t in p['t']:
                        ki, be = (t['n'], "") if t['n'].startswith("K-") else ("", t['n'])
                        QTreeWidgetItem(ex, ["", ki, be, t['d'], t['k'], "", "", ""])
        if hasattr(self.main, 'recalculate'): self.main.recalculate()
