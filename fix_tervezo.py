import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFrame, QSplitter, QTableWidget, 
                             QHeaderView, QTreeWidget)
from PyQt6.QtCore import Qt
import fixmod_adatkezeles
import fixmod_irsz_szerkeszto
import fixmod_nyomtatas
import fixmod_uj_partnerek
import fixmod_konfig
import fixmod_szetosztas

class FixTervezoApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fix Túra Tervező Rendszer")
        self.setWindowState(Qt.WindowState.WindowMaximized)
        self.setStyleSheet("background-color: #f5f6fa;")
        self.regi_kapcsok = set()
        self.regi_nev_tar = {}
        self.regi_oszlopok = {'tura': 0, 'datum': 1, 'partner': 3, 'tetel': 5}
        self.uj_oszlopok = {'cim': 2, 'tetel': 5}
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(15, 15, 15, 15)

        top_menu = QHBoxLayout()
        top_menu.setSpacing(15)
        top_menu.setContentsMargins(0, 0, 0, 15)

        self.btn_regi = self.create_menu_button("📍 Régi Partnerek", "#34495e")
        self.btn_uj = self.create_menu_button("👤 Új partnerek", "#2980b9")
        self.btn_irsz = self.create_menu_button("📝 IRSZ szerkesztő", "#8e44ad")
        self.btn_print = self.create_menu_button("🖨️ NYOMTATÁS", "#e67e22")
        self.btn_szetosztas = self.create_menu_button("🚀 SZÉTOSZTÁS", "#27ae60")
        self.btn_config = self.create_menu_button("⚙️ EXCEL LÉTREHOZÁS", "#7f8c8d")

        self.btn_regi.clicked.connect(lambda: fixmod_adatkezeles.partner_betoltes_regi(self))
        self.btn_irsz.clicked.connect(lambda: fixmod_irsz_szerkeszto.indit_irsz_szerkeszto(self))
        self.btn_print.clicked.connect(lambda: fixmod_nyomtatas.elonezet_es_nyomtatas(self.right_table))
        self.btn_uj.clicked.connect(lambda: fixmod_uj_partnerek.betoltes_es_feldolgozas(self))
        self.btn_config.clicked.connect(lambda: fixmod_konfig.indit_konfiguracio(self))
        self.btn_szetosztas.clicked.connect(lambda: fixmod_szetosztas.szetosztas_ablak_megnyitasa(self))

        top_menu.addWidget(self.btn_regi)
        top_menu.addWidget(self.btn_uj)
        top_menu.addWidget(self.btn_irsz)
        top_menu.addWidget(self.btn_config)
        top_menu.addStretch()
        top_menu.addWidget(self.btn_print)
        top_menu.addWidget(self.btn_szetosztas)
        main_layout.addLayout(top_menu)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setStyleSheet("QSplitter::handle { background-color: #dcdde1; width: 2px; }")

        # Bal oldal (Fa)
        self.left_panel = QFrame()
        self.left_panel.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #dcdde1;")
        l_layout = QVBoxLayout(self.left_panel)
        l_layout.addWidget(QLabel("<b>RÉGI PARTNEREK (ÖSSZESÍTETT)</b>"))
        self.left_tree = QTreeWidget()
        self.left_tree.setColumnCount(4)
        self.left_tree.setHeaderLabels(["Partner / Dátum", "Súly", "Túra", "Intenzitás"])
        self.left_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        l_layout.addWidget(self.left_tree)

        # Jobb oldal (Táblázat)
        self.right_panel = QFrame()
        self.right_panel.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #dcdde1;")
        r_layout = QVBoxLayout(self.right_panel)
        r_layout.addWidget(QLabel("<b>ÚJ PARTNEREK</b>"))
        self.right_table = QTableWidget()
        r_layout.addWidget(self.right_table)

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        main_layout.addWidget(self.splitter, 1)

        self.status_label = QLabel("Készenlét")
        main_layout.addWidget(self.status_label)
        self.setLayout(main_layout)

    def create_menu_button(self, text, color):
        btn = QPushButton(text)
        btn.setFixedHeight(50)
        btn.setMinimumWidth(180)
        btn.setStyleSheet(f"background-color: {color}; color: white; border-radius: 8px; font-weight: bold; border: none;")
        return btn

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = FixTervezoApp()
    win.show()
    sys.exit(app.exec())
