import os
from PyQt6.QtWidgets import (QPushButton, QDialog, QVBoxLayout, QLabel, 
                             QFrame, QHBoxLayout)
from PyQt6.QtCore import Qt, QTimer

class ModulInit:
    def __init__(self, main_app):
        self.main = main_app
        # Késleltetett inicializálás, hogy a többi gomb (Statisztika) már a helyén legyen
        QTimer.singleShot(800, self.init_gomb)

    def init_gomb(self):
        # Ha már létezik az objektum, ne duplázzuk
        if hasattr(self.main, 'tervezo_btn_obj'):
            return

        # A Tervező gomb létrehozása
        self.main.tervezo_btn_obj = QPushButton("🏗️ TERVEZŐ")
        self.main.tervezo_btn_obj.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71; 
                color: white; 
                font-weight: bold; 
                padding: 6px 12px; 
                border-radius: 4px; 
                margin-bottom: 5px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        self.main.tervezo_btn_obj.clicked.connect(self.megnyitas)

        try:
            # Megkeressük a bal oldali panel layoutját a left_tree alapján
            if hasattr(self.main, 'left_tree'):
                bal_layout = self.main.left_tree.parent().layout()
                if bal_layout:
                    # A Statisztika gomb az 1-es indexen van, 
                    # így a Tervezőt a 2-es indexre szúrjuk be (közvetlenül alá)
                    bal_layout.insertWidget(2, self.main.tervezo_btn_obj)
        except Exception as e:
            print(f"Tervező gomb elhelyezési hiba: {e}")

    def megnyitas(self):
        """Megnyitja a Tervező munkaablakot"""
        dialog = QDialog(self.main)
        dialog.setWindowTitle("Fuvar Tervező Munkaablak")
        dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Címsor
        cim_label = QLabel("🏗️ Speciális Fuvartervező")
        cim_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; margin-bottom: 10px;")
        cim_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(cim_label)
        
        # Elválasztó vonal
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # Tartalmi rész (egyelőre csak egy tájékoztató szöveg)
        info_label = QLabel(
            "Ez az ablak a fuvarok további optimalizálására szolgál.\n\n"
            "Itt később megvalósítható:\n"
            "• Járművek és sofőrök hozzárendelése\n"
            "• Útvonaltervezés térképen\n"
            "• Egyedi rakodási sorrend meghatározása"
        )
        info_label.setStyleSheet("font-size: 13px; line-height: 150%; padding: 20px;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(info_label)
        
        layout.addStretch() # Kitölti a maradék helyet
        
        # Bezárás gomb
        gomb_sor = QHBoxLayout()
        bezar_btn = QPushButton("Bezárás")
        bezar_btn.setFixedWidth(100)
        bezar_btn.clicked.connect(dialog.accept)
        gomb_sor.addStretch()
        gomb_sor.addWidget(bezar_btn)
        layout.addLayout(gomb_sor)

        dialog.exec()
