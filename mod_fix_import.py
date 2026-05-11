import pandas as pd
import json
import re
from PyQt6.QtWidgets import QTreeWidgetItem

class FixImportMotor:
    @staticmethod
    def tisztit_es_vag(text):
        """Levágja a címet a házszám után és megjegyzésbe teszi a többit."""
        t = str(text).replace('\r', ' ').replace('\n', ' ').strip()
        # Regex a HU irányítószám + Város + Utca + Házszám mintára
        match = re.search(r'(HU\s+\d{4}\s+[^,]+,[^0-9]+\d+[^\s]*)', t)
        if match:
            cim = match.group(1).strip()
            megj = t.replace(cim, "").strip(" ,/-")
            return cim, megj
        return t, ""

    @staticmethod
    def importalas_es_megjelenites(parent_window, fajl_utvonal):
        try:
            df = pd.read_excel(fajl_utvonal)
            parent_window.left_tree.clear()

            # 7. oszlop: Túra neve
            turak = df.iloc[:, 7].unique()
            
            for t_nev in turak:
                t_nev_str = str(t_nev) if pd.notnull(t_nev) and str(t_nev).strip() != "" else "TÚRA NÉLKÜL"
                
                # 1. SZÜLŐ: Túra (ZÁRVA)
                tura_item = QTreeWidgetItem(parent_window.left_tree)
                tura_item.setText(0, t_nev_str)
                t_suly = df[df.iloc[:, 7] == t_nev].iloc[:, 0].sum()
                tura_item.setText(3, f"{t_suly:.1f}")
                tura_item.setExpanded(False) 

                p_df = df[df.iloc[:, 7] == t_nev]
                
                for _, row in p_df.iterrows():
                    # 2. GYEREK: Partner (4. oszlop)
                    nyers_p_adat = str(row.iloc[4])
                    cim_tisztitott, extra_megj = FixImportMotor.tisztit_es_vag(nyers_p_adat)
                    
                    partner_item = QTreeWidgetItem(tura_item)
                    partner_item.setText(0, cim_tisztitott.replace('\n', ' ')) # Egy sorba kényszerítve
                    partner_item.setText(3, str(row.iloc[0])) # 0. oszlop: Összesített súly
                    partner_item.setText(4, extra_megj)       # Megjegyzés oszlop
                    
                    # 3. UNOKÁK: Tételek (6. oszlop) - JAVÍTOTT KULCSOKKAL
                    try:
                        raw_json = row.iloc[6]
                        if pd.isna(raw_json) or str(raw_json).strip() in ["", "[]", "nan"]:
                            tetel_lista = []
                        else:
                            # A json.loads automatikusan kezeli az \u00c9H típusú kódolást
                            tetel_lista = json.loads(str(raw_json))
                        
                        for t in tetel_lista:
                            unoka_item = QTreeWidgetItem(partner_item)
                            
                            # A kép alapján a pontos kulcsok: "nev", "db", "suly"
                            t_nev = str(t.get('nev', 'Ismeretlen'))
                            t_db = str(t.get('db', 0))
                            t_kg = str(t.get('suly', 0))
                            
                            unoka_item.setText(0, f"  └ {t_nev}")
                            unoka_item.setText(1, t_nev) # Tétel oszlop
                            unoka_item.setText(2, t_db)  # Db oszlop
                            unoka_item.setText(3, t_kg)  # Kg oszlop
                    except:
                        pass
            
            return True, "Sikeres betöltés"
        except Exception as e:
            return False, f"Hiba: {str(e)}"
