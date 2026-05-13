import os
import folium
from folium import plugins
import re
import glob
import webbrowser
import xml.etree.ElementTree as ET
import uuid
from datetime import datetime
from PyQt6.QtWidgets import (QPushButton, QDialog, QVBoxLayout, QHBoxLayout, 
                             QListWidget, QLabel, QProgressBar, QMessageBox, QComboBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from geopy.geocoders import Photon

# --- 1. HÁTTÉRSZÁL A KERESÉSHEZ (VÁLTOZATLAN) ---
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

                if t_nev in self.kml_db:
                    lat_lon = self.kml_db[t_nev]
                
                if not lat_lon:
                    try:
                        loc = self.geocoder.geocode(f"{t_cim}, Hungary", timeout=10)
                        if loc: lat_lon = [loc.latitude, loc.longitude]
                    except: pass

                if not lat_lon and "," in t_cim:
                    try:
                        t_cim_szuk = t_cim.rsplit(",", 1)[0].strip()
                        loc = self.geocoder.geocode(f"{t_cim_szuk}, Hungary", timeout=10)
                        if loc: lat_lon = [loc.latitude, loc.longitude]
                    except: pass

                if not lat_lon:
                    try:
                        varos = t_cim.split(",")[0].strip()
                        loc = self.geocoder.geocode(f"{varos}, Hungary", timeout=10)
                        if loc: lat_lon = [loc.latitude, loc.longitude]
                    except: pass
                
                if lat_lon:
                    talalt_pontok.append((lat_lon[0], lat_lon[1], teljes_szoveg))
            except: pass
            self.progress_update.emit(i + 1)
        self.finished.emit(talalt_pontok)

# --- 2. MODULÁRIS FŐ ABLAK OSZTÁLY ---
class TerkepTervezoAblak(QDialog):
    """
    Önállóan meghívható térkép-tervező ablak, amely automatikusan
    kiolvassa a szülőablak fastruktúrájában (QTreeWidget) szereplő túrákat.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_parent = parent  # A gombot indító ablak (KeziszerkesztoAblak)
        self.kml_mappa = "kml_adatok"
        self.mentes_mappa = "mentett_terkepek"
        
        self.geocoder = Photon(user_agent=f"FuvarTervezo_Final_Fix_{uuid.uuid4().hex[:6]}")
        self.telephelyek = {"Kecskemét": [46.9075, 19.6917], "Győr": [47.6875, 17.6504]}
        
        self.setWindowTitle("Térképes Útvonaltervező")
        self.resize(450, 500)
        self.initUI()

    def kml_beolvasas(self):
        db = {}
        if not os.path.exists(self.kml_mappa): 
            os.makedirs(self.kml_mappa)
            return db
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
        if mod == "nev": return szoveg.replace("🚛", "").replace("🚚", "").split("(")[0].strip().lower()
        match = re.search(r'\((.*?)\)', szoveg)
        if not match: return szoveg
        t = match.group(1)
        t = re.sub(r'HU \d{4} - ', '', t)
        return t.replace("HU ", "").replace(" - ", ", ").strip().rstrip(".")

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Telephely választó
        layout.addWidget(QLabel("<b>Telephely kiválasztása:</b>"))
        self.telep_combo = QComboBox()
        self.telep_combo.addItems(list(self.telephelyek.keys()))
        self.telep_combo.setFixedHeight(35)
        layout.addWidget(self.telep_combo)

        # Túra választó lista
        layout.addWidget(QLabel("<b>Válaszd ki a térképezni kívánt túrát:</b>"))
        self.lista = QListWidget()
        
        # --- AUTOMATIKUS KIOLVASÁS A KÉZI SZERKESZTŐBŐL ---
        # Átnézzük a szülőablak bal és jobb oldali fáját is, és kigyűjtjük a betöltött túrákat
        tura_nevek = set()
        if self.main_parent:
            for tree_attr in ['tree_bal', 'tree_jobb', 'tree_paratlan', 'tree_paros', 'tree_kozos']:
                if hasattr(self.main_parent, tree_attr):
                    tree_widget = getattr(self.main_parent, tree_attr)
                    for i in range(tree_widget.topLevelItemCount()):
                        t_szoveg = tree_widget.topLevelItem(i).text(0)
                        tura_nevek.add(t_szoveg)
        
        for t in sorted(list(tura_nevek)):
            self.lista.addItem(t)
            
        layout.addWidget(self.lista)

        # Folyamatjelző
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setFixedHeight(20)
        layout.addWidget(self.progress)

        # Indító gomb
        self.btn_general = QPushButton("🗺️ TÉRKÉP GENERÁLÁSA")
        self.btn_general.setFixedHeight(45)
        self.btn_general.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; border-radius: 5px;")
        self.btn_general.clicked.connect(self.inditas)
        layout.addWidget(self.btn_general)

    def inditas(self):
        if not self.lista.currentItem():
            QMessageBox.warning(self, "Figyelem", "Kérlek, válassz ki egy túrát a listából!")
            return
            
        p_nevek = []
        t_nev = self.lista.currentItem().text()
        
        # Megkeressük az adott túra alatti partnereket a szülőablak fái között
        if self.main_parent:
            for tree_attr in ['tree_bal', 'tree_jobb', 'tree_paratlan', 'tree_paros', 'tree_kozos']:
                if hasattr(self.main_parent, tree_attr):
                    tree_widget = getattr(self.main_parent, tree_attr)
                    for i in range(tree_widget.topLevelItemCount()):
                        it = tree_widget.topLevelItem(i)
                        if it.text(0) == t_nev:
                            for j in range(it.childCount()):
                                p_nevek.append(it.child(j).text(0))
                            break

        if p_nevek:
            self.btn_general.setEnabled(False)
            self.progress.setVisible(True)
            self.progress.setMaximum(len(p_nevek))
            self.progress.setValue(0)
            
            self.worker = GeocodeWorker(p_nevek, self.geocoder, self.szuper_tisztito, self.kml_beolvasas())
            self.worker.progress_update.connect(self.progress.setValue)
            self.worker.finished.connect(lambda p: self.terkep_kesz(p, self.telep_combo.currentText()))
            self.worker.start()
        else:
            QMessageBox.warning(self, "Figyelem", "A kijelölt túrához nem tartoznak partnerek!")

    def terkep_kesz(self, pontok, telep_nev):
        self.btn_general.setEnabled(True)
        self.progress.setVisible(False)
        
        if not pontok: 
            QMessageBox.warning(self, "Hiba", "Nem sikerült földrajzi koordinátákat rendelni a partnerekhez!")
            return
            
        try:
            if not os.path.exists(self.mentes_mappa): 
                os.makedirs(self.mentes_mappa)
                
            idopont = datetime.now().strftime("%Y-%m-%d_%H-%M")
            t_nev_tiszta = re.sub(r'[\\/*?:"<>|]', "", self.lista.currentItem().text().replace("🚛", "").replace("🚚", "").strip())
            teljes_utvonal = os.path.abspath(os.path.join(self.mentes_mappa, f"{t_nev_tiszta}_{idopont}.html"))

            start = self.telephelyek[telep_nev]
            m = folium.Map(location=start, zoom_start=8, tiles="cartodbpositron")
            all_pts = [start]
            folium.Marker(start, popup="TELEPHELY (START/CÉL)", icon=folium.Icon(color='green', icon='home')).add_to(m)

            for i, (lat, lon, nev) in enumerate(pontok):
                all_pts.append([lat, lon])
                folium.Marker([lat, lon], popup=nev, icon=plugins.BeautifyIcon(number=i+1, border_color='blue')).add_to(m)

            all_pts.append(start)
            line = folium.PolyLine(locations=all_pts, color="blue", weight=4, opacity=0.7).add_to(m)
            plugins.PolyLineTextPath(line, '    >    ', repeat=True, offset=7, attributes={'fill': 'red', 'font-size': '20', 'font-weight': 'bold'}).add_to(m)
            m.fit_bounds(all_pts)
            
            m.save(teljes_utvonal)
            webbrowser.open(f"file://{teljes_utvonal}")
            self.accept()  # Bezárja a dialógust sikeres generálás után
            
        except Exception as e:
            QMessageBox.critical(self, "Hiba", f"Térkép mentési hiba:\n{e}")
