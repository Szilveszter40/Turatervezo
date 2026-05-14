import os
import io
import json
import uuid
import shutil
import re
import pandas as pd
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, 
                             QTreeWidgetItem, QLabel, QPushButton, QMessageBox, 
                             QFrame, QHeaderView, QFileDialog, QMenu)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from fixmod_nyomtatas import modul_nyomtatas


class DraggableTree( QTreeWidget):
    """
    Kiterjesztett fa szerkezet, amely kikényszeríti és engedélyezi a teljes
    túrák (TopLevel) és partnerek panelek közötti fizikai mozgatását és másolását.
    """
    def __init__( self, parent= None):
        super(). __init__( parent)
        self. setDragEnabled( True)
        self. setAcceptDrops( True)
        self. setDragDropMode( QTreeWidget. DragDropMode. DragDrop)
        self. setDefaultDropAction( Qt. DropAction. MoveAction)
        self. setSelectionMode( QTreeWidget. SelectionMode. SingleSelection)
        self. setDropIndicatorShown( True)
        self. setIndentation( 20)
        self. setAnimated( True)
        self. setContextMenuPolicy( Qt. ContextMenuPolicy. CustomContextMenu)
        self. customContextMenuRequested. connect( self. show_context_menu)

    def supportedDropActions(self):
        """Engedélyezi a másolást és a mozgatást is a Qt felé"""
        return Qt.DropAction.MoveAction | Qt.DropAction.CopyAction

    def show_context_menu( self, position):
        item = self. itemAt( position)
        if not item: return
        menu = QMenu()
        item_type = item. data( 0, Qt. ItemDataRole. UserRole)
        main_win = self. window()
        if item_type == "TURA":
            if "🗑 töröltek" in item. text( 0). lower(): return
            delete_action = menu. addAction("🗑 Teljes túra törlése")
            action = menu. exec( self. viewport(). mapToGlobal( position))
            if action == delete_action and main_win and hasattr( main_win, 'tura_athelyezese_toroltekbe'):
                main_win. tura_athelyezese_toroltekbe( self, item)
        elif item_type == "PARTNER":
            delete_action = menu. addAction("🗑 Partner törlése")
            action = menu. exec( self. viewport(). mapToGlobal( position))
            if action == delete_action and main_win and hasattr( main_win, 'partner_athelyezese_toroltekbe'):
                main_win. partner_athelyezese_toroltekbe( self, item)

    def dragEnterEvent(self, event):
        if isinstance(event.source(), QTreeWidget):
            main_win = self.window()
            # Ha a KÖZÉPSŐ panelről húzzuk az OLDALSÓKRA, jelezzük a Qt-nak, hogy ez MÁSOLÁS (Copy)
            if event.source() == main_win.tree_kozos and self in [main_win.tree_paratlan, main_win.tree_paros]:
                event.setDropAction(Qt.DropAction.CopyAction)
            else:
                event.setDropAction(Qt.DropAction.MoveAction)
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if isinstance(event.source(), QTreeWidget):
            main_win = self.window()
            if event.source() == main_win.tree_kozos and self in [main_win.tree_paratlan, main_win.tree_paros]:
                event.setDropAction(Qt.DropAction.CopyAction)
            else:
                event.setDropAction(Qt.DropAction.MoveAction)
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        source_tree = event.source()
        if isinstance(source_tree, QTreeWidget):
            selected_items = source_tree.selectedItems()
            if not selected_items:
                return

            target_item = self.itemAt(event.position().toPoint())
            main_win = self.window()
            
            for item in selected_items:
                item_type = item.data(0, Qt.ItemDataRole.UserRole)
                
                if item_type == "TURA" and "🗑 töröltek" in item.text(0).lower(): continue
                if target_item and "🗑 töröltek" in target_item.text(0).lower(): continue

                # 👤 PARTNER MOZGATÁSA (Helyreállított, biztonságos hierarchia-kezeléssel)
                if item_type == "PARTNER":
                    # Eltávolítás a régi helyéről
                    if item.parent(): item.parent().removeChild(item)
                    else: source_tree.invisibleRootItem().removeChild(item)
                    
                    if target_item:
                        target_type = target_item.data(0, Qt.ItemDataRole.UserRole)
                        
                        # 1. Eset: Közvetlenül egy TÚRA fejlécre dobtuk -> bekerül az első helyre
                        if target_type == "TURA":
                            target_item.insertChild(0, item)
                            target_item.setExpanded(True)
                            
                        # 2. Eset: Egy másik PARTNERRE dobtuk -> a túrába kerül, a partner mellé
                        elif target_type == "PARTNER":
                            t_parent = target_item.parent()
                            if t_parent:
                                t_parent.insertChild(t_parent.indexOfChild(target_item), item)
                            else:
                                self.addTopLevelItem(item)
                                
                        # 3. Eset: Egy TÉTELRE (cím/csomag) dobtuk -> megkeressük a fő túrát, oda rakjuk
                        elif target_type == "TETEL":
                            p_parent = target_item.parent() # A tétel szülője (egy partner)
                            if p_parent:
                                t_parent = p_parent.parent() # A partner szülője (a túra)
                                if t_parent:
                                    t_parent.insertChild(t_parent.indexOfChild(p_parent), item)
                                else:
                                    self.addTopLevelItem(item)
                            else:
                                self.addTopLevelItem(item)
                    else:
                        # Ha üres területre dobtuk, a panel legtetejére/aljára szúrja be főelemként
                        self.addTopLevelItem(item)

                # 🚚 KOMPLETT TÚRA MOZGATÁSA ÉS AUTOMATIKUS KÉTOLDALI MÁSOLÁSA (Megtartva)
                elif item_type == "TURA":
                    tura_neve = item.text(0)
                    atlag_megallo = item.text(1)
                    ossz_suly = item.text(2)

                    # Áthelyezzük a túrát az aktuális panelre, ahova dobtuk
                    if item.parent(): item.parent().removeChild(item)
                    else: source_tree.invisibleRootItem().removeChild(item)
                    
                    if target_item:
                        target_root = target_item
                        while target_root.parent(): target_root = target_root.parent()
                        root_node = self.invisibleRootItem()
                        idx = root_node.indexOfChild(target_root)
                        root_node.insertChild(idx, item)
                    else:
                        self.addTopLevelItem(item)
                    item.setExpanded(True)

                    # DUPLIKÁLÁS A TÚLOLDALRA (Csak ha a KÖZÖS listából indult az áthúzás)
                    if source_tree == main_win.tree_kozos and self in [main_win.tree_paratlan, main_win.tree_paros]:
                        tulszo_tree = main_win.tree_paros if self == main_win.tree_paratlan else main_win.tree_paratlan
                        tulszo_root = tulszo_tree.invisibleRootItem()

                        mar_letezik_tulszo = False
                        for i in range(tulszo_root.childCount()):
                            if tulszo_root.child(i).text(0) == tura_neve:
                                mar_letezik_tulszo = True
                                break

                        if not mar_letezik_tulszo:
                            klon_tura = QTreeWidgetItem(tulszo_tree)
                            klon_tura.setText(0, tura_neve)
                            klon_tura.setText(1, atlag_megallo)
                            klon_tura.setText(2, ossz_suly)
                            klon_tura.setData(0, Qt.ItemDataRole.UserRole, "TURA")
                            klon_tura.setFlags(item.flags())
                            for col in range(3): klon_tura.setBackground(col, QColor("#dfe6e9"))

                            for j in range(item.childCount()):
                                eredeti_partner = item.child(j)
                                if eredeti_partner.data(0, Qt.ItemDataRole.UserRole) != "PARTNER": continue

                                klon_partner = QTreeWidgetItem(klon_tura)
                                klon_partner.setText(0, eredeti_partner.text(0))
                                klon_partner.setText(1, eredeti_partner.text(1))
                                klon_partner.setText(2, eredeti_partner.text(2))
                                klon_partner.setFont(0, eredeti_partner.font(0))
                                if eredeti_partner.foreground(0): 
                                    klon_partner.setForeground(0, eredeti_partner.foreground(0))
                                
                                klon_partner.setData(0, Qt.ItemDataRole.UserRole, "PARTNER")
                                p_adat = eredeti_partner.data(1, Qt.ItemDataRole.UserRole)
                                if p_adat: klon_partner.setData(1, Qt.ItemDataRole.UserRole, p_adat.copy())
                                klon_partner.setFlags(eredeti_partner.flags())

                                for k in range(eredeti_partner.childCount()):
                                    eredeti_tetel = eredeti_partner.child(k)
                                    klon_tetel = QTreeWidgetItem(klon_partner)
                                    klon_tetel.setText(0, eredeti_tetel.text(0))
                                    klon_tetel.setText(1, eredeti_tetel.text(1))
                                    klon_tetel.setText(2, eredeti_tetel.text(2))
                                    klon_tetel.setData(0, Qt.ItemDataRole.UserRole, eredeti_tetel.data(0, Qt.ItemDataRole.UserRole))
                                    klon_tetel.setFlags(eredeti_tetel.flags())

                            klon_tura.setExpanded(True)

            event.acceptProposedAction()
            if main_win and hasattr(main_win, 'suly_frissites'):
                main_win.suly_frissites()
        else:
            super().dropEvent(event)

class HetiBontasAblak(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_parent = parent
        self.setWindowTitle("Heti Bontás - Logisztikai Tervező")
        self.setWindowState(Qt.WindowState.WindowMaximized)
        
        self.heti_partner_adatok = []
        self.is_updating = False
        
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # --- 1. FELSŐ VEZÉRLŐSÁV ---
        top_bar_layout = QHBoxLayout()
        
        self.btn_excel_load = QPushButton("📂 EXCEL BETÖLTÉSE")
        self.btn_excel_load.setFixedHeight(45)
        self.btn_excel_load.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold; border-radius: 5px;")
        self.btn_excel_load.clicked.connect(self.excel_beolvasas_heti)
        top_bar_layout.addWidget(self.btn_excel_load, 1)

        self.btn_terkep_megnyit = QPushButton("🗺️ TÉRKÉPES TERVEZŐ")
        self.btn_terkep_megnyit.setFixedHeight(45)
        self.btn_terkep_megnyit.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; border-radius: 5px;")
        self.btn_terkep_megnyit.clicked.connect(self.terkep_modul_inditasa_heti)
        top_bar_layout.addWidget(self.btn_terkep_megnyit, 1)

        self.btn_nyomtatas = QPushButton("📄 NYOMTATÁSI KÉP")
        self.btn_nyomtatas.setFixedHeight(45)
        self.btn_nyomtatas.setStyleSheet("background-color: #34495e; color: white; font-weight: bold; border-radius: 5px;")
        self.btn_nyomtatas.clicked.connect(self.nyomtatas_inditasa)
        top_bar_layout.addWidget(self.btn_nyomtatas, 1)
        
        main_layout.addLayout(top_bar_layout)

        # --- 2. 3 PANEL ELRENDEZÉSE ---
        panels_layout = QHBoxLayout()
        panel_beallitasok = [
            ("Páratlan Hét adatai", "tree_paratlan"),
            ("Közös / Szétosztatlan tételek", "tree_kozos"),
            ("Páros Hét adatai", "tree_paros")
        ]

        for cim, attr_nev in panel_beallitasok:
            panel_frame = QFrame()
            panel_frame.setStyleSheet("QFrame { border: 1px solid #b2bec3; background-color: #f8f9fa; border-radius: 5px; }")
            panel_vbox = QVBoxLayout(panel_frame)
            panel_vbox.setContentsMargins(8, 8, 8, 8)
            
            lbl_cim = QLabel(f"<b>{cim}</b>")
            lbl_cim.setAlignment(Qt.AlignmentFlag.AlignCenter)
            panel_vbox.addWidget(lbl_cim)
            
            tree = DraggableTree(self)
            tree.setColumnCount(3)
            tree.setHeaderLabels(["Partner / Tétel", "Intenzitás / Db", "Súly"])
            tree.setColumnWidth(0, 250)
            tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            
            tree.model().dataChanged.connect(lambda: self.suly_frissites())
            tree.model().rowsInserted.connect(lambda: self.suly_frissites())
            tree.model().rowsRemoved.connect(lambda: self.suly_frissites())
            
            setattr(self, attr_nev, tree)
            panel_vbox.addWidget(tree)
            panels_layout.addWidget(panel_frame, 1)

        main_layout.addLayout(panels_layout, 1)

        # --- 3. ALSÓ SÁV (ÚJ MENTÉS GOMBBAL) ---
        bottom_layout = QHBoxLayout()
        
        # ÚJ MENTÉS GOMB (Bal oldalon, narancs színben)
        self.btn_mentes_excel = QPushButton("💾 AKTUÁLIS ÁLLAPOT MENTÉSE EXCELBE")
        self.btn_mentes_excel.setFixedWidth(320)
        self.btn_mentes_excel.setFixedHeight(40)
        self.btn_mentes_excel.setStyleSheet("background-color: #e67e22; color: white; font-weight: bold; border-radius: 5px;")
        self.btn_mentes_excel.clicked.connect(self.mentes_excelbe_heti)
        bottom_layout.addWidget(self.btn_mentes_excel)

        bottom_layout.addStretch()
        
        self.btn_bezar = QPushButton("❌ BEZÁRÁS")
        self.btn_bezar.setFixedWidth(150)
        self.btn_bezar.setFixedHeight(40)
        self.btn_bezar.setStyleSheet("background-color: #7f8c8d; color: white; font-weight: bold; border-radius: 5px;")
        self.btn_bezar.clicked.connect(self.reject) 
        bottom_layout.addWidget(self.btn_bezar)
        main_layout.addLayout(bottom_layout)

    def nyomtatas_inditasa(self): modul_nyomtatas(self)
    def terkep_modul_inditasa_heti(self):
        try:
            from fixmod_terkep import TerkepTervezoAblak
            self.terkep_ablak = TerkepTervezoAblak(self)
            self.terkep_ablak.exec()
        except Exception as e: QMessageBox.critical(self, "Hiba", f"Hiba: {e}")

    # =====================================================================
    # 🗂️ TÖRÖLTEK MAPPA GENERÁLÁSA ÉS DINAMIKUS TÖRLESEK
    # =====================================================================
    def _toroltek_csomopont_lekerese(self):
        """Megkeresi vagy létrehozza a Töröltek gyűjtőt a középső panelen."""
        tree = self.tree_kozos
        root = tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if "🗑️ töröltek" in item.text(0).lower():
                return item
        
        # Ha nincs, létrehozzuk szürke dizájnnal
        toroltek = QTreeWidgetItem(tree)
        toroltek.setText(0, "🚚 🗑️ TÖRÖLTEK (Archív)")
        toroltek.setText(1, "Átlag: 0 cím")
        toroltek.setText(2, "0 kg")
        toroltek.setData(0, Qt.ItemDataRole.UserRole, "TURA")
        toroltek.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDropEnabled)
        for col in range(3): toroltek.setBackground(col, QColor("#b2bec3"))
        return toroltek

    def tura_athelyezese_toroltekbe(self, source_tree, tura_item):
        """A jobb klikkel kijelölt teljes túrát bepakolja a Töröltek alá."""
        toroltek_node = self._toroltek_csomopont_lekerese()
        
        # Átrakjuk a partnereket a töröltek alá
        while tura_item.childCount() > 0:
            p_child = tura_item.takeChild(0)
            toroltek_node.addChild(p_child)
            
        # Magát a túra üres héját töröljük a felületről
        (tura_item.parent() or source_tree.invisibleRootItem()).removeChild(tura_item)
        self.suly_frissites()
        QMessageBox.information(self, "Törlés", "A túra partnerei az archívumba kerültek.")

    def partner_athelyezese_toroltekbe(self, source_tree, partner_item):
        """Egyetlen partner áthelyezése a Töröltek gyűjtőtúrába."""
        toroltek_node = self._toroltek_csomopont_lekerese()
        (partner_item.parent() or source_tree.invisibleRootItem()).removeChild(partner_item)
        toroltek_node.addChild(partner_item)
        self.suly_frissites()

    def suly_frissites(self):
        if self.is_updating: return
        self.is_updating = True
        try:
            for tree in [self.tree_paratlan, self.tree_kozos, self.tree_paros]:
                root = tree.invisibleRootItem()
                for i in range(root.childCount()):
                    tura_item = root.child(i)
                    if tura_item.data(0, Qt.ItemDataRole.UserRole) == "TURA":
                        uj_szumma_suly = 0.0
                        for j in range(tura_item.childCount()):
                            partner_item = tura_item.child(j)
                            if partner_item.data(0, Qt.ItemDataRole.UserRole) == "PARTNER":
                                suly_szoveg = partner_item.text(2)
                                tisztitott_suly = re.sub(r'[^\d.,]', '', suly_szoveg).replace(',', '.')
                                try: uj_szumma_suly += float(tisztitott_suly) if '.' in tisztitott_suly else int(tisztitott_suly)
                                except: pass
                        tura_item.setText(2, f"{int(uj_szumma_suly)} kg")
                        if tura_item.childCount() > 25 and "töröltek" not in tura_item.text(0).lower():
                            tura_item.setForeground(0, QColor("#e74c3c"))
                        else: tura_item.setForeground(0, QColor("#2c3e50"))
        finally: self.is_updating = False

        # =====================================================================
    # JAVÍTOTT: EXCEL EXPORT (AZ AKTUÁLIS ÁLLAPOT MENTÉSE)
    # =====================================================================
    def mentes_excelbe_heti(self):
        path, _ = QFileDialog.getSaveFileName(self, "Állapot mentése", "Heti_Bontas_Mentve.xlsx", "Excel Files (*.xlsx)")
        if not path: return

        mentendo_sorok = []
        
        # A változó neve itt 'panelek'
        panelek = [
            (self.tree_paratlan, "Páratlan"),
            (self.tree_kozos, "Közös"),
            (self.tree_paros, "Páros")
        ]

        # JAVÍTÁS: Most már hajszálpontosan a 'panelek' változón megy végig a ciklus
        for tree, panel_nev in panelek:
            root = tree.invisibleRootItem()
            for i in range(root.childCount()):
                t_item = root.child(i)
                if t_item.data(0, Qt.ItemDataRole.UserRole) != "TURA": continue
                
                is_torolt_group = "🗑️ töröltek" in t_item.text(0).lower()
                t_nev_mentes = t_item.text(0).replace("🚚", "").replace("🗑️ TÖRÖLTEK (Archív)", "TÖRÖLTEK").strip()

                for j in range(t_item.childCount()):
                    p_item = t_item.child(j)
                    if p_item.data(0, Qt.ItemDataRole.UserRole) != "PARTNER": continue
                    
                    p_adat = p_item.data(1, Qt.ItemDataRole.UserRole) or {}
                    
                    p_adat['Túra neve'] = t_nev_mentes
                    p_adat['Heti_Panel_Statusz'] = "TOROLT" if is_torolt_group else panel_nev
                    
                    if 'Tetel' in p_adat:
                        p_adat['Tetel_JSON_FIX'] = json.dumps(p_adat['Tetel'])

                    mentendo_sorok.append(p_adat)

        if not mentendo_sorok:
            QMessageBox.warning(self, "Mentés", "Nincs menthető adat a táblázatokban!")
            return

        try:
            df_ment = pd.DataFrame(mentendo_sorok)
            column_mapping = {
                'Súly': 'A', 'Átlag megálló': 'B', 'Irányítószám': 'D', 
                'Intenzitás': 'E', 'Db szám': 'F', 'Partner státusza': 'H',
                'Tetel_JSON_FIX': 'I', 'Túra neve': 'J'
            }
            for k, v in column_mapping.items():
                if k in df_ment.columns: df_ment[v] = df_ment[k]

            df_ment.to_excel(path, index=False, engine='openpyxl')
            QMessageBox.information(self, "Mentés", "Az aktuális heti elrendezés sikeresen elmentve!")
        except Exception as e:
            QMessageBox.critical(self, "Hiba", f"Nem sikerült menteni az Excelt:\n{e}")

    # =====================================================================
    # 📂 EXCEL VISSZATÖLTÉSE (KIEGÉSZÍTVE A MENTETT MODULLAL)
    # =====================================================================
    def excel_beolvasas_heti(self):
        path, _ = QFileDialog.getOpenFileName(self, "Heti adatok betöltése", "", "Excel Files (*.xlsx)")
        if not path: return

        temp_path = f"temp_read_heti_{uuid.uuid4().hex}.xlsx"
        self.is_updating = True
        try:
            shutil.copy2(path, temp_path)
            with open(temp_path, "rb") as f:
                df = pd.read_excel(io.BytesIO(f.read()), engine='openpyxl')
            if os.path.exists(temp_path): os.remove(temp_path)

            self.tree_paratlan.clear()
            self.tree_kozos.clear()
            self.tree_paros.clear()
            
            turak_szotar = {}
            for _, row in df.iterrows():
                p = row.to_dict()
                t_nev = str(p.get('Túra neve') or p.get('Túra') or p.get('J', 'ISMERETLEN TÚRA')).strip()
                if t_nev.lower() in ['nan', '', 'none']: t_nev = 'ISMERETLEN TÚRA'
                
                p_nev = str(p.get('Partner', ''))
                p_cim = str(p.get('Cim', ''))
                p_id = f"{p_nev}_{p_cim}".strip()
                if not p_id or p_id == "_": continue

                uj_tetelek = []
                json_adat = p.get('Tetel_JSON_FIX')
                if isinstance(json_adat, str) and json_adat.strip():
                    try: uj_tetelek = json.loads(json_adat)
                    except: pass
                p['Tetel'] = uj_tetelek

                if 'IRSZ' in p: p['IRSZ'] = str(p['IRSZ']).replace('.0', '').strip()

                if t_nev not in turak_szotar:
                    turak_szotar[t_nev] = {'partnerek': {}, 'mentett_panel': p.get('Heti_Panel_Statusz', '')}
                
                if p_id in turak_szotar[t_nev]['partnerek']:
                    if uj_tetelek: turak_szotar[t_nev]['partnerek'][p_id]['Tetel'].extend(uj_tetelek)
                else: turak_szotar[t_nev]['partnerek'][p_id] = p

            # Kirajzolás a mentett panelállapot figyelembevételével
            for t_nev, t_adat in turak_szotar.items():
                partnerek_listaja = list(t_adat['partnerek'].values())
                if not partnerek_listaja: continue

                ossz_suly = sum(float(p.get('Súly') or p.get('Alap_B') or p.get('A', 0)) for p in partnerek_listaja)
                atlag_megallo = 0
                for p in partnerek_listaja:
                    m_ertek = p.get('Átlag megálló') or p.get('Atlag_Megallo') or p.get('B')
                    if m_ertek and str(m_ertek).lower() != 'nan':
                        atlag_megallo = m_ertek
                        break

                # Panel kiválasztása: Először a mentett státuszt nézzük, ha az nincs, akkor a nevet
                m_statusz = str(t_adat['mentett_panel']).upper()
                if m_statusz == "PARATLAN": target_tree = self.tree_paratlan
                elif m_statusz == "PAROS": target_tree = self.tree_paros
                elif m_statusz == "TOROLT" or t_nev == "TÖRÖLTEK":
                    target_tree = self.tree_kozos
                    # Automatikusan a töröltek csomópontot adjuk meg célként
                    root_item = self._toroltek_csomopont_lekerese()
                else:
                    t_nev_kisbetus = t_nev.lower()
                    if 'páratlan' in t_nev_kisbetus or 'paratlan' in t_nev_kisbetus: target_tree = self.tree_paratlan
                    elif 'páros' in t_nev_kisbetus or 'paros' in t_nev_kisbetus: target_tree = self.tree_paros
                    else: target_tree = self.tree_kozos

                # Ha nem a töröltek listáról van szó, létrehozzuk a normál túrafejlécet
                if m_statusz != "TOROLT" and t_nev != "TÖRÖLTEK":
                    root_item = QTreeWidgetItem(target_tree)
                    root_item.setText(0, f"🚚 {t_nev}")
                    root_item.setText(1, f"Átlag: {atlag_megallo} cím")
                    root_item.setText(2, f"{int(ossz_suly)} kg")
                    # ÚJ, JAVÍTOTT SOROK (Engedélyezi a túra megfogását és vonszolását is):
                    root_item.setData(0, Qt.ItemDataRole.UserRole, "TURA")
                    root_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDropEnabled | Qt.ItemFlag.ItemIsDragEnabled)

                    for col in range(3): root_item.setBackground(col, QColor("#dfe6e9"))

                # Partnerek berakása
                for p in partnerek_listaja:
                    p_item = QTreeWidgetItem(root_item)
                    p_nev = str(p.get('Partner', 'Ismeretlen'))
                    p_statusz = str(p.get('Partner statusza') or p.get('Statusz') or p.get('H', '')).upper().strip()
                    p_cim = str(p.get('Cim') or p.get('Cím', 'Nincs cím'))
                    
                    if 'ÚJ' in p_statusz:
                        p_item.setText(0, f"✨ [ÚJ] {p_nev} ({p_cim})")
                        p_item.setForeground(0, QColor("#3498db"))
                    else: p_item.setText(0, f"👤 {p_nev}")

                    p_item.setText(1, str(p.get('Intenzitás') or p.get('Intenz', '')))
                    p_item.setText(2, f"{int(p.get('Súly') or p.get('Alap_B') or p.get('A', 0))} kg")
                    
                    p_font = QFont(); p_font.setBold(True); p_item.setFont(0, p_font)
                    p_item.setData(0, Qt.ItemDataRole.UserRole, "PARTNER")
                    p_item.setData(1, Qt.ItemDataRole.UserRole, p)
                    p_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled)

                    tetelek = p.get('Tetel', [])
                    if not tetelek:
                        t_item = QTreeWidgetItem(p_item)
                        t_item.setText(0, f" 📍 {p_cim}")
                        t_item.setData(0, Qt.ItemDataRole.UserRole, "TETEL")
                    else:
                        for t in tetelek:
                            t_item = QTreeWidgetItem(p_item)
                            t_item.setText(0, f" 📦 {t.get('nev') or t.get('Megnevezés') or 'Termék'}")
                            t_item.setText(1, str(t.get('db') or t.get('Mennyiség') or p.get('Db szám', 0)))
                            t_item.setText(2, f"{int(t.get('suly') or t.get('Súly') or 0)} kg")
                            t_item.setData(0, Qt.ItemDataRole.UserRole, "TETEL")
                            t_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)

                if m_statusz != "TOROLT" and t_nev != "TÖRÖLTEK":
                    root_item.setExpanded(False)

            self.is_updating = False
            self.suly_frissites()
            QMessageBox.information(self, "Siker", "Az adatok (és az archívum) sikeresen betöltve!")
        except Exception as e:
            self.is_updating = False
            QMessageBox.critical(self, "Hiba", f"Hiba: {e}")
