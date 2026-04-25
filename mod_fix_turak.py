import json
import os
import datetime
from PyQt6.QtWidgets import QPushButton, QMenu, QMessageBox, QInputDialog, QTreeWidgetItem, QHBoxLayout, QAbstractItemView
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
        self.sablon_btn = QPushButton("📋 SABLONOK")
        self.sablon_btn.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        
        menu = QMenu(self.sablon_btn)
        akt_het = self.get_aktualis_het_tipus()
        menu.addAction(f"📂 MAI NAP betöltése ({akt_het})").triggered.connect(lambda: self.napi_osszes_betoltese(akt_het))
        menu.addSeparator()
        menu.addAction("📂 Választás kézzel...").triggered.connect(lambda: self.napi_osszes_betoltese(None))
        menu.addAction("💾 Kijelölt túra mentése sablonként").triggered.connect(self.mentes_aktualis_kijelolt)
        self.sablon_btn.setMenu(menu)

        try:
            if hasattr(self.main, 'a_b'):
                parent_layout = self.main.a_b.parent().layout()
                if parent_layout:
                    parent_layout.insertWidget(0, self.sablon_btn)
        except: pass

    def mentes_aktualis_kijelolt(self):
        item = self.main.right_tree.currentItem()
        if item:
            while item.parent(): item = item.parent()
            if item.data(0, Qt.ItemDataRole.UserRole) == "TURA":
                self.sablon_mentese(item)
                return
        QMessageBox.warning(self.main, "Figyelem", "Jelölj ki egy túrát!")

    def sablon_mentese(self, tura_item):
        het, ok1 = QInputDialog.getItem(self.main, "Mentés", "Hét típusa:", self.het_tipusok, 2, False)
        if not ok1: return
        nap, ok2 = QInputDialog.getItem(self.main, "Mentés", "Melyik nap?", self.napok, 0, False)
        if not ok2: return

        partnerek = [tura_item.child(i).text(0) for i in range(tura_item.childCount())]
        if not partnerek: return

        adatok = self.adatok_beolvasasa()
        if not isinstance(adatok, dict): adatok = {}
        if het not in adatok: adatok[het] = {}
        if nap not in adatok[het]: adatok[het][nap] = {}
        adatok[het][nap][str(tura_item.text(0))] = partnerek
        
        with open(self.sablon_fajl, "w", encoding="utf-8") as f:
            json.dump(adatok, f, ensure_ascii=False, indent=4)
        QMessageBox.information(self.main, "Kész", "Sablon elmentve.")

    def napi_osszes_betoltese(self, het_pref=None):
        adatok = self.adatok_beolvasasa()
        if not adatok: return

        if het_pref is None:
            het_pref, ok = QInputDialog.getItem(self.main, "Betöltés", "Hét típusa:", list(adatok.keys()), 0, False)
            if not ok: return

        napok_ebben = set(adatok.get(het_pref, {}).keys())
        if "Minden héten" in adatok:
            napok_ebben.update(adatok["Minden héten"].keys())
        
        if not napok_ebben: return
        nap_lista = sorted(list(napok_ebben), key=lambda x: self.napok.index(x) if x in self.napok else 99)
        nap, ok = QInputDialog.getItem(self.main, "Betöltés", "Melyik nap?", nap_lista, 0, False)
        if not ok: return

        osszes_sablon = adatok.get(het_pref, {}).get(nap, {}).copy()
        if "Minden héten" in adatok:
            osszes_sablon.update(adatok["Minden héten"].get(nap, {}))

        # --- A JAVÍTÁS LÉNYEGE ---
        for t_nev, partner_nevek in osszes_sablon.items():
            talalt_partnerek = []
            i = self.main.left_tree.topLevelItemCount() - 1
            while i >= 0:
                lp = self.main.left_tree.topLevelItem(i)
                if lp.text(0) in partner_nevek:
                    p_adat = {
                        'nev': lp.text(0), 'kg': lp.text(3), 'megj': lp.text(4),
                        'tetelek': []
                    }
                    for j in range(lp.childCount()):
                        c = lp.child(j)
                        p_adat['tetelek'].append({'n': c.text(1), 'd': c.text(2), 'k': c.text(3)})
                    talalt_partnerek.append(p_adat)
                    self.main.left_tree.takeTopLevelItem(i)
                i -= 1

            if talalt_partnerek:
                t_item = self.main.add_tura_item(t_nev)
                for p in talalt_partnerek:
                    # Partner fejléc - Kényszerített FLAG-ek és UserRole
                    ex = QTreeWidgetItem(t_item, [p['nev'], "", "", "", p['kg'], p['megj'], "", ""])
                    ex.setData(0, Qt.ItemDataRole.UserRole, "PARTNER")
                    ex.setData(0, Qt.ItemDataRole.UserRole + 1, p['megj'])
                    
                    # Beállítjuk, hogy az elem mozgatható (Drag) és fogadható (Drop) legyen
                    ex.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled | 
                                Qt.ItemFlag.ItemIsDropEnabled | Qt.ItemFlag.ItemIsEnabled)
                    
                    for t in p['tetelek']:
                        ki, be = (t['n'], "") if t['n'].startswith("K-") else ("", t['n'])
                        c_item = QTreeWidgetItem(ex, ["", ki, be, t['d'], t['k'], "", "", ""])
                        c_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        
        # Frissítés után újraaktiváljuk a jobb oldali fa belső állapotát
        self.main.recalculate()
        self.main.right_tree.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.main.right_tree.setDragEnabled(True)
        self.main.right_tree.setAcceptDrops(True)

    def adatok_beolvasasa(self):
        if not os.path.exists(self.sablon_fajl): return {}
        try:
            with open(self.sablon_fajl, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
