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
        
        # Globális recalculate felülírás a színezéshez (minden modulra hat!)
        if hasattr(self.main, 'recalculate'):
            self.original_recalculate = self.main.recalculate
            self.main.recalculate = self.patched_recalculate

    def patched_recalculate(self):
        """ Ez fut le minden változáskor, így a Fix Túrák színezése is megjavul """
        self.original_recalculate() 
        
        for i in range(self.main.right_tree.topLevelItemCount()):
            t = self.main.right_tree.topLevelItem(i)
            if t.data(0, Qt.ItemDataRole.UserRole) == "TURA":
                try:
                    # Súly kiolvasása és színezése (index 4)
                    s_text = t.text(4).replace(" kg", "").replace(",", ".")
                    suly = float(s_text)
                    
                    if suly > 2000:
                        t.setForeground(4, QColor("red"))
                    else:
                        t.setForeground(4, QColor("black"))
                except:
                    pass

    def evir_gyors_masolas(self):
        fajlnev = "temp_excel_adatok.json"
        if not os.path.exists(fajlnev):
            QMessageBox.warning(self.main, "Hiba", "Nincs betöltött Excel adat!")
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

            for t_n, p_list in terv.items():
                # Ikon beillesztése: 🚛 + Túranév
                ikonos_nev = f"🚛 {t_n}"
                target = self._get_vagy_uj_tura(ikonos_nev)
                target.setExpanded(False)
                
                for i in range(self.main.left_tree.topLevelItemCount() - 1, -1, -1):
                    p_it = self.main.left_tree.topLevelItem(i)
                    if p_it.text(0).strip() in p_list:
                        p = self.main.left_tree.takeTopLevelItem(i)
                        
                        # Partner létrehozása normál stílussal
                        uj_p = QTreeWidgetItem(target, [p.text(0), "", "", p.text(2), p.text(3), p.text(4), "", ""])
                        uj_p.setData(0, Qt.ItemDataRole.UserRole, "PARTNER")
                        
                        while p.childCount() > 0:
                            c = p.takeChild(0)
                            tt = c.text(1)
                            ki, be = (tt, "") if tt.startswith("K-") else ("", tt)
                            QTreeWidgetItem(uj_p, ["", ki, be, c.text(2), c.text(3), "", "", ""])

            self.main.recalculate()
            self.main.right_tree.update()
            QMessageBox.information(self.main, "Siker", "Excel túrák összeállítva!")

        except Exception as e:
            QMessageBox.critical(self.main, "Hiba", str(e))

    def _get_vagy_uj_tura(self, ikonos_nev):
        for i in range(self.main.right_tree.topLevelItemCount()):
            it = self.main.right_tree.topLevelItem(i)
            if it.text(0).strip() == ikonos_nev:
                return it
        
        if hasattr(self.main, 'add_tura_item'):
            return self.main.add_tura_item(ikonos_nev)
        return None
