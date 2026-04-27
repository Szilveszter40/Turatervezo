import os
import folium
from folium import plugins
import webbrowser
import tempfile
import time
import re
from PyQt6.QtWidgets import (QPushButton, QDialog, QVBoxLayout, QHBoxLayout, 
                             QListWidget, QLabel, QWidget, QProgressBar, QMessageBox, QComboBox, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer
from geopy.geocoders import ArcGIS

class ModulInit:
    def __init__(self, main_app):
        self.main = main_app
        self.geocoder = ArcGIS(user_agent="FuvarTervezo_Final")
        self.telephelyek = {
            "Kecskemét": [46.9075, 19.6917],
            "Győr": [47.6875, 17.6504]
        }
        # Kicsit többet várunk, hogy a fix_turak modul biztosan létrehozza a konténert
        QTimer.singleShot(1500, self.init_gomb)

    def init_gomb(self):
        if hasattr(self.main, 'terkep_btn_obj'): return

        self.main.terkep_btn_obj = QPushButton("🗺️ TÉRKÉP")
        self.main.terkep_btn_obj.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; padding: 6px; border-radius: 4px;")
        self.main.terkep_btn_obj.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.main.terkep_btn_obj.clicked.connect(self.valaszto_ablak)

        # Megkeressük a közös konténert
        if hasattr(self.main, 'gomb_sor_kontener'):
            self.main.gomb_sor_kontener.layout().addWidget(self.main.terkep_btn_obj, 1)
        else:
            # Ha nincs konténer, berakja magát külön (tartalék terv)
            try:
                self.main.right_tree.parent().layout().insertWidget(1, self.main.terkep_btn_obj)
            except: pass

    def valaszto_ablak(self):
        dialog = QDialog(self.main)
        dialog.setWindowTitle("Térképes Útvonaltervező")
        dialog.setMinimumSize(400, 500)
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("<b>Indulási telephely:</b>"))
        self.telep_combo = QComboBox()
        self.telep_combo.addItems(["Kecskemét", "Győr"])
        layout.addWidget(self.telep_combo)
        
        layout.addSpacing(10)
        layout.addWidget(QLabel("<b>Válaszd ki a túrát:</b>"))
        self.lista = QListWidget()
        for i in range(self.main.right_tree.topLevelItemCount()):
            self.lista.addItem(self.main.right_tree.topLevelItem(i).text(0))
        layout.addWidget(self.lista)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        def inditas():
            if not self.lista.currentItem(): return
            t_nev = self.lista.currentItem().text()
            telep_nev = self.telep_combo.currentText()
            p_nevek = [it.child(j).text(0) for i in range(self.main.right_tree.topLevelItemCount()) 
                       for it in [self.main.right_tree.topLevelItem(i)] if it.text(0) == t_nev 
                       for j in range(it.childCount())]
            
            if p_nevek:
                self.progress.setVisible(True)
                self.progress.setMaximum(len(p_nevek))
                self.general_es_nyit(t_nev, p_nevek, telep_nev, self.progress)
                dialog.accept()

        btn_ok = QPushButton("🗺️ Útvonal generálása")
        btn_ok.setFixedHeight(40)
        btn_ok.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold;")
        btn_ok.clicked.connect(inditas)
        layout.addWidget(btn_ok)
        dialog.exec()

    def szuper_tisztito(self, szoveg):
        match = re.search(r'\((.*?)\)', szoveg)
        if not match: return szoveg
        belso = match.group(1)
        if "HU " in belso: return belso.split("HU ", 1)[1].strip().rstrip(".")
        parts = belso.split(" - ")
        return parts[-1].strip().rstrip(".")

    def general_es_nyit(self, t_nev, partner_nevek, telep_nev, progress_bar):
        start_coords = self.telephelyek[telep_nev]
        m = folium.Map(location=start_coords, zoom_start=8, tiles="cartodbpositron")
        points = [start_coords]

        folium.Marker(start_coords, popup=f"START: {telep_nev}", icon=folium.Icon(color='green', icon='home')).add_to(m)

        for i, teljes_szoveg in enumerate(partner_nevek):
            progress_bar.setValue(i + 1)
            self.main.repaint()
            tiszta_cim = self.szuper_tisztito(teljes_szoveg)
            try:
                time.sleep(0.2)
                location = self.geocoder.geocode(f"{tiszta_cim}, Hungary")
                if location:
                    coords = [location.latitude, location.longitude]
                    points.append(coords)
                    folium.Marker(coords, popup=teljes_szoveg, icon=plugins.BeautifyIcon(number=i+1, border_color='blue')).add_to(m)
            except: continue

        points.append(start_coords)
        if len(points) > 1:
            plugins.AntPath(locations=points, color="blue", pulse_color="red", weight=5, opacity=0.6).add_to(m)
            m.fit_bounds(points)
            temp_file = os.path.join(tempfile.gettempdir(), f"fuvar_{int(time.time())}.html")
            m.save(temp_file)
            webbrowser.open(temp_file)
