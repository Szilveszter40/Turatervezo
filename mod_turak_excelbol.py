from PyQt6.QtWidgets import QMessageBox, QTreeWidgetItem
import os

class ModulInit:
    def __init__(self, main_app):
        self.main = main_app
        if not hasattr(self.main, 'active_modules'):
            self.main.active_modules = []
        self.main.active_modules.append(self)

    def excel_fajl_valasztas(self):
        """ 
        Ez a függvény fut le a gombnyomásra. 
        Mivel a neve 'excel_fajl_valasztas', a mod_fix_turak.py meg fogja találni,
        de BELÜL már nincs ablaknyitás!
        """
        
        # 1. Turanevek beolvasása az összehasonlításhoz
        ervenyes_turak = []
        if os.path.exists("Turanevek.txt"):
            try:
                with open("Turanevek.txt", "r", encoding="utf-8") as f:
                    # Kiszedjük az üres sorokat és a felesleges szóközöket
                    ervenyes_turak = [line.strip() for line in f if line.strip()]
            except:
                pass

        # 2. Ellenőrzés: Van-e adat a bal oldalon?
        count = self.main.left_tree.topLevelItemCount()
        if count == 0:
            QMessageBox.warning(self.main, "Hiba", "A bal panel üres! Töltsd be az Excelt!")
            return

        # 3. Adatok feldolgozása
        feldolgozott = 0
        for i in range(count):
            sor = self.main.left_tree.topLevelItem(i)
            
            # KINYERJÜK A TÚRANEVET: 
            # A tervezo_stabil.py az Excel A oszlopát az elem adat-tárolójába menti (Qt.ItemDataRole.UserRole = 32)
            t_nev_excel = sor.data(0, 32) 
            
            # Ha a UserRole üres, megpróbáljuk a szöveget (hátha ott van elrejtve)
            if not t_nev_excel:
                t_nev_excel = sor.text(0).strip()

            # Ellenőrizzük, hogy a kinyert név benne van-e a Turanevek.txt-ben
            if t_nev_excel in ervenyes_turak:
                
                # Megkeressük/Létrehozzuk a túra-fejlécet a JOBB oldalon
                jobb_tura = None
                for j in range(self.main.right_tree.topLevelItemCount()):
                    if self.main.right_tree.topLevelItem(j).text(0) == t_nev_excel:
                        jobb_tura = self.main.right_tree.topLevelItem(j)
                        break
                
                if not jobb_tura:
                    jobb_tura = QTreeWidgetItem([t_nev_excel])
                    self.main.right_tree.addTopLevelItem(jobb_tura)

                # ADATOK ÁTMÁSOLÁSA (Oszlopok: 0=Partner/Cím, 1=Tétel, 2=Db, 3=Kg, 4=Megjegyzés)
                p_nev_cim = sor.text(0)
                tetel     = sor.text(1)
                darab     = sor.text(2)
                suly      = sor.text(3)
                megj      = sor.text(4)

                # KI / BE logika (K- kezdetű tétel a KI oszlopba megy)
                ki_oszlop, be_oszlop = "", ""
                if tetel.upper().startswith("K-"):
                    ki_oszlop = tetel
                else:
                    be_oszlop = tetel

                # ÚJ SOR A JOBB PANELRE: 
                # 0=Partner/Cím, 1=KI, 2=Be, 3=Db, 4=Kg, 5=Megjegyzés, 6=Rendszám, 7=Sofőr
                uj_sor = QTreeWidgetItem([
                    p_nev_cim, ki_oszlop, be_oszlop, darab, suly, megj, "", ""
                ])
                
                jobb_tura.addChild(uj_sor)
                self.main.right_tree.expandItem(jobb_tura)
                feldolgozott += 1

        if feldolgozott > 0:
            QMessageBox.information(self.main, "Kész", f"Sikeresen átmásolva: {feldolgozott} tétel.")
        else:
            QMessageBox.warning(self.main, "Figyelem", "Nem történt másolás. Lehet, hogy a túranevek nem egyeznek a Turanevek.txt tartalmával.")
