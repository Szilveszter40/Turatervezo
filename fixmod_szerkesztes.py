import json
import pandas as pd
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, 
                             QTreeWidgetItem, QLabel, QPushButton, QMessageBox, 
                             QListWidget, QListWidgetItem, QAbstractItemView, QFrame, 
                             QSizePolicy, QHeaderView, QComboBox, QFileDialog, QLineEdit)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QTreeWidget, QAbstractItemView, QTreeWidgetItem
from PyQt6.QtCore import Qt, QTimer

class DraggableTree(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDropIndicatorShown(True)
        self.setIndentation(20)
        self.setAnimated(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, position):
        item = self.itemAt(position)
        if not item:
            return

        from PyQt6.QtWidgets import QMenu
        menu = QMenu()
        user_role = item.data(0, Qt.ItemDataRole.UserRole)

        # --- 1. TÚRA TÖRLÉSE (A te meglévő kódod) ---
        if user_role == "TURA":
            delete_action = menu.addAction("Túra törlése")
            is_empty = item.childCount() == 0
            delete_action.setEnabled(is_empty)
            if not is_empty:
                delete_action.setText("Túra törlése (nem üres!)")

            action = menu.exec(self.viewport().mapToGlobal(position))
            
            if action == delete_action and is_empty:
                root = self.invisibleRootItem()
                (item.parent() or root).removeChild(item)
                self._hiv_suly_frissites()

        # --- 2. PARTNER TÖRLÉSE (Áthelyezés Töröltekbe) ---
        elif user_role == "PARTNER":
            move_action = menu.addAction("🗑 Partner törlése (Áthelyezés)")
            action = menu.exec(self.viewport().mapToGlobal(position))
            
            if action == move_action:
                self.partner_athelyezese_toroltekbe(item)

    def _hiv_suly_frissites(self):
        """Segédfüggvény a súlyfrissítés eléréséhez"""
        main_win = self.window()
        while main_win and not hasattr(main_win, 'suly_frissites'):
            parent = main_win.parent()
            if not parent: break
            main_win = parent
        if main_win and hasattr(main_win, 'suly_frissites'):
            main_win.suly_frissites()

    def partner_athelyezese_toroltekbe(self, item):
        # 1. Megkeressük, létezik-e már a "Töröltek" túra ebben a fában
        toroltek_node = None
        for i in range(self.topLevelItemCount()):
            node = self.topLevelItem(i)
            if "Töröltek" in node.text(0):
                toroltek_node = node
                break
        
        # 2. Ha nem találjuk, LÉTREHOZZUK és kényszerítjük a megjelenítést
        if not toroltek_node:
            toroltek_node = QTreeWidgetItem(self) # Közvetlenül a fához adjuk
            toroltek_node.setText(0, "🚚 Töröltek")
            toroltek_node.setText(1, "Átlag: 0 cím")
            toroltek_node.setText(2, "Össz: 0 kg")
            toroltek_node.setData(0, Qt.ItemDataRole.UserRole, "TURA")
            toroltek_node.setBackground(0, QColor("#dfe6e9"))
            # Engedélyezzük, hogy lehessen bele pakolni
            toroltek_node.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDropEnabled)
            
            # Kényszerített láthatóság
            self.addTopLevelItem(toroltek_node)

        # 3. ÁTHELYEZÉS
        regi_szulo = item.parent()
        if regi_szulo:
            # Kivesszük a régi helyéről
            index = regi_szulo.indexOfChild(item)
            kivett_item = regi_szulo.takeChild(index)
            # Betesszük az újba
            toroltek_node.addChild(kivett_item)
            
            # Adat frissítése a partneren belül (hogy a mentés is tudja)
            p_adat = kivett_item.data(1, Qt.ItemDataRole.UserRole)
            if p_adat:
                p_adat['Túra'] = "Töröltek"
                kivett_item.setData(1, Qt.ItemDataRole.UserRole, p_adat)
            
            # Túra kinyitása, hogy látszódjon a törölt partner
            toroltek_node.setExpanded(True)
            
            # Számok frissítése (hogy az eredeti túra súlya csökkenjen)
            self._hiv_suly_frissites()

    def dragEnterEvent(self, event):
        if event.source():
            event.accept()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.source():
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        source_tree = event.source()
        if not source_tree:
            event.ignore()
            return

        source_item = source_tree.currentItem()

        if not source_item or source_item.data(0, Qt.ItemDataRole.UserRole) != "PARTNER":
            event.ignore()
            return

        target_item = self.itemAt(event.position().toPoint())
        if not target_item:
            event.ignore()
            return

        p_adat = source_item.data(1, Qt.ItemDataRole.UserRole)
        target_type = target_item.data(0, Qt.ItemDataRole.UserRole)

        dest_root = None
        index = 0

        if target_type == "TURA":
            dest_root = target_item
            index = dest_root.childCount()
        elif target_type == "PARTNER":
            dest_root = target_item.parent()
            index = dest_root.indexOfChild(target_item)
        elif target_item.parent() and target_item.parent().data(0, Qt.ItemDataRole.UserRole) == "PARTNER":
            partner_node = target_item.parent()
            dest_root = partner_node.parent()
            index = dest_root.indexOfChild(partner_node)

        if not dest_root or dest_root.data(0, Qt.ItemDataRole.UserRole) != "TURA":
            event.ignore()
            return

        main_win = self.window()
        while main_win and not hasattr(main_win, 'partner_sor_letrehozas'):
            main_win = main_win.parent()

        if source_tree == self:
            # --- PANELEN BELÜLI MOZGATÁS ---
            old_parent = source_item.parent()
            if old_parent:
                old_index = old_parent.indexOfChild(source_item)
                if old_parent == dest_root and index > old_index:
                    index -= 1
                
                moving_item = old_parent.takeChild(old_index)
                dest_root.insertChild(index, moving_item)
                self.setCurrentItem(moving_item)
                dest_root.setExpanded(True)
        else:
            # --- PANELEK KÖZÖTTI MOZGATÁS ---
            if main_win:
                main_win.partner_sor_letrehozas(dest_root, p_adat)
                uj_item = dest_root.takeChild(dest_root.childCount() - 1)
                dest_root.insertChild(index, uj_item)
                
                if source_item.parent():
                    source_item.parent().removeChild(source_item)
                dest_root.setExpanded(True)

        # Itt a javítás: IgnoreAction-t kell használni
        event.setDropAction(Qt.DropAction.IgnoreAction)
        event.accept()

        if main_win:
            QTimer.singleShot(100, main_win.suly_frissites)

class KeziszerkesztoAblak(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_parent = parent
        self.setWindowTitle("Kézi Túra Szerkesztő - Stabil Verzió")
        self.resize(1300, 900)
        self.osszes_tura_neve = self._turak_kigyujtese()
        self.initUI()

    def showEvent(self, event):
        super().showEvent(event)
        self.setWindowState(Qt.WindowState.WindowMaximized)

    def _turak_kigyujtese(self):
        turak = set()
        for p in self.main_parent.minden_partner_adat:
            t_nev = str(p.get('Túra', 'ISMERETLEN'))
            if t_nev.lower() in ['nan', '', 'none']: t_nev = 'ISMERETLEN'
            turak.add(t_nev)
        return sorted(list(turak))

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # --- FELSŐ VEZÉRLŐSÁV (FELEZVE) ---
        top_control_layout = QHBoxLayout()
        self.btn_frissit = QPushButton("📂 AKTUÁLIS BETÖLTÉSE (SZÉTOSZTÁSBÓL)")
        self.btn_frissit.setFixedHeight(45)
        self.btn_frissit.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold; border-radius: 5px;")
        self.btn_frissit.clicked.connect(self.aktualis_betoltese_fajlbol)
        top_control_layout.addWidget(self.btn_frissit, 1)

        het_layout = QHBoxLayout()
        het_label = QLabel("<b>SZŰRÉS HÉTRE:</b>")
        het_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.combo_het = QComboBox()
        self.combo_het.addItems(["Mind (Összes adat)", "Páratlan Hét", "Páros Hét"])
        self.combo_het.setFixedHeight(45)
        self.combo_het.setStyleSheet("padding: 5px; font-weight: bold;")
        self.combo_het.currentIndexChanged.connect(self.adatok_betoltese)
        het_layout.addWidget(het_label)
        het_layout.addWidget(self.combo_het)
        top_control_layout.addLayout(het_layout, 1)
        main_layout.addLayout(top_control_layout)

        # --- TÚRA VÁLASZTÓK ---
        top_row = QHBoxLayout()
        for title, attr in [("Bal oldali túrák:", "list_bal"), ("Jobb oldali túrák:", "list_jobb")]:
            f = QFrame()
            f.setStyleSheet("QFrame { border: 1px solid #ccc; background: #f9f9f9; border-radius: 5px; }")
            v = QVBoxLayout(f)
            v.addWidget(QLabel(f"<b>{title}</b>"))
            lw = QListWidget()
            lw.setMaximumHeight(100)
            # Itt fontos, hogy ha a betöltés után üres, a setup_ui_content tölti majd fel
            for t in getattr(self, 'osszes_tura_neve', []):
                it = QListWidgetItem(t)
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                it.setCheckState(Qt.CheckState.Unchecked)
                lw.addItem(it)
            setattr(self, attr, lw)
            v.addWidget(lw)
            top_row.addWidget(f)
        main_layout.addLayout(top_row, 0)

        btn_load = QPushButton("🔄 KIJELÖLT TÚRÁK MEGJELENÍTÉSE")
        btn_load.setFixedHeight(35)
        btn_load.setStyleSheet("background-color: #3498db; color: white; font-weight: bold;")
        btn_load.clicked.connect(self.adatok_betoltese)
        main_layout.addWidget(btn_load)

        # --- ÚJ: TÚRA LÉTREHOZÁSA SZEKCIÓ ---
        uj_tura_frame = QFrame()
        uj_tura_frame.setStyleSheet("QFrame { background-color: #fcf3cf; border: 1px solid #f39c12; border-radius: 5px; }")
        uj_tura_layout = QHBoxLayout(uj_tura_frame)
        
        self.uj_tura_nev_input = QLineEdit()
        self.uj_tura_nev_input.setPlaceholderText("Új túra neve (pl. Budapest Páros)")
        self.uj_tura_nev_input.setFixedHeight(30)
        self.uj_tura_nev_input.setStyleSheet("background: white; border: 1px solid #ccc;")
        
        btn_uj_tura = QPushButton("➕ ÚJ TÚRA")
        btn_uj_tura.setFixedWidth(120)
        btn_uj_tura.setFixedHeight(30)
        btn_uj_tura.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold;")
        btn_uj_tura.clicked.connect(self.uj_tura_letrehozasa_esemeny)
        
        uj_tura_layout.addWidget(QLabel("<b>Új túra hozzáadása:</b>"))
        uj_tura_layout.addWidget(self.uj_tura_nev_input)
        uj_tura_layout.addWidget(btn_uj_tura)
        main_layout.addWidget(uj_tura_frame)

        # --- Ezután jön a DRAGGABLE TREES rész ---

        # --- DRAGGABLE TREES (BAL ÉS JOBB) ---
        h_trees = QHBoxLayout()
        self.tree_bal = DraggableTree(self)
        self.tree_jobb = DraggableTree(self)
        
        for t in [self.tree_bal, self.tree_jobb]:
            t.setColumnCount(3)
            t.setHeaderLabels(["Partner / Tétel", "Intenzitás / Db", "Súly"])
            t.setColumnWidth(0, 400) # Elég hely az ikonoknak és a fának
            t.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            
            # Drag & Drop viselkedés szabályozása
            t.setDragEnabled(True)
            t.setAcceptDrops(True)
            t.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
            t.setDropIndicatorShown(True)
            t.setIndentation(20) # Látható legyen a fa eltolása
            
            h_trees.addWidget(t)
        
        main_layout.addLayout(h_trees, 1)

        btn_save = QPushButton("💾 VÁLTOZÁSOK VÉGLEGESÍTÉSE")
        btn_save.setFixedHeight(50)
        btn_save.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        btn_save.clicked.connect(self.mentes_es_vissza)
        main_layout.addWidget(btn_save)

    def uj_tura_letrehozasa_esemeny(self):
        uj_nev = self.uj_tura_nev_input.text().strip()
        
        if not uj_nev:
            return
            
        if uj_nev in self.osszes_tura_neve:
            self.uj_tura_nev_input.clear()
            return

        # 1. Hozzáadás a belső listához
        self.osszes_tura_neve.append(uj_nev)
        self.osszes_tura_neve.sort()
        
        # 2. Hozzáadás a választó listákhoz (bejelölve)
        for list_widget in [self.list_bal, self.list_jobb]:
            it = QListWidgetItem(uj_nev)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            it.setCheckState(Qt.CheckState.Checked) 
            list_widget.addItem(it)
            
        self.uj_tura_nev_input.clear()
        
        # 3. Frissítés, hogy megjelenjen az üres túra a fában
        self.adatok_betoltese()


    def aktualis_betoltese_fajlbol(self):
        import os, pandas as pd, json, io, time, shutil, uuid
        from PyQt6.QtWidgets import QMessageBox, QFileDialog

        # 1. Tallózás (vagy alapértelmezett)
        path, _ = QFileDialog.getOpenFileName(self, "Túra betöltése", "", "Excel Files (*.xlsx)")
        if not path: return

        # Cache elkerülése egyedi ideiglenes fájllal
        temp_path = f"temp_read_{uuid.uuid4().hex}.xlsx"

        try:
            shutil.copy2(path, temp_path)
            with open(temp_path, "rb") as f:
                df = pd.read_excel(io.BytesIO(f.read()), engine='openpyxl')
            
            # Töröljük a temp fájlt azonnal
            if os.path.exists(temp_path): os.remove(temp_path)

            friss_adatok = []
            for _, row in df.iterrows():
                p = row.to_dict()
                # JSON visszaalakítás
                if 'Tetel_JSON_FIX' in p and isinstance(p['Tetel_JSON_FIX'], str):
                    try: p['Tetel'] = json.loads(p['Tetel_JSON_FIX'])
                    except: p['Tetel'] = []
                elif 'Tetel' not in p:
                    p['Tetel'] = []
                
                # IRSZ tisztítás (hogy ne legyen .0 hiba)
                if 'IRSZ' in p:
                    p['IRSZ'] = str(p['IRSZ']).replace('.0', '').strip()
                
                friss_adatok.append(p)

            # --- A LEGFONTOSABB RÉSZ: TELJES MEMÓRIA-CSERE ---
            # Kiürítjük a főprogram listáját és feltöltjük az Excel tartalmával
            self.main_parent.minden_partner_adat.clear()
            self.main_parent.minden_partner_adat.extend(friss_adatok)

            # GUI ürítése és a választható túrák (Autó - Nap) kigyűjtése a fájlból
            self.tree_bal.clear()
            self.tree_jobb.clear()
            self.setup_ui_content() 

            QMessageBox.information(self, "Siker", f"Betöltve: {len(friss_adatok)} partner.\nAz autók és napok listája frissült!")

        except Exception as e:
            if os.path.exists(temp_path): os.remove(temp_path)
            QMessageBox.critical(self, "Hiba", f"Beolvasási hiba: {e}")

        
    def setup_ui_content(self):
        # Ürítjük a választó listákat
        self.list_bal.clear()
        self.list_jobb.clear()

        uj_turak = set()
        for p in self.main_parent.minden_partner_adat:
            t_nev = str(p.get('Túra', 'KIOSZTATLAN'))
            if t_nev and t_nev != 'nan':
                uj_turak.add(t_nev)

        # ABC sorrendben feltöltjük a listákat az új túranevekkel
        for t in sorted(list(uj_turak)):
            for lw in [self.list_bal, self.list_jobb]:
                it = QListWidgetItem(t)
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                it.setCheckState(Qt.CheckState.Unchecked) # NINCS AUTOMATIKUS PIPA
                lw.addItem(it)

    def partner_sor_letrehozas(self, parent_item, p):
        # DEBUG kiegészítve a túra nevével
        print(f"DEBUG RAJZOLÁS: {p['Partner']} - {p.get('Túra')}")
        
        p_item = QTreeWidgetItem(parent_item)
        p_nev = str(p.get('Partner', 'Ismeretlen')).replace('\n', ' ')
        p_statusz = str(p.get('Statusz', '')).upper()
        p_cim = str(p.get('Cim', 'Nincs cím')).replace('\n', ' ')

        # ÚJ partner kékkel + címmel
        if p_statusz == 'ÚJ':
            p_item.setText(0, f"✨ [ÚJ] {p_nev} ({p_cim})")
            p_item.setForeground(0, QColor("#3498db"))
        else:
            p_item.setText(0, f"👤 {p_nev}")

        p_item.setText(1, str(p.get('Intenz', '')))
        p_item.setText(2, f"{int(p.get('Alap_B', 0))} kg")
        
        p_font = QFont()
        p_font.setBold(True)
        p_item.setFont(0, p_font)
        
        # ADATOK TÁROLÁSA
        p_item.setData(0, Qt.ItemDataRole.UserRole, "PARTNER")
        # Nagyon fontos: a mentés funkció a data(1, ...) részt nézi!
        p_item.setData(1, Qt.ItemDataRole.UserRole, p) 

        # DRAG & DROP FIX: 
        # Csak ItemIsDragEnabled van, NINCS ItemIsDropEnabled! 
        # Így nem tudod a partnerbe "belepottyantani" a másikat.
        p_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled)
        
        p_item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)

        # TÉTELEK LISTÁZÁSA A JSON-BŐL
        tetelek = p.get('Tetel', [])
        if not tetelek:
            json_adat = p.get('Tetel_JSON_FIX', '')
            if isinstance(json_adat, str) and json_adat.strip():
                try:
                    # Itt olvassuk be a JSON-t az Excel cellából
                    tetelek = json.loads(json_adat)
                except:
                    tetelek = []

        if not tetelek:
            t_item = QTreeWidgetItem(p_item)
            t_item.setText(0, f"   📍 {p_cim}")
            t_item.setData(0, Qt.ItemDataRole.UserRole, "TETEL")
        else:
            for t_adat in tetelek:
                t_item = QTreeWidgetItem(p_item)
                
                # --- JAVÍTÁS A JSON KULCSOKHOZ ---
                # Megnézzük a 'nev' kulcsot, ha nincs, a 'Megnevezés'-t (ÚJ partnerekhez)
                t_nev = t_adat.get('nev') or t_adat.get('Megnevezés') or 'Ismeretlen termék'
                
                # Megnézzük a 'db' kulcsot, ha nincs, a 'Mennyiség'-et
                t_db = t_adat.get('db') or t_adat.get('Mennyiség') or 0
                
                # Megnézzük a 'suly' kulcsot, ha nincs, a 'Súly'-t
                t_suly = t_adat.get('suly') or t_adat.get('Súly') or 0
                
                t_item.setText(0, f"   📦 {t_nev}")
                t_item.setText(1, f"{t_db} db")
                t_item.setText(2, f"{int(t_suly)} kg")
                
                t_item.setData(0, Qt.ItemDataRole.UserRole, "TETEL")
                t_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)

        return p_item
    
    def is_active_on_week(self, intenzitas, het_idx):
        # het_idx: 0=Mind, 1=Páratlan, 2=Páros
        if het_idx == 0: return True
    
        s = str(intenzitas).upper()
    
        # HETI: minden héten ott van
        if "HETI" in s and "2" not in s and "KÉTHETI" not in s: 
           return True
    
        # PÁRATLAN szűrés
        if het_idx == 1:
           return any(x in s for x in ["PÁRATLAN", "1", "1+3"])
    
        # PÁROS szűrés
        if het_idx == 2:
           return any(x in s for x in ["PÁROS", "2", "2+4"])
        
        return False
  
    def is_active_on_week(self, intenzitas, het_idx):
        """
        Eldönti, hogy az adott intenzitás alapján a partner aktív-e az adott héten.
        intenzitas: pl. '1+3', '2+4', 'Páratlan', 'Páros', 'Minden héten' vagy üres
        het_idx: 1, 2, 3 vagy 4
        """
        if not intenzitas or intenzitas == "" or "minden" in intenzitas.lower():
           return True
    
        intenzitas = intenzitas.replace(" ", "")
    
        # Konkrét hetek kezelése (pl. 1+3)
        if "+" in intenzitas:
           hetek = intenzitas.split("+")
           return str(het_idx) in hetek

        # Szöveges típusok kezelése
        if "páratlan" in intenzitas.lower():
           return het_idx in [1, 3]
        if "páros" in intenzitas.lower():
           return het_idx in [2, 4]
        
        # Ha csak egy szám van megadva
        if intenzitas.isdigit():
           return int(intenzitas) == het_idx

        return True


    def adatok_betoltese(self):
        self.tree_bal.clear()
        self.tree_jobb.clear()
        het_idx = self.combo_het.currentIndex()

        print(f"DEBUG: Hét váltva, aktuális index: {het_idx}")

        # Kijelöltek begyűjtése
        kijelolt_bal = [self.list_bal.item(i).text() for i in range(self.list_bal.count()) if self.list_bal.item(i).checkState() == Qt.CheckState.Checked]
        kijelolt_jobb = [self.list_jobb.item(i).text() for i in range(self.list_jobb.count()) if self.list_jobb.item(i).checkState() == Qt.CheckState.Checked]

        # Fordított sorrend az adatoknál, ha szükséges
        friss_lista = list(reversed(self.main_parent.minden_partner_adat))
        
        # A két panel (fa) és a hozzájuk tartozó kijelölt túrák feldolgozása
        for tree, kijeloltek in [(self.tree_bal, kijelolt_bal), (self.tree_jobb, kijelolt_jobb)]:
            for t_nev in kijeloltek:
                # --- ÁTLAG ÉS SÚLY KISZÁMÍTÁSA ---
                # Megkeressük a túrához tartozó partnereket az összesített súlyhoz és az átlaghoz
                tura_partnerei = [p for p in friss_lista if str(p.get('Túra', '')).replace('.0', '').strip() == t_nev.strip()]
                
                atlag_megallo = 0
                pillanatnyi_suly = 0
                if tura_partnerei:
                    # Az átlag megállót az első partnertől vesszük (mert az Excel mentésnél mindenkié ugyanaz)
                    atlag_megallo = tura_partnerei[0].get('Atlag_Megallo', 0)
                    # A pillanatnyi súlyt pedig összeadjuk
                    pillanatnyi_suly = sum(float(p.get('Alap_B', 0)) for p in tura_partnerei)

                # Létrehozzuk a TÚRA (ROOT) elemet
                root = QTreeWidgetItem(tree)
                root.setText(0, f"🚚 {t_nev}")
                # Itt állítjuk be az átlagot és a súlyt az oszlopokba:
                root.setText(1, f"Átlag: {atlag_megallo} cím")
                root.setText(2, f"{int(pillanatnyi_suly)} kg")
                
                root.setData(0, Qt.ItemDataRole.UserRole, "TURA")
                root.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDropEnabled)
                
                # Színek és stílus
                for col in range(3):
                    root.setBackground(col, QColor("#dfe6e9"))
                
                # Piros szín, ha a pillanatnyi megállószám (nem az átlag!) több mint 25
                if len(tura_partnerei) > 25:
                    root.setForeground(0, QColor("#e74c3c"))

                # Partnerek hozzáadása (VÁLTOZATLAN)
                for p in tura_partnerei:
                    # 1. Heti szűrés
                    if het_idx != 0 and not self.is_active_on_week(p.get('Intenz', ''), het_idx):
                        continue
                    self.partner_sor_letrehozas(root, p)
                
                root.setExpanded(False)
        
        # Súlyok újraszámolása a betöltés végén
        if hasattr(self, 'suly_frissites'):
            self.suly_frissites()


    def suly_frissites(self):
        for tree in [self.tree_bal, self.tree_jobb]:
            for i in range(tree.topLevelItemCount()):
                root = tree.topLevelItem(i)
                if root.data(0, Qt.ItemDataRole.UserRole) != "TURA":
                    continue

                t_nev_aktualis = root.text(0).replace("🚚 ", "").strip()

                # --- 1. ALAP SÚLY KERESÉSE ---
                alap_suly_atlag = 0
                t_nev_aktualis = root.text(0).replace("🚚 ", "").strip()
                
                # Végigmegyünk a partnereken, és keressük a túra eredeti átlagsúlyát
                for j in range(root.childCount()):
                    p_adat = root.child(j).data(1, Qt.ItemDataRole.UserRole)
                    if p_adat and p_adat.get('Statusz') == 'RÉGI':
                        # Megnézzük, hogy ez a partner eredetileg ehhez a túrához tartozott-e
                        p_t_eredeti = str(p_adat.get('Túra', '')).replace('.0', '').strip()
                        
                        # Ha van egyezés, kinyerjük az Alap_B-t (ami a túra átlaga)
                        if p_t_eredeti == t_nev_aktualis:
                            s_ertek = float(p_adat.get('Alap_B', 0) or 0)
                            # Csak akkor fogadjuk el, ha reális túrasúly (pl. > 100 kg)
                            if s_ertek > 100:
                                alap_suly_atlag = s_ertek
                                break # Megvan az alap, mehetünk a következő lépésre

                # --- 1. ALAP ÁTLAGOK KINYERÉSE (Megálló és Súly) ---
                alap_megallo_atlag = 0
                alap_suly_atlag = 0
                
                for j in range(root.childCount()):
                    p_adat = root.child(j).data(1, Qt.ItemDataRole.UserRole)
                    if p_adat and 'Atlag_Megallo' in p_adat:
                        p_t_eredeti = str(p_adat.get('Túra', '')).replace('.0', '').strip()
                        if p_t_eredeti == t_nev_aktualis:
                            # Megálló átlag (B oszlop)
                            alap_megallo_atlag = float(p_adat['Atlag_Megallo'])
                            # Súly átlag (G oszlop - Alap_B-ként mentve a szétosztásnál)
                            # Feltételezzük, hogy az 'Alap_B' a régi partnereknél a túra átlaga volt mentéskor
                            alap_suly_atlag = float(p_adat.get('Alap_B', 0))
                            break

                # --- 2. VÁLTOZÁSOK SZÁMÍTÁSA (Csak az ÚJ partnerek alapján) ---
                uj_megallok_szama = 0
                uj_partnerek_sulya = 0
                
                # Ha alap_atlag 0, akkor mindenki számít, ha nem 0, akkor csak az ÚJAK
                for j in range(root.childCount()):
                    item = root.child(j)
                    if item.data(0, Qt.ItemDataRole.UserRole) == "PARTNER":
                        p_adat = item.data(1, Qt.ItemDataRole.UserRole)
                        is_uj = str(p_adat.get('Statusz', '')).upper() == 'ÚJ'
                        
                        if alap_megallo_atlag == 0: # Új manuális túra esetén mindenki számít
                            uj_megallok_szama += 1
                            uj_partnerek_sulya += float(p_adat.get('Alap_B', 0))
                        elif is_uj: # Régi túra esetén csak az ÚJ partner módosít
                            uj_megallok_szama += 1
                            uj_partnerek_sulya += float(p_adat.get('Alap_B', 0))

                # --- 3. MEGJELENÍTÉS FRISSÍTÉSE ---
                
                # A MEGÁLLÓKHOZ NEM NYÚLTUNK (maradt a korábbi működő logika)
                vegleges_megallo = int(round(alap_megallo_atlag + uj_megallok_szama))
                root.setText(1, f"Átlag: {vegleges_megallo} cím")

                # A SÚLY most már követi ugyanezt az elvet
                # Régi túra átlagsúlya + az új partnerek súlya
                vegleges_suly = int(round(alap_suly_atlag + uj_partnerek_sulya))
                root.setText(2, f"Össz: {vegleges_suly} kg")

                # Színezés a megálló alapján (Változatlan)
                if vegleges_megallo > 25:
                    root.setForeground(1, QColor("#e74c3c"))
                else:
                    root.setForeground(1, QColor("black"))

    def mentes_es_vissza(self):
        try:
            import json
            import pandas as pd

            # 1. ADATOK ÖSSZEGYŰJTÉSE A FÁKBÓL
            frissitett_lista = []
            
            # Végigmegyünk mindkét fán (bal és jobb)
            for tree in [self.tree_bal, self.tree_jobb]:
                # Végigmegyünk a túrákon (root elemek)
                for i in range(tree.topLevelItemCount()):
                    tura_item = tree.topLevelItem(i)
                    # Kiszedjük a túra nevét az ikon nélkül (pl. "1. autó - Hétfő")
                    tura_nev = tura_item.text(0).replace("🚚 ", "").strip()
                    
                    # Végigmegyünk a túra alatti partnereken
                    for j in range(tura_item.childCount()):
                        partner_item = tura_item.child(j)
                        # A setData-val korábban elmentett eredeti partner objektumot kérjük le
                        p_adat = partner_item.data(1, Qt.ItemDataRole.UserRole)
                        
                        if p_adat:
                            # Frissítjük a túra nevét arra, amilyen mappa alatt most van
                            p_adat['Túra'] = tura_nev
                            frissitett_lista.append(p_adat)

            # 2. SZINKRONIZÁCIÓ A FŐPROGRAMMAL
            # Csak azokat írjuk felül, amiket szerkesztettünk
            # (Vagy a teljes listát cseréljük, ha mindenkit betöltöttünk)
            if frissitett_lista:
                self.main_parent.minden_partner_adat = frissitett_lista

            # 3. MENTÉS EXCELBE (hogy megmaradjon a kézi sorrend)
            path, _ = QFileDialog.getSaveFileName(self, "Szerkesztett túra mentése", "Tura_Terv_Szerkesztett.xlsx", "Excel (*.xlsx)")
            
            if path:
                df_save = pd.DataFrame(frissitett_lista)
                if 'Tetel' in df_save.columns:
                    df_save['Tetel_JSON_FIX'] = df_save['Tetel'].apply(lambda x: json.dumps(x))
                    df_save = df_save.drop(columns=['Tetel'])
                
                df_save.to_excel(path, index=False)
                QMessageBox.information(self, "Siker", "A módosítások mentve a fájlba és a memóriába is!")
                self.close() # Bezárjuk a szerkesztőt

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            QMessageBox.critical(self, "Hiba", f"Hiba a véglegesítéskor: {e}")

def indit_szerkeszto(parent):
    dialog = KeziszerkesztoAblak(parent)
    return dialog.exec()