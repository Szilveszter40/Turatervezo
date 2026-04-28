import os
from PyQt6.QtWidgets import QFileDialog, QMessageBox

class ModulInit:
    def __init__(self, main_app):
        self.main = main_app
        if not hasattr(self.main, 'active_modules'):
            self.main.active_modules = []
        self.main.active_modules.append(self)

    def excel_fajl_valasztas(self):
        utvonal, _ = QFileDialog.getOpenFileName(self.main, "Excel fájl", "", "Excel (*.xlsx *.xls)")
        if utvonal:
            QMessageBox.information(self.main, "Kiválasztva", os.path.basename(utvonal))
