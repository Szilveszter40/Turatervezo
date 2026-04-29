import os
import folium
from folium import plugins
import re
import glob
import webbrowser
import xml.etree.ElementTree as ET
from datetime import datetime
from PyQt6.QtWidgets import (QPushButton, QDialog, QVBoxLayout, QHBoxLayout, 
                             QListWidget, QLabel, QProgressBar, QMessageBox, QComboBox)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from geopy.geocoders import Photon

# --- 1. HÁTTÉRSZÁL A KERESÉSHEZ ---
class GeocodeWorker(QThread):
    progress_update = pyqtSignal(int)
    finished = pyqtSignal(list)

    def __init__(self, partner_nevek, geocoder, tisztito_funkcio, kml_adatbazis):
        super().__init__()
        self.partner_nevek = partner_nevek
        self.geocoder = geocoder
        self.tisztito = tisztito_funkcio
        self.kml_db = kml_adatbazis

    def run(self):
        talalt_pontok = []
        for i, teljes_szoveg in enumerate(self.partner_nevek):
            try:
                t_nev = self.tisztito(teljes_szoveg, mod="nev")
                t_cim = self.tisztito(teljes_szoveg, mod="cim")
                lat_lon = None

                # 1. KML
                if t_nev in self.kml_db:
                    lat_lon = self.kml_db[t_nev]
                
                # 2. Online Teljes
                if not lat_lon:
                    try:
                        loc = self.geocoder.geocode(f"{t_cim}, Hungary", timeout=10)
                        if loc: lat_lon = [loc.latitude, loc.longitude]
                    except: pass

                # 3. Online Házszám nélkül
                if not lat_lon and "," in t_cim:
                    try:
                        t_cim_szuk = t_cim.rsplit(",", 1)[0].strip()
                        loc = self.geocoder.geocode(f"{t_cim_szuk}, Hungary", timeout=10)
                        if loc: lat_lon = [loc.latitude, loc.longitude]
                    except: pass

                # 4. Csak Város
                if not lat_lon:
                    try:
                        varos = t_cim.split(",")[0].strip()
                        loc = self.geocoder.geocode(f"{varos}, Hungary", timeout=10)
                        if loc: lat_lon = [loc.latitude, loc.longitude]
                    except: pass
                
                if lat_lon:
                    # JAVÍTÁS: Itt csak a [lat, lon, név] hármast adjuk át, nem duplázzuk a listát!
                    talalt_pontok.append((lat_lon[0], lat_lon[1], teljes_szoveg))
            except: pass
            self.progress_update.emit(i + 1)
        self.finished.emit(talalt_pontok)

# --- 2. FŐ MODUL OSZTÁLY ---
class ModulInit:
    def __init__(self, main_app):
        self.main = main_app
        self.kml_mappa = "kml_adatok"
        self.mentes_mappa = "mentett_terkepek"
        if not hasattr(self.main, 'active_modules'): self.main.active_modules = []
        if self not in self.main.active_modules: self.main.active_modules.append(self)
        self.geocoder = Photon(user_agent="FuvarTervezo_Final_Fix")
        self.telephelyek = {"Kecskemét": [46.9075, 19.6917], "Győr": [47.6875, 17.6504]}
        QTimer.singleShot(1500, self.init_gomb)

    def kml_beolvasas(self):
        db = {}
        if not os.path.exists(self.kml_mappa): os.makedirs(self.kml_mappa); return db
        for f in glob.glob(os.path.join(self.kml_mappa, "*.kml")):
            try:
                tree = ET.parse(f)
                for pm in tree.iter():
                    if pm.tag.endswith('Placemark'):
                        n, c = "", ""
                        for e in pm.iter():
                            if e.tag.endswith('name'): n = e.text.strip().lower() if e.text else ""
                            if e.tag.endswith('coordinates'): c = e.text.strip().split(',') if e.text else ""
                        if n and len(c) >= 2: db[n] = [float(c[1]), float(c[0])]
            except: continue
        return db

    def szuper_tisztito(self, szoveg, mod="cim"):
        if mod == "nev": return szoveg.replace("🚛", "").split("(")[0].strip().lower()
        match = re.search(r'\((.*?)\)', szoveg)
        if not match: return szoveg
        t = match.group(1)
        t = re.sub(r'HU \d{4} - ', '', t)
        return t.replace("HU ", "").replace(" - ", ", ").strip().rstrip(".")

    def init_gomb(self):
        if not hasattr(self.main, 'terkep_btn_obj'):
            self.main.terkep_btn_obj = QPushButton("🗺️ TÉRKÉP")
            self.main.terkep_btn_obj.setStyleSheet("background-color: #3498db; color: white; font-weight: bold;")
            if hasattr(self.main, 'left_layout'): self.main.left_layout.addWidget(self.main.terkep_btn_obj)
        try: self.main.terkep_btn_obj.clicked.disconnect()
        except: pass
        self.main.terkep_btn_obj.clicked.connect(self.valaszto_ablak)

    def valaszto_ablak(self):
        self.dialog = QDialog(self.main)
        self.dialog.setWindowTitle("Útvonaltervező")
        l = QVBoxLayout(self.dialog)
        l.addWidget(QLabel("<b>Telephely:</b>"))
        self.telep_combo = QComboBox(); self.telep_combo.addItems(list(self.telephelyek.keys())); l.addWidget(self.telep_combo)
        l.addWidget(QLabel("<b>Túra:</b>"))
        self.lista = QListWidget()
        for i in range(self.main.right_tree.topLevelItemCount()): self.lista.addItem(self.main.right_tree.topLevelItem(i).text(0))
        l.addWidget(self.lista)
        self.progress = QProgressBar(); self.progress.setVisible(False); l.addWidget(self.progress)
        self.btn = QPushButton("🗺️ Generálás"); self.btn.clicked.connect(self.inditas); l.addWidget(self.btn)
        self.dialog.exec()

    def inditas(self):
        if not self.lista.currentItem(): return
        p_nevek = []
        t_nev = self.lista.currentItem().text()
        for i in range(self.main.right_tree.topLevelItemCount()):
            it = self.main.right_tree.topLevelItem(i)
            if it.text(0) == t_nev:
                for j in range(it.childCount()): p_nevek.append(it.child(j).text(0))
                break
        if p_nevek:
            self.btn.setEnabled(False); self.progress.setVisible(True); self.progress.setMaximum(len(p_nevek))
            self.worker = GeocodeWorker(p_nevek, self.geocoder, self.szuper_tisztito, self.kml_beolvasas())
            self.worker.progress_update.connect(self.progress.setValue)
            self.worker.finished.connect(lambda p: self.terkep_kesz(p, self.telep_combo.currentText()))
            self.worker.start()

    def terkep_kesz(self, pontok, telep_nev):
        self.dialog.accept()
        if not pontok: QMessageBox.warning(self.main, "Hiba", "Nincs pont!"); return
        try:
            if not os.path.exists(self.mentes_mappa): os.makedirs(self.mentes_mappa)
            idopont = datetime.now().strftime("%Y-%m-%d_%H-%M")
            t_nev = re.sub(r'[\\/*?:"<>|]', "", self.lista.currentItem().text().replace("🚛", "").strip())
            teljes_utvonal = os.path.abspath(os.path.join(self.mentes_mappa, f"{t_nev}_{idopont}.html"))

            start = self.telephelyek[telep_nev]
            m = folium.Map(location=start, zoom_start=8, tiles="cartodbpositron")
            all_pts = [start]
            folium.Marker(start, popup="START", icon=folium.Icon(color='green', icon='home')).add_to(m)

            for i, (lat, lon, nev) in enumerate(pontok):
                all_pts.append([lat, lon])
                folium.Marker([lat, lon], popup=nev, icon=plugins.BeautifyIcon(number=i+1, border_color='blue')).add_to(m)

            all_pts.append(start)
            line = folium.PolyLine(locations=all_pts, color="blue", weight=4, opacity=0.7).add_to(m)
            plugins.PolyLineTextPath(line, '    >    ', repeat=True, offset=7, attributes={'fill': 'red', 'font-size': '20', 'font-weight': 'bold'}).add_to(m)
            m.fit_bounds(all_pts)
            m.save(teljes_utvonal); webbrowser.open(f"file://{teljes_utvonal}")
        except Exception as e:
            QMessageBox.critical(self.main, "Hiba", f"Hiba: {e}")
