import os
from PyQt6.QtWidgets import QPushButton, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QWidget
from PyQt6.QtCore import Qt, QTimer

class ModulInit:
    def __init__(self, main_app):
        self.main = main_app
        # 1.2 másodperc várakozás a biztonság kedvéért
        QTimer.singleShot(1200, self.init_gomb)

    def init_gomb(self):
        if hasattr(self.main, 'terkep_btn_obj'):
            return

        if not hasattr(self.main, 'fix_tura_btn_obj'):
            return

        sablon_btn = self.main.fix_tura_btn_obj
        jobb_layout = sablon_btn.parent().layout()

        if not jobb_layout:
            return

        # 1. Vízszintes tároló létrehozása
        self.gomb_kontener = QWidget()
        kontener_layout = QHBoxLayout(self.gomb_kontener)
        kontener_layout.setContentsMargins(0, 0, 0, 0)
        kontener_layout.setSpacing(5)

        # 2. Térkép gomb létrehozása és stílusozása
        self.main.terkep_btn_obj = QPushButton("🗺️ TÉRKÉP")
        stilus = sablon_btn.styleSheet()
        if "background-color" in stilus:
            stilus = stilus.replace("#f39c12", "#3498db").replace("orange", "#3498db")
        else:
            stilus = "background-color: #3498db; color: white; font-weight: bold; padding: 8px;"
            
        self.main.terkep_btn_obj.setStyleSheet(stilus)
        self.main.terkep_btn_obj.setFont(sablon_btn.font())
        self.main.terkep_btn_obj.setFixedHeight(sablon_btn.height() if sablon_btn.height() > 0 else 35)
        self.main.terkep_btn_obj.clicked.connect(self.terkep_megnyitasa)

        # 3. Sablonok gomb áthelyezése a konténerbe
        jobb_layout.removeWidget(sablon_btn)
        kontener_layout.addWidget(sablon_btn)
        kontener_layout.addWidget(self.main.terkep_btn_obj)

        # 4. A konténer beillesztése az 1-es indexre (egy szinttel lejjebb a legtetejétől)
        # Ha 0 volt, akkor a legtetején volt, az 1-es index teszi eggyel lejebb.
        jobb_layout.insertWidget(1, self.gomb_kontener)

    def terkep_megnyitasa(self):
        dialog = QDialog(self.main)
        dialog.setWindowTitle("Útvonaltervező Térkép")
        dialog.setMinimumSize(800, 600)
        layout = QVBoxLayout(dialog)
        
        info = QLabel("<b>🗺️ Térképes útvonaloptimalizálás</b><br><br>Fejlesztés alatt...")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)
        
        bezar = QPushButton("Bezárás")
        bezar.clicked.connect(dialog.accept)
        layout.addWidget(bezar)
        
        dialog.exec()
