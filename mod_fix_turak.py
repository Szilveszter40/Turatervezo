import json
import os
import datetime
from PyQt6.QtWidgets import (QPushButton, QMenu, QMessageBox, QInputDialog, 
                             QTreeWidgetItem, QVBoxLayout, QHBoxLayout, QWidget, 
                             QDialog, QListWidget, QSizePolicy, QLabel)
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
        self.takaritas()
        self.main.gomb_sor_kontener = QWidget()
        layout = QHBoxLayout(self.main.gomb_sor_kontener)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # --- SABLON GOMB ---
        self.main.fix_tura_btn_obj = QPushButton("📋 SABLONOK KEZELÉSE")
        self.main.fix_tura_btn_obj.setStyleSheet("background-color: #607D8B; color: white; font-weight: bold; padding: 6px; border-radius: 3px;")
        self.main.fix_tura_btn_obj.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.menu = QMenu(self.main.fix_tura_btn_obj)
        self.menu.addAction("📅 Visszakeresés").triggered.connect(self.kezi_valasztas_ablak)
        self.menu.addAction("💾 Mentés sablonként").triggered.connect(self.mentes_aktualis_kijelolt)
        self.menu.addAction("📂 Sablonok kezelése / Törlés").triggered.connect(self.sablon_kezelo_ablak)
        self.main.fix_tura_btn_obj.setMenu(self.menu)

        # --- HOLNAP GOMB ---
        self.main.holnap_btn_obj = QPushButton("🚚 HOLNAPI TÚRÁK SABLONBÓL")
        self.main.holnap_btn_obj.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; padding: 6px; border-radius: 3px;")
        self.main.holnap_btn_obj.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.main.holnap_btn_obj.clicked.connect(self.holnapi_inditas_fix)

        self.excel_btn = QPushButton("📊 HOLNAPI TÚRÁK EVIR-BŐL")
        self.excel_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 6px; border-radius: 4px;")
        self.excel_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.excel_btn.clicked.connect(self.excel_import_hivas)

        # --- TÉRKÉP GOMB ---
        if hasattr(self.main, 'terkep_btn_obj'):
            self.terkep_btn = self.main.terkep_btn_obj
        else:
            self.terkep_btn = QPushButton("🗺️ TÉRKÉP")
            self.terkep_btn.setStyleSheet("background-color: #1a5276; color: white; font-weight: bold; padding: 6px; border-radius: 3px;")
            self.main.terkep_btn_obj = self.terkep_btn
        
        self.terkep_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout.addWidget(self.main.fix_tura_btn_obj, 1)
        layout.addWidget(self.main.holnap_btn_obj, 1)
        layout.addWidget(self.excel_btn, 1)
        layout.addWidget(self.terkep_btn, 1)

        try:
            target = self.main.right_tree.parent().layout()
            target.insertWidget(1, self.main.gomb_sor_kontener)
        except: pass

    def suly_ellenorzes(self):
        """Késleltetett színezés a Recalculate felülbírálása ellen"""
        if not hasattr(self.main, 'right_tree'): return
        QTimer.singleShot(300, self._vegrehajt_szinezes)

    def _vegrehajt_szinezes(self):
        self.main.right_tree.blockSignals(True)
        bold_f = QFont(); bold_f.setBold(True)
        
        for i in range(self.main.right_tree.topLevelItemCount()):
            it = self.main.right_tree.topLevelItem(i)
            if it.data(0, Qt.ItemDataRole.UserRole) == "TURA":
                try:
                    # Szöveg tisztítása és szám kinyerése
                    txt = it.text(4).replace(" kg", "").replace(" ", "").replace(",", ".").strip()
                    if not txt: continue
                    suly = float(txt)
                    
                    it.setFont(4, bold_f)
                    
                    if suly >= 2000:
                        # Erőteljes kiemelés: piros háttér, fehér szöveg
                        it.setBackground(4, QColor("#e74c3c"))
                        it.setForeground(4, QColor("white"))
                    else:
                        # Visszaállítás alaphelyzetbe
                        it.setBackground(4, QColor("transparent"))
                        it.setForeground(4, QColor("black"))
                except:
                    pass
        
        self.main.right_tree.blockSignals(False)
        self.main.right_tree.viewport().update()

    def holnapi_inditas_fix(self):
        try:
            holnap = datetime.datetime.now() + datetime.timedelta(days=1)
            napok = ["Hétfő", "Kedd", "Szerda", "Csütörtök", "Péntek", "Szombat", "Vasárnap"]
            h_nap = napok[holnap.weekday()]
            # Hét típusa számítás
            het_sorszam = holnap.isocalendar()[1]
            h_het = "Páros hét" if het_sorszam % 2 == 0 else "Páratlan hét"
            self.napi_osszes_betoltese(h_het, h_nap)
        except Exception as e:
            print(f"Hiba a dátumnál: {e}")

    def napi_osszes_betoltese(self, het_pref, nap_pref):
        if not os.path.exists(self.sablon_utvonal): return
        try:
            with open(self.sablon_utvonal, "r", encoding="utf-8") as f:
                ad = json.load(f)
        except: return

        t_terv = ad.get(het_pref, {}).get(nap_pref, {}).copy()
        if "Minden héten" in ad:
            t_terv.update(ad["Minden héten"].get(nap_pref, {}))
        
        if not t_terv:
            QMessageBox.information(self.main, "Infó", f"Nincs mentett túra: {nap_pref}")
            return

        self.main.right_tree.blockSignals(True)
        try:
            bal_oldal = {self.main.left_tree.topLevelItem(i).text(0).split('(')[0].strip().upper(): self.main.left_tree.topLevelItem(i) 
                         for i in range(self.main.left_tree.topLevelItemCount())}
            
            atmozgatott = 0
            for t_nev, p_nevek in t_terv.items():
                if t_nev == "_mentve": continue
                ti = self.main.add_tura_item(f"🚛 {t_nev}")
                ti.setData(0, Qt.ItemDataRole.UserRole, "TURA")
                
                for p_mentett in p_nevek:
                    p_clean = p_mentett.split('(')[0].strip().upper()
                    if p_clean in bal_oldal:
                        lp = bal_oldal[p_clean]
                        uj_p = QTreeWidgetItem(ti)
                        uj_p.setText(0, lp.text(0))
                        uj_p.setText(3, lp.text(2)) # Darab
                        uj_p.setText(4, lp.text(3)) # Kg
                        uj_p.setData(0, Qt.ItemDataRole.UserRole, "PARTNER")
                        
                        for k in range(lp.childCount()):
                            c_old = lp.child(k)
                            c_uj = QTreeWidgetItem(uj_p)
                            t_n = c_old.text(1)
                            if t_n.startswith("K-"): c_uj.setText(1, t_n)
                            else: c_uj.setText(2, t_n)
                            c_uj.setText(3, c_old.text(2))
                            c_uj.setText(4, c_old.text(3))
                        
                        idx = self.main.left_tree.indexOfTopLevelItem(lp)
                        if idx != -1: self.main.left_tree.takeTopLevelItem(idx)
                        atmozgatott += 1
            
            if hasattr(self.main, 'recalculate'):
                self.main.recalculate()
        finally:
            self.main.right_tree.blockSignals(False)
            self.suly_ellenorzes()

    def kezi_valasztas_ablak(self):
        if not os.path.exists(self.sablon_utvonal): return
        try:
            with open(self.sablon_utvonal, "r", encoding="utf-8") as f:
                ad = json.load(f)
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
        except: pass

    def mentes_aktualis_kijelolt(self):
        it = self.main.right_tree.currentItem()
        if not it: return
        while it.parent(): it = it.parent()
        if it.data(0, Qt.ItemDataRole.UserRole) == "TURA":
            h, ok1 = QInputDialog.getItem(self.main, "Mentés", "Hét:", ["Páros hét", "Páratlan hét", "Minden héten"], 2, False)
            n, ok2 = QInputDialog.getItem(self.main, "Mentés", "Nap:", ["Hétfő", "Kedd", "Szerda", "Csütörtök", "Péntek", "Szombat", "Vasárnap"], 0, False)
            if ok1 and ok2:
                try:
                    ad = {}
                    if os.path.exists(self.sablon_utvonal):
                        with open(self.sablon_utvonal, "r", encoding="utf-8") as f: ad = json.load(f)
                    t_n = it.text(0).replace("🚛 ", "")
                    if h not in ad: ad[h] = {}
                    if n not in ad[h]: ad[h][n] = {}
                    ad[h][n][t_n] = [it.child(i).text(0) for i in range(it.childCount())]
                    with open(self.sablon_utvonal, "w", encoding="utf-8") as f:
                        json.dump(ad, f, indent=4, ensure_ascii=False)
                    QMessageBox.information(self.main, "Siker", "Mentve.")
                except: pass

    def sablon_kezelo_ablak(self):
        # Új ablak a sablonok listázásához
        self.kezelo_dialog = QDialog(self.main)
        self.kezelo_dialog.setWindowTitle("Mentett Sablonok Karbantartása")
        self.kezelo_dialog.setMinimumSize(400, 500)
        layout = QVBoxLayout(self.kezelo_dialog)

        layout.addWidget(QLabel("<b>Összes mentett sablon:</b>"))
        
        self.sablon_lista_widget = QListWidget()
        self.sablon_lista_frissites() # Lista feltöltése a JSON-ből
        layout.addWidget(self.sablon_lista_widget)

        # Törlés gomb
        btn_torles = QPushButton("🗑️ Kijelölt sablon végleges törlése")
        btn_torles.setFixedHeight(40)
        btn_torles.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold; border-radius: 4px;")
        btn_torles.clicked.connect(self.sablon_torles_vegrehajtas)
        layout.addWidget(btn_torles)

        self.kezelo_dialog.exec()

    def sablon_lista_frissites(self):
        self.sablon_lista_widget.clear()
        json_fajl = "fix_turak_napi.json"
        
        if os.path.exists(json_fajl):
            try:
                with open(json_fajl, "r", encoding="utf-8") as f:
                    adatok = json.load(f)
                    
                    # 1. szint: Hét (pl. Páros hét)
                    for het, napok in adatok.items():
                        if isinstance(napok, dict):
                            # 2. szint: Nap (pl. Hétfő)
                            for nap, turak in napok.items():
                                if isinstance(turak, dict):
                                    # 3. szint: A konkrét Túrák nevei
                                    for tura_neve in turak.keys():
                                        self.sablon_lista_widget.addItem(f"{het} -> {nap} -> {tura_neve}")
                                else:
                                    # Ha a nap alatt rögtön adatok vannak (nem több túra)
                                    self.sablon_lista_widget.addItem(f"{het} -> {nap}")
            except Exception as e:
                print(f"Hiba a listázáskor: {e}")

    def sablon_torles_vegrehajtas(self):
        item = self.sablon_lista_widget.currentItem()
        if not item: return
        
        szoveg = item.text()
        parts = szoveg.split(" -> ")
        
        valasz = QMessageBox.question(self.kezelo_dialog, "Megerősítés", f"Törlöd a következőt?\n{szoveg}")
        if valasz != QMessageBox.StandardButton.Yes: return

        try:
            json_fajl = "fix_turak_napi.json"
            with open(json_fajl, "r", encoding="utf-8") as f:
                adatok = json.load(f)

            if len(parts) == 3: # Hét -> Nap -> Túra forma
                het, nap, tura = parts
                if het in adatok and nap in adatok[het] and tura in adatok[het][nap]:
                    del adatok[het][nap][tura]
                    
                    # Takarítás: ha üres lett a nap vagy a hét
                    if not adatok[het][nap]: del adatok[het][nap]
                    if not adatok[het]: del adatok[het]

            elif len(parts) == 2: # Csak Hét -> Nap forma
                het, nap = parts
                if het in adatok and nap in adatok[het]:
                    del adatok[het][nap]
                    if not adatok[het]: del adatok[het]

            with open(json_fajl, "w", encoding="utf-8") as f:
                json.dump(adatok, f, ensure_ascii=False, indent=4)
            
            self.sablon_lista_frissites()
            QMessageBox.information(self.kezelo_dialog, "Siker", "Törölve.")
        except Exception as e:
            QMessageBox.critical(self.main, "Hiba", f"Hiba: {e}")

    
    def auto_mentes_esemeny(self, item, column):
        if self.main.right_tree.signalsBlocked(): return
        if hasattr(self.main, 'recalculate'):
            self.main.right_tree.blockSignals(True)
            try: self.main.recalculate()
            finally: self.main.right_tree.blockSignals(False)
            self.suly_ellenorzes()

    def excel_import_hivas(self):
        # Teljesen új nevet keresünk, hogy véletlenül se a régi ablaknyitóst hívja meg
        modul_megvan = False
        for m in self.main.active_modules:
            if hasattr(m, 'evir_gyors_masolas'): # <--- ÚJ NÉV
                m.evir_gyors_masolas()           # <--- ÚJ NÉV
                modul_megvan = True
                break
    
        if not modul_megvan:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self.main, "Hiba", "Az Excel modul (evir_gyors_masolas) nem található!")
