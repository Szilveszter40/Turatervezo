import os
import folium
from folium import plugins
import time
import re
import io
from PyQt6.QtWidgets import (QPushButton, QDialog, QVBoxLayout, QHBoxLayout, 
                             QListWidget, QLabel, QWidget, QProgressBar, QMessageBox, QComboBox)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from geopy.geocoders import Photon

# --- 1. BELSŐ TÉRKÉP MEGJELENÍTŐ ABLAK ---
class TerkepAblak(QDialog):
    def __init__(self, html_content, parent=None):
        super().__init__(parent)
        
        # --- KRITIKUS JAVÍTÁS: Késleltetett import ---
        # Csak itt, az ablak létrehozásakor importáljuk a böngészőmotort.
        # Ez megakadályozza az OpenGL hibaüzenetet a főprogram indításakor.
        try:
            from PyQt6.QtWebEngineWidgets import QWebEngineView
        except ImportError:
            QMessageBox.critical(self, "Hiba", "A PyQt6-WebEngine nincs telepítve!")
            return

        self.setWindowTitle("Útvonal Terv - Belső Nézet")
        self.setMinimumSize(1100, 800)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Window)
        
        layout = QVBoxLayout(self)
        self.browser = QWebEngineView()
        
        # HTML tartalom betöltése a memóriából
        self.browser.setHtml(html_content)
        
        layout.addWidget(self.browser)
        
        btn_vissza = QPushButton("BEZÁRÁS")
        btn_vissza.setFixedHeight(40)
        btn_vissza.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold;")
        btn_vissza.clicked.connect(self.close)
        layout.addWidget(btn_vissza)

# --- 2. HÁTTÉRSZÁL A GEOKÓDOLÁSHOZ ---
class GeocodeWorker(QThread):
    progress_update = pyqtSignal(int)
    finished = pyqtSignal(list)

    def __init__(self, partner_nevek, geocoder, tisztito_funkcio):
        super().__init__()
        self.partner_nevek = partner_nevek
        self.geocoder = geocoder
        self.tisztito = tisztito_funkcio

    def run(self):
        talalt_koordinatak = []
        for i, teljes_szoveg in enumerate(self.partner_nevek):
            tiszta_cim = self.tisztito(teljes_szoveg)
            try:
                location = self.geocoder.geocode(f"{tiszta_cim}, Hungary", timeout=10, language="hu")
                if location:
                    talalt_koordinatak.append((location.latitude, location.longitude, teljes_szoveg))
            except:
                pass
            self.progress_update.emit(i + 1)
        self.finished.emit(talalt_koordinatak)

# --- 3. FŐ MODUL OSZTÁLY ---
class ModulInit:
    def __init__(self, main_app):
        self.main = main_app
        self.worker = None
        self.terkep_megjelenito = None 
        
        # Regisztráció az aktív modulok közé
        if not hasattr(self.main, 'active_modules'):
            self.main.active_modules = []
        self.main.active_modules.append(self)

        self.geocoder = Photon(user_agent="FuvarTervezo_Internal_Viewer_Final")
        self.telephelyek = {
            "Kecskemét": [46.9075, 19.6917],
            "Győr": [47.6875, 17.6504]
        }
        # Időzített gomb-kapcsolódás a többi modul után
        QTimer.singleShot(1500, self.init_gomb)

    def init_gomb(self):
        # Megpróbálunk a fix_turak által kezelt közös gombhoz csatlakozni
        if hasattr(self.main, 'terkep_btn_obj'):
            try: self.main.terkep_btn_obj.clicked.disconnect()
            except: pass
            self.main.terkep_btn_obj.clicked.connect(self.valaszto_ablak)
            self.main.terkep_btn_obj.setText("🗺️ TÉRKÉP")
        else:
            # Ha nincs közös gomb, létrehozunk egyet a konténerbe
            self.main.terkep_btn_obj = QPushButton("🗺️ TÉRKÉP")
            self.main.terkep_btn_obj.setStyleSheet("background-color: #3498db; color: white; font-weight: bold;")
            self.main.terkep_btn_obj.clicked.connect(self.valaszto_ablak)
            if hasattr(self.main, 'gomb_sor_kontener'):
                self.main.gomb_sor_kontener.layout().addWidget(self.main.terkep_btn_obj, 1)

    def valaszto_ablak(self):
        self.dialog = QDialog(self.main)
        self.dialog.setWindowTitle("Térképes Útvonaltervező")
        self.dialog.setMinimumSize(400, 450)
        layout = QVBoxLayout(self.dialog)
        
        layout.addWidget(QLabel("<b>Indulási telephely:</b>"))
        self.telep_combo = QComboBox()
        self.telep_combo.addItems(list(self.telephelyek.keys()))
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

        self.btn_inditas = QPushButton("🗺️ Útvonal generálása")
        self.btn_inditas.setFixedHeight(40)
        self.btn_inditas.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold;")
        self.btn_inditas.clicked.connect(self.folyamat_inditasa)
        layout.addWidget(self.btn_inditas)
        
        self.dialog.exec()

    def szuper_tisztito(self, szoveg):
        match = re.search(r'\((.*?)\)', szoveg)
        if not match: return szoveg
        tiszta = match.group(1)
        tiszta = tiszta.replace("HU ", "").replace(" - ", ", ")
        return tiszta.strip().rstrip(".")

    def folyamat_inditasa(self):
        if not self.lista.currentItem(): return
        
        t_nev = self.lista.currentItem().text()
        telep_nev = self.telep_combo.currentText()
        p_nevek = []
        
        for i in range(self.main.right_tree.topLevelItemCount()):
            it = self.main.right_tree.topLevelItem(i)
            if it.text(0) == t_nev:
                for j in range(it.childCount()):
                    p_nevek.append(it.child(j).text(0))
                break

        if p_nevek:
            self.btn_inditas.setEnabled(False)
            self.progress.setVisible(True)
            self.progress.setMaximum(len(p_nevek))
            self.progress.setValue(0)
            
            self.worker = GeocodeWorker(p_nevek, self.geocoder, self.szuper_tisztito)
            self.worker.progress_update.connect(self.progress.setValue)
            self.worker.finished.connect(lambda coords: self.terkep_kesz(coords, telep_nev))
            self.worker.start()

    def terkep_kesz(self, talalt_pontok, telep_nev):
        if hasattr(self, 'dialog'): self.dialog.accept()
        
        start_coords = self.telephelyek[telep_nev]
        m = folium.Map(location=start_coords, zoom_start=8, tiles="cartodbpositron")
        points = [start_coords]
        folium.Marker(start_coords, popup=f"START: {telep_nev}", icon=folium.Icon(color='green', icon='home')).add_to(m)

        for i, (lat, lon, nev) in enumerate(talalt_pontok):
            coords = [lat, lon]
            points.append(coords)
            folium.Marker(coords, popup=nev, icon=plugins.BeautifyIcon(number=i+1, border_color='blue')).add_to(m)

        points.append(start_coords)
        
        if len(points) > 1:
            plugins.AntPath(locations=points, color="blue", pulse_color="red", weight=5, opacity=0.6).add_to(m)
            m.fit_bounds(points)
            
            # Mentés memóriába
            out = io.BytesIO()
            m.save(out, close_file=False)
            html_content = out.getvalue().decode()
            
            # Megjelenítés a belső ablakban
            self.terkep_megjelenito = TerkepAblak(html_content, self.main)
            self.terkep_megjelenito.show()
        else:
            QMessageBox.warning(self.main, "Hiba", "Nem találtam koordinátákat.")
