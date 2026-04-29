import os
import json
from PyQt6.QtWidgets import QMessageBox, QTreeWidgetItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

class ModulInit:
    def __init__(self, main_app):
        self.main = main_app
        if not hasattr(self.main, 'active_modules'):
            self.main.active_modules = []
        if self not in self.main.active_modules:
            self.main.active_modules.append(self)
        
        # --- GLOBÁLIS OKOSÍTÁSOK ---
        if hasattr(self.main, 'recalculate'):
            self.original_recalculate = self.main.recalculate
            self.main.recalculate = self.patched_recalculate

        # Felülírjuk az add_tura_item-et is, hogy az Új Túra gombnál is legyen ikon
        if hasattr(self.main, 'add_tura_item'):
            self.original_add_item = self.main.add_tura_item
            self.main.add_tura_item = self.patched_add_item

    def patched_add_item(self, nev):
        """ Ez a függvény gondoskodik róla, hogy minden kézzel létrehozott túra is megkapja az ikont """
        ikon = "🚛 "
        if not nev.startswith(ikon):
            nev = f"{ikon}{nev}"
        return self.original_add_item(nev)

    def patched_recalculate(self):
        """ Folyamatos színezés 2000 kg felett """
        self.original_recalculate() 
        for i in range(self.main.right_tree.topLevelItemCount()):
            t = self.main.right_tree.topLevelItem(i)
            if t.data(0, Qt.ItemDataRole.UserRole) == "TURA":
                try:
                    s_text = t.text(4).replace(" kg", "").replace(",", ".")
                    suly = float(s_text)
                    t.setForeground(4, QColor("red") if suly > 2000 else QColor("black"))
                except:
                    pass

    def evir_gyors_masolas(self):
        fajlnev = "temp_excel_adatok.json"
        if not os.path.exists(fajlnev):
            return

        try:
            with open(fajlnev, "r", encoding="utf-8") as f:
                nyers_adatok = json.load(f)

            terv = {}
            for sor in nyers_adatok:
                t_n = str(sor.get("Tura", "")).strip()
                p_n = str(sor.get("PartnerKulcs", "")).strip()
                if t_n and p_n:
                    if t_n not in terv: terv[t_n] = []
                    if p_n not in terv[t_n]: terv[t_n].append(p_n)

            kihagyott = 0
            for t_n, p_list in terv.items():
                # Szűrés a Túrázandó partnerekre
                check_name = t_n.lower().replace("á", "a").replace("ó", "o").replace("ú", "u")
                if "turazando" in check_name or "turan" in check_name:
                    kihagyott += len(p_list)
                    continue 

                # Itt már a patched_add_item-et fogja hívni a _get_vagy_uj_tura, 
                # így az ikon garantált!
                target = self._get_vagy_uj_tura(t_n)
                target.setExpanded(False)
                
                for i in range(self.main.left_tree.topLevelItemCount() - 1, -1, -1):
                    p_it = self.main.left_tree.topLevelItem(i)
                    if p_it.text(0).strip() in p_list:
                        p = self.main.left_tree.takeTopLevelItem(i)
                        megj = p.text(4) 
                        uj_p = QTreeWidgetItem(target, [p.text(0), "", "", p.text(2), p.text(3), megj, "", ""])
                        uj_p.setData(0, Qt.ItemDataRole.UserRole, "PARTNER")
                        uj_p.setData(0, Qt.ItemDataRole.UserRole + 1, megj)
                        while p.childCount() > 0:
                            c = p.takeChild(0)
                            tt = c.text(1)
                            ki, be = (tt, "") if tt.startswith("K-") else ("", tt)
                            QTreeWidgetItem(uj_p, ["", ki, be, c.text(2), c.text(3), "", "", ""])

            self.main.recalculate()
            self.main.right_tree.update()
            QMessageBox.information(self.main, "Siker", "Excel túrák kész!")

        except Exception as e:
            QMessageBox.critical(self.main, "Hiba", str(e))

    def _get_vagy_uj_tura(self, t_n):
        # Keressük az ikonos nevet
        ikonos = f"🚛 {t_n}"
        for i in range(self.main.right_tree.topLevelItemCount()):
            it = self.main.right_tree.topLevelItem(i)
            # Megnézzük ikonnal és ikon nélkül is az egyezést
            if it.text(0).strip() in [t_n, ikonos]: 
                return it
        # Ha nem találjuk, létrehozzuk (a patched_add_item teszi rá az ikont)
        return self.main.add_tura_item(t_n)
