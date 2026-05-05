from PyQt6.QtWidgets import (QDialog, QFormLayout, QSpinBox, QDialogButtonBox, 
                             QTabWidget, QWidget, QVBoxLayout, QLabel)

class ExcelKonfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Excel Oszlopok Beállítása")
        self.resize(350, 300)
        
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        # --- RÉGI PARTNEREK FÜL ---
        self.tab_regi = QWidget()
        regi_layout = QFormLayout(self.tab_regi)
        
        # Alapértékek betöltése a főprogramból vagy alapbeállítás
        regi_alap = getattr(parent, 'regi_oszlopok', {'tura': 0, 'datum': 1, 'partner': 3, 'tetel': 5})
        
        self.r_tura = QSpinBox(); self.r_tura.setValue(regi_alap['tura'])
        self.r_datum = QSpinBox(); self.r_datum.setValue(regi_alap['datum'])
        self.r_partner = QSpinBox(); self.r_partner.setValue(regi_alap['partner'])
        self.r_tetel = QSpinBox(); self.r_tetel.setValue(regi_alap['tetel'])
        
        regi_layout.addRow("Túra oszlop (A=0):", self.r_tura)
        regi_layout.addRow("Dátum oszlop (B=1):", self.r_datum)
        regi_layout.addRow("Partner oszlop (D=3):", self.r_partner)
        regi_layout.addRow("Tétel oszlop (F=5):", self.r_tetel)
        
        # --- ÚJ PARTNEREK FÜL ---
        self.tab_uj = QWidget()
        uj_layout = QFormLayout(self.tab_uj)
        uj_alap = getattr(parent, 'uj_oszlopok', {'cim': 2, 'tetel': 5})
        
        self.u_cim = QSpinBox(); self.u_cim.setValue(uj_alap['cim'])
        self.u_tetel = QSpinBox(); self.u_tetel.setValue(uj_alap['tetel'])
        
        uj_layout.addRow("Cím oszlop:", self.u_cim)
        uj_layout.addRow("Tétel oszlop:", self.u_tetel)

        self.tabs.addTab(self.tab_regi, "Régi Adatok")
        self.tabs.addTab(self.tab_uj, "Új Adatok")
        
        layout.addWidget(self.tabs)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def get_values(self):
        return {
            'regi': {'tura': self.r_tura.value(), 'datum': self.r_datum.value(), 
                     'partner': self.r_partner.value(), 'tetel': self.r_tetel.value()},
            'uj': {'cim': self.u_cim.value(), 'tetel': self.u_tetel.value()}
        }

def indit_konfiguracio(parent):
    dialog = ExcelKonfigDialog(parent)
    if dialog.exec():
        eredmeny = dialog.get_values()
        parent.regi_oszlopok = eredmeny['regi']
        parent.uj_oszlopok = eredmeny['uj']
        parent.status_label.setText("✓ Oszlopbeállítások frissítve.")
