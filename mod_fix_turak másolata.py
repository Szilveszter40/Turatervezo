import json
import os
import datetime
from PyQt6.QtWidgets import (QPushButton, QMenu, QMessageBox, QInputDialog, 
                             QTreeWidgetItem, QVBoxLayout, QHBoxLayout, 
                             QDialog, QListWidget, QLabel)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont

class ModulInit:
    def __init__(self, main_app):
        self.main = main_app
        self.sablon_fajl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fix_turak_napi.json")
        self.napok = ["Hétfő", "Kedd", "Szerda", "Csütörtök", "Péntek", "Szombat", "Vasárnap"]
        self.het_tipusok = ["Páros hét", "Páratlan hét", "Minden héten"]
        
        # Rövid várakozás az inicializáláshoz
        QTimer.singleShot(500, self.init_gomb)
        
        if hasattr(self.main, 'right_tree'):
            self.main.right_tree.itemChanged.connect(self.auto_mentes_esemeny)

    def init_gomb(self):
        if hasattr(self.main, 'fix_tura_btn_obj'):
            return

        # Gomb létrehozása narancssárga stílussal (hogy látványos legyen a jobb felsőben)
        self.main.fix_tura_btn_obj = QPushButton("📋 SABLONOK")
        self.main.fix_tura_btn_obj.setStyleSheet("""
            QPushButton {
                background-color: #f39c12; 
                color: white; 
                font-weight: bold; 
                padding: 8px; 
                border-radius: 4px;
                margin-bottom: 2px;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)

        # Elhelyezés a JOBB OLDALI PANEL tetején
        try:
            if hasattr(self.main, 'right_tree'):
                # Megkeressük a jobb oldali fa szülőjének layoutját
                jobb_panel_layout = self.main.right_tree.parent().layout()
                if jobb_panel_layout:
                    # A 0. indexre szúrjuk be, így minden felett, a jobb felső részen lesz
                    jobb_panel_layout.insertWidget(1, self.main.fix_tura_btn_obj)
        except Exception as e:
            print(f"Sablon gomb elhelyezési hiba: {e}")

        # Menü felépítése
        uj_menu = QMenu(self.main.fix_tura_btn_obj)
        h_het, h_nap = self.get_holnapi_adatok()
        
        uj_menu.addAction(f"🚚 HOLNAPI NAP ({h_nap})").triggered.connect(lambda: self.napi_osszes_betoltese(h_het, h_nap))
        uj_menu.addSeparator()
        uj_menu.addAction("📅 VISSZAKERESÉS DÁTUM SZERINT").triggered.connect(self.kezi_valasztas_ablak)
        uj_menu.addAction("💾 Kijelölt mentése sablonként").triggered.connect(self.mentes_aktualis_kijelolt)
        uj_menu.addSeparator()
        uj_menu.addAction("🗑️ MENTETT TÚRÁK (Törlés)").triggered.connect(self.sablonok_kezelese)
        self.main.fix_tura_btn_obj.setMenu(uj_menu)

    def get_holnapi_adatok(self):
        holnap = datetime.datetime.now() + datetime.timedelta(days=1)
        het_szam = holnap.isocalendar()[1]
        het_tipus = "Páros hét" if het_szam % 2 == 0 else "Páratlan hét"
        nap_hu = {"Monday": "Hétfő", "Tuesday": "Kedd", "Wednesday": "Szerda", "Thursday": "Csütörtök", "Friday": "Péntek", "Saturday": "Szombat", "Sunday": "Vasárnap"}
        return het_tipus, nap_hu.get(holnap.strftime("%A"), "Hétfő")

    def suly_ellenorzes(self):
        if not hasattr(self.main, 'right_tree'):
            return
        for i in range(self.main.right_tree.topLevelItemCount()):
            it = self.main.right_tree.topLevelItem(i)
            if it.data(0, Qt.ItemDataRole.UserRole) == "TURA":
                try:
                    s_txt = it.text(4).replace(" kg", "").replace(",", ".").strip()
                    s = float(s_txt) if s_txt else 0.0
                    # Csak a súly oszlop (4-es index) legyen piros, ha > 2000
                    it.setForeground(4, QColor("red") if s > 2000 else QColor("black"))
                    f = QFont()
                    if s > 2000:
                        f.setBold(True)
                    it.setFont(4, f)
                except:
                    pass

    def kezi_valasztas_ablak(self):
        ad = self.adatok_beolvasasa()
        if not ad:
            return
        dialog = QDialog(self.main)
        dialog.setWindowTitle("Visszakeresés dátum szerint")
        dialog.setMinimumSize(400, 450)
        layout = QVBoxLayout(dialog)
        lista = QListWidget()
        
        bejegyzések = []
        for het, napok in ad.items():
            if isinstance(napok, dict):
                for nap, adatok in napok.items():
                    datum = adatok.get("_mentve", "Régi adat") if isinstance(adatok, dict) else "Régi adat"
                    bejegyzések.append((datum, het, nap))
        
        for d, h, n in sorted(bejegyzések, reverse=True):
            lista.addItem(f"{d} | {h} - {n}")
            lista.item(lista.count()-1).setData(Qt.ItemDataRole.UserRole, [h, n])

        layout.addWidget(lista)
        def betolt():
            if lista.currentItem():
                h, n = lista.currentItem().data(Qt.ItemDataRole.UserRole)
                dialog.accept()
                self.napi_osszes_betoltese(h, n)
        
        b = QPushButton("Kiválasztott nap betöltése")
        b.clicked.connect(betolt)
        layout.addWidget(b)
        dialog.exec()

    def mentes_aktualis_kijelolt(self):
        it = self.main.right_tree.currentItem()
        if it:
            while it.parent():
                it = it.parent()
            if it.data(0, Qt.ItemDataRole.UserRole) == "TURA":
                h, ok1 = QInputDialog.getItem(self.main, "Mentés", "Hét típusa:", self.het_tipusok, 2, False)
                n, ok2 = QInputDialog.getItem(self.main, "Mentés", "Melyik nap?", self.napok, 0, False)
                if ok1 and ok2:
                    adat = self.adatok_beolvasasa()
                    if h not in adat:
                        adat[h] = {}
                    if n not in adat[h]:
                        adat[h][n] = {"_mentve": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
                    adat[h][n][it.text(0)] = [it.child(i).text(0) for i in range(it.childCount())]
                    with open(self.sablon_fajl, "w", encoding="utf-8") as f:
                        json.dump(adat, f, ensure_ascii=False, indent=4)
                    QMessageBox.information(self.main, "Siker", "Mentve az archívumba.")
                return
        QMessageBox.warning(self.main, "Hiba", "Jelölj ki egy túrát a mentéshez!")

    def napi_osszes_betoltese(self, het_pref, nap_pref):
        ad = self.adatok_beolvasasa()
        t_terv = ad.get(het_pref, {}).get(nap_pref, {}).copy()
        if "Minden héten" in ad:
            if nap_pref in ad["Minden héten"]:
                t_terv.update(ad["Minden héten"][nap_pref])
        
        elerheto = {self.main.left_tree.topLevelItem(i).text(0): i for i in range(self.main.left_tree.topLevelItemCount())}
        torlendo = []
        
        for t_nev, p_nevek in t_terv.items():
            if t_nev == "_mentve":
                continue
            v_partnerek = [p for p in p_nevek if p in elerheto]
            if v_partnerek:
                ti = self.main.add_tura_item(t_nev)
                for p_nev in v_partnerek:
                    lp = self.main.left_tree.topLevelItem(elerheto[p_nev])
                    ex = QTreeWidgetItem(ti, [lp.text(0), "", "", "", lp.text(3), lp.text(4), "", ""])
                    ex.setData(0, Qt.ItemDataRole.UserRole, "PARTNER")
                    for j in range(lp.childCount()):
                        c = lp.child(j)
                        ki, be = (c.text(1), "") if c.text(1).startswith("K-") else ("", c.text(1))
                        QTreeWidgetItem(ex, ["", ki, be, c.text(2), c.text(3), "", "", ""])
                    torlendo.append(elerheto[p_nev])

        for idx in sorted(list(set(torlendo)), reverse=True):
            self.main.left_tree.takeTopLevelItem(idx)
            
        if hasattr(self.main, 'recalculate'):
            self.main.recalculate()
            self.suly_ellenorzes()

    def auto_mentes_esemeny(self, item, column):
        if hasattr(self.main, 'recalculate'):
            self.main.recalculate()
            self.suly_ellenorzes()
        top = item
        while top.parent():
            top = top.parent()
        if top.data(0, Qt.ItemDataRole.UserRole) == "TURA":
            ad = self.adatok_beolvasasa()
            for h in ad:
                for n in ad[h]:
                    if isinstance(ad[h][n], dict) and top.text(0) in ad[h][n]:
                        ad[h][n][top.text(0)] = [top.child(i).text(0) for i in range(top.childCount())]
                        with open(self.sablon_fajl, "w", encoding="utf-8") as f:
                            json.dump(ad, f, ensure_ascii=False, indent=4)

    def adatok_beolvasasa(self):
        if not os.path.exists(self.sablon_fajl):
            return {}
        try:
            with open(self.sablon_fajl, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}

    def sablonok_kezelese(self):
        ad = self.adatok_beolvasasa()
        if not ad:
            return
        d = QDialog(self.main)
        d.setWindowTitle("Kezelés")
        d.setMinimumSize(400, 400)
        l = QVBoxLayout(d)
        lw = QListWidget()
        l.addWidget(lw)
        for h, ns in ad.items():
            for n, ts in ns.items():
                if isinstance(ts, dict):
                    for t in ts.keys():
                        if t != "_mentve":
                            lw.addItem(f"{h} | {n} | {t}")
                            lw.item(lw.count()-1).setData(Qt.ItemDataRole.UserRole, [h, n, t])
        def tor():
            c = lw.currentItem()
            if not c:
                return
            h, n, t = c.data(Qt.ItemDataRole.UserRole)
            if h in ad and n in ad[h] and t in ad[h][n]:
                del ad[h][n][t]
                with open(self.sablon_fajl, "w", encoding="utf-8") as f:
                    json.dump(ad, f, ensure_ascii=False, indent=4)
                lw.takeItem(lw.row(c))
        
        btn = QPushButton("Törlés")
        btn.clicked.connect(tor)
        l.addWidget(btn)
        d.exec()
