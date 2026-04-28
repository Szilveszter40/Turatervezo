import os
import json
import re
from PyQt6.QtWidgets import QMessageBox, QTreeWidgetItem
from PyQt6.QtGui import QFont
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
            QMessageBox.warning(self.main, "Hiba", "Nincs adat! Töltsd be az Excelt a bal panelen.")
            return

        ervenyes_turak = []
        if os.path.exists("Turanevek.txt"):
            with open("Turanevek.txt", "r", encoding="utf-8") as f:
                ervenyes_turak = [line.strip() for line in f if line.strip()]

        try:
            with open(fajlnev, "r", encoding="utf-8") as f:
                nyers_adatok = json.load(f)

            # 1. ADATOK CSOPORTOSÍTÁSA
            feldolgozott = {}
            for sor in nyers_adatok:
                t_nev = sor.get("Tura", "ISMERETLEN")
                if t_nev not in ervenyes_turak: continue

                p_teljes = sor.get("PartnerKulcs", "Ismeretlen")
                cim_match = re.search(r'\((.*?)\)', p_teljes)
                p_cim = cim_match.group(1) if cim_match else p_teljes

                tetel_nev = sor.get("Tetel", "ISMERETLEN")
                megj_szoveg = str(sor.get("Megj", "")).strip()
                
                if t_nev not in feldolgozott: feldolgozott[t_nev] = {}
                if p_cim not in feldolgozott[t_nev]:
                    feldolgozott[t_nev][p_cim] = {'tetelek': {}, 'partner_megj': set()}
                
                if tetel_nev not in feldolgozott[t_nev][p_cim]['tetelek']:
                    feldolgozott[t_nev][p_cim]['tetelek'][tetel_nev] = {'db': 0.0, 'kg': 0.0}

                # Összesítés a tételen belül
                d = feldolgozott[t_nev][p_cim]['tetelek'][tetel_nev]
                d['db'] += float(sor.get("Db", 0) or 0)
                d['kg'] += float(sor.get("Kg", 0) or 0)
                
                # Megjegyzés gyűjtése csak a partner szintjére
                if megj_szoveg and megj_szoveg.lower() != "nan" and megj_szoveg != "":
                    feldolgozott[t_nev][p_cim]['partner_megj'].add(megj_szoveg)

            # 2. MEGJELENÍTÉS
            font_bold = QFont(); font_bold.setBold(True)
            self.main.right_tree.collapseAll()

            for t_nev, partnerek in feldolgozott.items():
                t_ossz_kg = sum(sum(t['kg'] for t in p['tetelek'].values()) for p in partnerek.values())

                # I. SZINT: TÚRA
                jobb_tura = self._get_or_create_tura(t_nev)
                jobb_tura.setText(4, f"{t_ossz_kg:,.1f} kg")
                for col in range(8): jobb_tura.setFont(col, font_bold)

                for p_cim, p_adat in partnerek.items():
                    p_ossz_kg = sum(t['kg'] for t in p_adat['tetelek'].values())
                    p_megj_ossz = " | ".join(p_adat['partner_megj'])
                    
                    # II. SZINT: PARTNER (Megjegyzés itt jelenik meg)
                    uj_partner = QTreeWidgetItem(jobb_tura)
                    uj_partner.setText(0, p_cim)
                    uj_partner.setText(4, f"{p_ossz_kg:,.1f}")
                    uj_partner.setText(5, p_megj_ossz) 
                    uj_partner.setToolTip(5, p_megj_ossz)

                    # III. SZINT: TÉTELEK (Megjegyzés oszlop üresen marad)
                    for t_nev, t_adat in p_adat['tetelek'].items():
                        ki, be = ("", t_nev) if not t_nev.upper().startswith("K-") else (t_nev, "")
                        
                        tetel_elem = QTreeWidgetItem(uj_partner)
                        tetel_elem.setText(1, ki)
                        tetel_elem.setText(2, be)
                        tetel_elem.setText(3, str(int(t_adat['db'])))
                        tetel_elem.setText(4, f"{t_adat['kg']:,.1f}")
                        tetel_elem.setText(5, "") # TÉTELEKNÉL ÜRES A MEGJEGYZÉS
                        
                        for col in range(1, 5):
                            tetel_elem.setTextAlignment(col, Qt.AlignmentFlag.AlignCenter)

                self.main.right_tree.collapseItem(jobb_tura)

            QMessageBox.information(self.main, "Kész", "Importálás sikeres, a megjegyzések a partnerekhez rendelve.")

        except Exception as e:
            QMessageBox.critical(self.main, "Hiba", f"Hiba: {e}")

    def _get_or_create_tura(self, nev):
        for i in range(self.main.right_tree.topLevelItemCount()):
            if self.main.right_tree.topLevelItem(i).text(0).strip() == nev:
                return self.main.right_tree.topLevelItem(i)
        item = QTreeWidgetItem(self.main.right_tree)
        item.setText(0, nev)
        return item
