from PyQt6.QtWidgets import (QPushButton, QDialog, QVBoxLayout, QHBoxLayout, 
                             QListWidget, QLabel, QMessageBox)
from PyQt6.QtCore import Qt

class ModulInit:
    def __init__(self, main_app):
        self.main = main_app
        self.init_gomb()

    def init_gomb(self):
        # 1. ELLENŐRZÉS: Ha már létezik az objektum, nem csinálunk újat
        if hasattr(self.main, 'stat_btn_obj'):
            return

        # 2. GOMB LÉTREHOZÁSA
        self.main.stat_btn_obj = QPushButton("📊 STATISZTIKA")
        self.main.stat_btn_obj.setStyleSheet("""
            QPushButton {
                background-color: #3498db; 
                color: white; 
                font-weight: bold; 
                padding: 6px 12px; 
                border-radius: 4px; 
                margin-bottom: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.main.stat_btn_obj.clicked.connect(self.megjelenites)

        try:
            if hasattr(self.main, 'left_tree'):
                bal_layout = self.main.left_tree.parent().layout()
                if bal_layout:
                    # 3. MÁSODIK ELLENŐRZÉS: Vizuálisan is megnézzük, ott van-e már
                    for i in range(bal_layout.count()):
                        item = bal_layout.itemAt(i).widget()
                        if isinstance(item, QPushButton) and "STATISZTIKA" in item.text():
                            return # Ha már a layoutban van ilyen gomb, kilépünk

                    # Ha minden tiszta, beszúrjuk a keresősáv fölé
                    bal_layout.insertWidget(1, self.main.stat_btn_obj)
        except Exception as e:
            print(f"Statisztika gomb hiba: {e}")

    def megjelenites(self):
        dialog = QDialog(self.main)
        dialog.setWindowTitle("Partner Statisztika")
        dialog.setMinimumSize(450, 500)
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("<b>📦 Tervezett súlyok partnerenként:</b>"))
        suly_lista = QListWidget()
        osszes_suly = 0
        
        # Jobb oldali fa bejárása
        for i in range(self.main.right_tree.topLevelItemCount()):
            tura = self.main.right_tree.topLevelItem(i)
            for j in range(tura.childCount()):
                partner = tura.child(j)
                p_nev = partner.text(0)
                p_suly = 0
                for k in range(partner.childCount()):
                    t = partner.child(k)
                    try:
                        s_text = t.text(4).replace(" kg", "").replace(",", ".").strip()
                        if s_text:
                            p_suly += float(s_text)
                    except: pass
                if p_suly > 0:
                    suly_lista.addItem(f"{p_nev}: {p_suly:.2f} kg")
                    osszes_suly += p_suly
        
        layout.addWidget(suly_lista)
        layout.addWidget(QLabel(f"<b>Mindösszesen: {osszes_suly:.2f} kg</b>"))
        
        layout.addSpacing(15)
        layout.addWidget(QLabel("<b>⚠️ Még nem tervezett partnerek (bal oldalon):</b>"))
        kimaradt_lista = QListWidget()
        kimaradt_lista.setStyleSheet("color: #e67e22;")
        for i in range(self.main.left_tree.topLevelItemCount()):
            kimaradt_lista.addItem(self.main.left_tree.topLevelItem(i).text(0))
        
        layout.addWidget(kimaradt_lista)
        
        b = QPushButton("Bezárás")
        b.clicked.connect(dialog.accept)
        layout.addWidget(b)
        dialog.exec()
