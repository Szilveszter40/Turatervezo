import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFrame, QSplitter, QTableWidget, QHeaderView)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class FixTervezoApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fix Túra Tervező Modul - Szerkesztő")
        
        # Teljes képernyős beállítás a tálca figyelembevételével
        self.init_window_size()
        self.setStyleSheet("background-color: #f5f6fa;")
        
        self.initUI()

    def init_window_size(self):
        # Eltávolítjuk a manuális setGeometry-t, mert az okozza az ütközést
        # Ehelyett csak jelezzük, hogy maximalizálva induljon
        self.setWindowState(Qt.WindowState.WindowMaximized)

    def initUI(self):
        # Fő függőleges elrendezés
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # --- FELSŐ GOMBSOR (Menü) ---
        top_menu = QHBoxLayout()
        top_menu.setSpacing(15)  # Szünet a gombok között
        top_menu.setContentsMargins(0, 0, 0, 15)

        # Gombok létrehozása egyedi színekkel
        self.btn_regi = self.create_menu_button("📍 Túrában lévő Partnerek", "#34495e") # Sötétszürke
        self.btn_uj = self.create_menu_button("👤 Új partnerek", "#2980b9")           # Kék
        self.btn_irsz = self.create_menu_button("📝 Irányítószám szerkesztő", "#8e44ad") # Lila
        self.btn_osztas = self.create_menu_button("🚀 SZÉTOSZTÁS", "#27ae60")        # Zöld
        self.btn_print = self.create_menu_button("🖨️ NYOMTATÁS (PDF)", "#e67e22") # Narancssárga
        

        top_menu.addWidget(self.btn_regi)
        top_menu.addWidget(self.btn_uj)
        top_menu.addWidget(self.btn_irsz)
        top_menu.addStretch() # Elválasztja a bal oldali gombokat a szétosztástól
        top_menu.addWidget(self.btn_osztas)
        top_menu.addWidget(self.btn_print)
        

        main_layout.addLayout(top_menu)

        # --- KÖZÉPSŐ MEGFELEZETT PANEL (Splitter) ---
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #dcdde1;
                width: 2px;
            }
        """)

        # Bal oldali panel (Régi partnerek)
        self.left_panel = QFrame()
        self.left_panel.setFrameShape(QFrame.Shape.StyledPanel)
        self.left_panel.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #dcdde1;")
        left_layout = QVBoxLayout(self.left_panel)
        
        left_title = QLabel("AKTÍV TÚRÁK / RÉGI PARTNEREK")
        left_title.setFont(QFont('Segoe UI', 10, QFont.Weight.Bold))
        left_layout.addWidget(left_title)
        
        self.left_table = QTableWidget()
        self.left_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        left_layout.addWidget(self.left_table)

        # Jobb oldali panel (Új partnerek)
        self.right_panel = QFrame()
        self.right_panel.setFrameShape(QFrame.Shape.StyledPanel)
        self.right_panel.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #dcdde1;")
        right_layout = QVBoxLayout(self.right_panel)
        
        right_title = QLabel("FELDOLGOZANDÓ ÚJ PARTNEREK")
        right_title.setFont(QFont('Segoe UI', 10, QFont.Weight.Bold))
        right_layout.addWidget(right_title)
        
        self.right_table = QTableWidget()
        self.right_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        right_layout.addWidget(self.right_table)

        # Panelek hozzáadása a splitterhez és arányok beállítása
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)

        # A splitter kapja meg a maradék összes függőleges helyet (stretch=1)
        main_layout.addWidget(self.splitter, 1)

        # --- ALSÓ ÁLLAPOTSOR ---
        self.status_label = QLabel("Készenlét - Válasszon a fenti menüpontok közül.")
        self.status_label.setStyleSheet("color: #7f8c8d; font-size: 11px; padding-top: 10px;")
        main_layout.addWidget(self.status_label)

        self.setLayout(main_layout)

    def create_menu_button(self, text, color):
        btn = QPushButton(text)
        btn.setFixedHeight(50)
        btn.setMinimumWidth(220)
        
        # Hover szín kiszámítása (kicsit világosabb)
        hover_color = self.adjust_color(color, 25)
        
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border-radius: 8px;
                font-family: 'Segoe UI';
                font-size: 13px;
                font-weight: bold;
                border: none;
                padding-left: 15px;
                padding-right: 15px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                border: 1px solid rgba(255, 255, 255, 0.5);
            }}
            QPushButton:pressed {{
                background-color: #2c3e50;
            }}
        """)
        return btn

    def adjust_color(self, hex_color, amount):
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        new_rgb = tuple(min(255, c + amount) for c in rgb)
        return "#%02x%02x%02x" % new_rgb

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FixTervezoApp()
    # Itt is kivesszük a manuális screen méregetést
    window.show()
    sys.exit(app.exec())