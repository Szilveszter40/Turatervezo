import os
import json
from PyQt6.QtWidgets import QMessageBox, QTreeWidgetItem
from PyQt6.QtCore import Qt

class ModulInit:
    def __init__(self, main_app):
        self.main = main_app
        if not hasattr(self.main, 'active_modules'):
            self.main.active_modules = []
        if self not in self.main.active_modules:
            self.main.active_modules.append(self)

    def evir_gyors_masolas(self):
        fajlnev = "temp_excel_adatok.json"
        if not os.path.exists(fajlnev):
            QMessageBox.warning(self.main, "Hiba", "Nincs betöltött Excel adat a memóriában!")
            return

        try:
            with open(fajlnev, "r", encoding="utf-8") as f:
                nyers_adatok = json.load(f)

            # 1. Térkép készítése (Túra -> Partnerek)
            terv = {}
            for sor in nyers_adatok:
                t_nev = str(sor.get("Tura", "")).strip()
                p_nev = str(sor.get("PartnerKulcs", "")).strip()
                if t_nev and p_nev:
                    if t_nev not in terv: terv[t_nev] = []
                    if p_nev not in terv[t_nev]: terv[t_nev].append(p_nev)

            # 2. Átrakás a bal oldalról (a főprogram logikájával)
            for t_nev, partner_listaban in terv.items():
                # TÚRA LÉTREHOZÁSA (A főprogram saját függvényével!)
                # Ez rakja rá a ComboBox-okat és a színeket!
                target_tura = self._get_vagy_uj_tura(t_nev)
                
                for i in range(self.main.left_tree.topLevelItemCount() - 1, -1, -1):
                    p_item = self.main.left_tree.topLevelItem(i)
                    if p_item.text(0).strip() in partner_listaban:
                        # KIVESSZÜK balról
                        p = self.main.left_tree.takeTopLevelItem(i)
                        
                        # LÉTREHOZZUK jobbra (Partner: 0:Név, 3:Db, 4:Súly, 5:Megj)
                        uj_p = QTreeWidgetItem(target_tura, [p.text(0), "", "", p.text(2), p.text(3), p.text(4), "", ""])
                        uj_p.setData(0, Qt.ItemDataRole.UserRole, "PARTNER")
                        
                        if hasattr(self.main, 'bold_f'):
                            uj_p.setFont(0, self.main.bold_f)
                        
                        # TÉTELEK áthelyezése
                        while p.childCount() > 0:
                            c = p.takeChild(0)
                            tt = c.text(1)
                            ki, be = (tt, "") if tt.startswith("K-") else ("", tt)
                            QTreeWidgetItem(uj_p, ["", ki, be, c.text(2), c.text(3), "", "", ""])

            # 3. FRISSÍTÉS (Ez élesíti a súlyokat és a gombokat)
            if hasattr(self.main, 'recalculate'):
                self.main.recalculate()
            
            self.main.right_tree.update()
            QMessageBox.information(self.main, "Siker", "Excel túrák összeállítva a jobb panelen!")

        except Exception as e:
            QMessageBox.critical(self.main, "Hiba", f"Hiba az Excel feldolgozáskor: {str(e)}")

    def _get_vagy_uj_tura(self, t_nev):
        for i in range(self.main.right_tree.topLevelItemCount()):
            it = self.main.right_tree.topLevelItem(i)
            if it.text(0).strip() == t_nev: return it
        
        if hasattr(self.main, 'add_tura_item'):
            return self.main.add_tura_item(t_nev)
        return None
