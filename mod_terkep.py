import os
import folium
from folium import plugins # Új import az irányjelző vonalhoz
import webbrowser
import tempfile
import time
import re
from PyQt6.QtWidgets import (QPushButton, QDialog, QVBoxLayout, QHBoxLayout, 
                             QListWidget, QLabel, QWidget, QProgressBar, QMessageBox, QComboBox)
from PyQt6.QtCore import Qt, QTimer
from geopy.geocoders import ArcGIS

class ModulInit:
    def __init__(self, main_app):
        self.main = main_app
        self.geocoder = ArcGIS(user_agent="FuvarTervezo_Loop_v10")
        # Telephelyek koordinátái
        self.telephelyek = {
            "Kecskemét": [46.9075, 19.6917],
            "Győr": [47.6875, 17.6504]
        }
        QTimer.singleShot(1200, self.init_gomb)

    def init_gomb(self):
        if hasattr(self.main, 'terkep_btn_obj') or not hasattr(self.main, 'fix_tura_btn_obj'):
            return
        sablon_btn = self.main.fix_tura_btn_obj
        jobb_layout = sablon_btn.parent().layout()
        if not jobb_layout: return

        self.gomb_kontener = QWidget()
        kont_l = QHBoxLayout(self.gomb_kontener)
        kont_l.setContentsMargins(0, 0, 0, 0)
        kont_l.setSpacing(5)

        self.main.terkep_btn_obj = QPushButton("🗺️ TÉRKÉP")
        stilus = sablon_btn.styleSheet().replace("#f39c12", "#3498db").replace("orange", "#3498db")
        self.main.terkep_btn_obj.setStyleSheet(stilus)
        self.main.terkep_btn_obj.setFont(sablon_btn.font())
        self.main.terkep_btn_obj.setFixedHeight(sablon_btn.height() if sablon_btn.height() > 0 else 35)
        self.main.terkep_btn_obj.clicked.connect(self.valaszto_ablak)

        jobb_layout.removeWidget(sablon_btn)
        kont_l.addWidget(sablon_btn)
        kont_l.addWidget(self.main.terkep_btn_obj)
        jobb_layout.insertWidget(1, self.gomb_kontener)

    def valaszto_ablak(self):
        dialog = QDialog(self.main)
        dialog.setWindowTitle("Térképes Útvonaltervező")
        dialog.setMinimumSize(400, 550)
        layout = QVBoxLayout(dialog)
        
        # Telephely választó
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
        if "HU " in belso:
            return belso.split("HU ", 1)[1].strip().rstrip(".")
        parts = belso.split(" - ")
        return parts[-1].strip().rstrip(".")

    def general_es_nyit(self, t_nev, partner_nevek, telep_nev, progress_bar):
        # Kezdő koordináta (telephely)
        start_coords = self.telephelyek[telep_nev]
        
        m = folium.Map(location=start_coords, zoom_start=8, tiles="cartodbpositron")
        points = [start_coords] # Az útvonal a telephelyről indul

        # Telephely jelölése (Zöld házikó)
        folium.Marker(
            start_coords, 
            popup=f"START/CÉL: {telep_nev}", 
            tooltip=f"Telephely: {telep_nev}",
            icon=folium.Icon(color='green', icon='home', prefix='fa')
        ).add_to(m)

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
                    # Sorszámozott jelölők a partnereknek
                    folium.Marker(
                        coords, 
                        popup=teljes_szoveg, 
                        tooltip=f"{i+1}. megálló: {teljes_szoveg.split('(')[0]}",
                        icon=plugins.BeautifyIcon(
                            number=i+1,
                            border_color='blue',
                            text_color='blue',
                            inner_icon_style='margin-top:0;'
                        )
                    ).add_to(m)
            except: continue

        # Útvonal zárása: visszatérés a telephelyre
        points.append(start_coords)

        if len(points) > 1:
            # Animált irányjelző vonal (AntPath) - "vonuló" piros csíkokkal
            plugins.AntPath(
                locations=points,
                color="blue",
                pulse_color="red",
                weight=5,
                opacity=0.6,
                delay=1000 # Az animáció sebessége
            ).add_to(m)
            m.fit_bounds(points)
            
            temp_file = os.path.join(tempfile.gettempdir(), f"fuvar_{int(time.time())}.html")
            m.save(temp_file)
            webbrowser.open(temp_file)
        else:
            QMessageBox.warning(self.main, "Hiba", "Nem sikerült címeket találni.")
