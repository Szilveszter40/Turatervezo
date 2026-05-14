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
from PyQt6.QtCore import Qt, QTimer
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
            raw_selected = source_tree.selectedItems()
            if not raw_selected:
                return

            # Kizárólag a legfelső szintű elemeket engedjük át
            selected_items = []
            for item in raw_selected:
                p_curr = item.parent()
                is_child_of_selected = False
                while p_curr:
                    if p_curr in raw_selected:
                        is_child_of_selected = True
                        break
                    p_curr = p_curr.parent()
                if not is_child_of_selected:
                    selected_items.append(item)

            target_item = self.itemAt(event.position().toPoint())
            main_win = self.window()

            for item in selected_items:
                item_type = item.data(0, Qt.ItemDataRole.UserRole)
                
                if item_type == "TURA" and "🗑 töröltek" in item.text(0).lower(): continue
                if target_item and "🗑 töröltek" in target_item.text(0).lower(): continue

                # 👤 PARTNER MOZGATÁSA (Garantáltan stabil, klónozásos technika)
                if item_type == "PARTNER":
                    target_tura = None
                    insert_idx = 0
                    
                    # 1. LÉPÉS: Pozíció kiszámítása, amíg minden elem a fix helyén van
                    if target_item:
                        target_type = target_item.data(0, Qt.ItemDataRole.UserRole)
                        
                        if target_type == "TURA":
                            target_tura = target_item
                            insert_idx = 0  # A túra legtetejére szúrja be
                        elif target_type == "PARTNER":
                            target_tura = target_item.parent()
                            if target_tura:
                                insert_idx = target_tura.indexOfChild(target_item)  # Pontosan FÖLÉ
                        elif target_type == "TETEL":
                            p_parent = target_item.parent()
                            if p_parent:
                                target_tura = p_parent.parent()
                                if target_tura:
                                    insert_idx = target_tura.indexOfChild(p_parent)

                    # Ha üres térre dobtuk, a cél panel legtetejére kerül
                    if not target_tura:
                        insert_idx = self.topLevelItemCount()

                    # 2. LÉPÉS: Biztonsági jelzés-blokkolás az elcsúszások ellen
                    source_tree.blockSignals(True)
                    self.blockSignals(True)

                    try:
                        # 3. LÉPÉS: Biztonságos KLÓNOZÁS a memóriahibák elkerülésére
                        klon_partner = item.clone()
                        
                        # Ha a közös panelből húzzuk át egy oldalsó heti panelbe, frissítjük a belső státuszt
                        if source_tree == main_win.tree_kozos and self in [main_win.tree_paratlan, main_win.tree_paros]:
                            p_panel_nev = "PARATLAN" if self == main_win.tree_paratlan else "PAROS"
                            p_adat = klon_partner.data(1, Qt.ItemDataRole.UserRole)
                            if isinstance(p_adat, dict):
                                p_adat_uj = p_adat.copy()
                                p_adat_uj['Heti_Panel_Statusz'] = p_panel_nev
                                klon_partner.setData(1, Qt.ItemDataRole.UserRole, p_adat_uj)

                        # 4. LÉPÉS: A klón beszúrása a kiszámolt pontos indexre
                        if target_tura:
                            target_tura.insertChild(insert_idx, klon_partner)
                        else:
                            self.insertTopLevelItem(insert_idx, klon_partner)

                        # 5. LÉPÉS: Az eredeti régi elem fizikai megsemmisítése a forrásból
                        old_parent = item.parent()
                        if old_parent:
                            idx = old_parent.indexOfChild(item)
                            if idx != -1: old_parent.takeChild(idx)
                        else:
                            idx = source_tree.indexOfTopLevelItem(item)
                            if idx != -1: source_tree.takeTopLevelItem(idx)

                    finally:
                        # Jelzések visszakapcsolása
                        source_tree.blockSignals(False)
                        self.blockSignals(False)

                    # 🎯 A legfontosabb rész: Megmondjuk a Qt-nak, hogy KÉZZEL elintéztük, 
                    # ne csináljon semmi automatikus dolgot a háttérben, ami eltüntetné az elemet.
                    event.setDropAction(Qt.DropAction.IgnoreAction)
                    event.accept()
                    
                    if main_win and hasattr(main_win, 'suly_frissites'):
                        QTimer.singleShot(50, main_win.suly_frissites)
                    return  # Kilépünk a metódusból, hogy a függvény végi kód ne fusson le duplán!


                # 🚚 KOMPLETT TÚRA MOZGATÁSA (Azonnali leválasztásos technika)
                elif item_type == "TURA":
                    tura_neve = item.text(0)
                    atlag_megallo = item.text(1)
                    ossz_suly = item.text(2)

                    # Határozzuk meg a panelek státuszait
                    aktualis_panel_nev = "KOZOS"
                    if self == main_win.tree_paratlan: aktualis_panel_nev = "PARATLAN"
                    elif self == main_win.tree_paros: aktualis_panel_nev = "PAROS"

                    # 🎯 LÉPÉS 1: FIZIKAI LEVÁLASZTÁS AZONNAL A FORRÁSBÓL
                    # Ezzel elvágjuk a memóriaszálat, a Közös panel elrendezi az indexeit, 
                    # így az alatta lévő elemek garantáltan biztonságban és láthatóak maradnak!
                    old_parent = item.parent()
                    if old_parent:
                        idx = old_parent.indexOfChild(item)
                        if idx != -1: old_parent.takeChild(idx)
                    else:
                        idx = source_tree.indexOfTopLevelItem(item)
                        if idx != -1: 
                            source_tree.takeTopLevelItem(idx)

                    # 🎯 LÉPÉS 2: Felépítjük a túra tiszta másolatát a CÉL panelen
                    klon_cel = QTreeWidgetItem(self)
                    klon_cel.setText(0, tura_neve)
                    klon_cel.setText(1, atlag_megallo)
                    klon_cel.setText(2, ossz_suly)
                    klon_cel.setData(0, Qt.ItemDataRole.UserRole, "TURA")
                    klon_cel.setFlags(item.flags())
                    for col in range(3): klon_cel.setBackground(col, QColor("#dfe6e9"))

                    # Átmásoljuk az összes partnert az új céltúrába
                    for j in range(item.childCount()):
                        eredeti_partner = item.child(j)
                        if not eredeti_partner or eredeti_partner.data(0, Qt.ItemDataRole.UserRole) != "PARTNER": continue

                        p_item = QTreeWidgetItem(klon_cel)
                        p_item.setText(0, eredeti_partner.text(0))
                        p_item.setText(1, eredeti_partner.text(1))
                        p_item.setText(2, eredeti_partner.text(2))
                        p_item.setFont(0, eredeti_partner.font(0))
                        if eredeti_partner.foreground(0): p_item.setForeground(0, eredeti_partner.foreground(0))
                        p_item.setData(0, Qt.ItemDataRole.UserRole, "PARTNER")
                        
                        p_adat_orig = eredeti_partner.data(1, Qt.ItemDataRole.UserRole)
                        if p_adat_orig and isinstance(p_adat_orig, dict):
                            p_adat_uj = p_adat_orig.copy()
                            p_adat_uj['Heti_Panel_Statusz'] = aktualis_panel_nev
                            p_item.setData(1, Qt.ItemDataRole.UserRole, p_adat_uj)
                        p_item.setFlags(eredeti_partner.flags())

                        for k in range(eredeti_partner.childCount()):
                            orig_tetel = eredeti_partner.child(k)
                            t_item = QTreeWidgetItem(p_item)
                            t_item.setText(0, orig_tetel.text(0))
                            t_item.setText(1, orig_tetel.text(1))
                            t_item.setText(2, orig_tetel.text(2))
                            t_item.setData(0, Qt.ItemDataRole.UserRole, "TETEL")
                            t_item.setFlags(orig_tetel.flags())

                    klon_cel.setExpanded(False)

                    # 🎯 LÉPÉS 3: Ha a KÖZÖS-ből indult, felépítjük a másolatot a TÚLOLDALRA is
                    if source_tree == main_win.tree_kozos and self in [main_win.tree_paratlan, main_win.tree_paros]:
                        tulszo_tree = main_win.tree_paros if self == main_win.tree_paratlan else main_win.tree_paratlan
                        tulszo_panel_nev = "PAROS" if self == main_win.tree_paratlan else "PARATLAN"
                        
                        mar_letezik_tulszo = False
                        t_root = tulszo_tree.invisibleRootItem()
                        for i in range(t_root.childCount()):
                            if t_root.child(i).text(0) == tura_neve:
                                mar_letezik_tulszo = True
                                break

                        if not mar_letezik_tulszo:
                            klon_tulszo = QTreeWidgetItem(tulszo_tree)
                            klon_tulszo.setText(0, tura_neve)
                            klon_tulszo.setText(1, atlag_megallo)
                            klon_tulszo.setText(2, ossz_suly)
                            klon_tulszo.setData(0, Qt.ItemDataRole.UserRole, "TURA")
                            klon_tulszo.setFlags(item.flags())
                            for col in range(3): klon_tulszo.setBackground(col, QColor("#dfe6e9"))

                            for j in range(item.childCount()):
                                eredeti_partner = item.child(j)
                                if not eredeti_partner or eredeti_partner.data(0, Qt.ItemDataRole.UserRole) != "PARTNER": continue

                                p_item_t = QTreeWidgetItem(klon_tulszo)
                                p_item_t.setText(0, eredeti_partner.text(0))
                                p_item_t.setText(1, eredeti_partner.text(1))
                                p_item_t.setText(2, eredeti_partner.text(2))
                                p_item_t.setFont(0, eredeti_partner.font(0))
                                if eredeti_partner.foreground(0): p_item_t.setForeground(0, eredeti_partner.foreground(0))
                                p_item_t.setData(0, Qt.ItemDataRole.UserRole, "PARTNER")
                                
                                p_adat_orig = eredeti_partner.data(1, Qt.ItemDataRole.UserRole)
                                if p_adat_orig and isinstance(p_adat_orig, dict):
                                    p_adat_uj = p_adat_orig.copy()
                                    p_adat_uj['Heti_Panel_Statusz'] = tulszo_panel_nev
                                    p_item_t.setData(1, Qt.ItemDataRole.UserRole, p_adat_uj)
                                p_item_t.setFlags(eredeti_partner.flags())

                                for k in range(eredeti_partner.childCount()):
                                    orig_tetel = eredeti_partner.child(k)
                                    t_item_t = QTreeWidgetItem(p_item_t)
                                    t_item_t.setText(0, orig_tetel.text(0))
                                    t_item_t.setText(1, orig_tetel.text(1))
                                    t_item_t.setText(2, orig_tetel.text(2))
                                    t_item_t.setData(0, Qt.ItemDataRole.UserRole, "TETEL")
                                    t_item_t.setFlags(orig_tetel.flags())

                            klon_tulszo.setExpanded(False)

            if source_tree == main_win.tree_kozos and self in [main_win.tree_paratlan, main_win.tree_paros]:
                event.setDropAction(Qt.DropAction.IgnoreAction)
                event.accept()
            else:
                event.acceptProposedAction()

            if main_win and hasattr(main_win, 'suly_frissites'):
                QTimer.singleShot(50, main_win.suly_frissites)
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

        # 🆕 ÚJ TÚRA LÉTREHOZÁSA GOMB BEILLESZTÉSE
        self.btn_uj_tura = QPushButton("🆕 ÚJ TÚRA LÉTREHOZÁSA")
        self.btn_uj_tura.setFixedHeight(45)
        self.btn_uj_tura.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold; border-radius: 5px;")
        self.btn_uj_tura.clicked.connect(self.uj_tura_letrehozasa)
        top_bar_layout.addWidget(self.btn_uj_tura, 1)

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
            tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
            tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
            tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
            
            # Itt adjuk meg a kiinduló szélességeket pixelben:
            tree.setColumnWidth(0, 240) # Első oszlop szélessége
            tree.setColumnWidth(1, 100) # Második oszlop szélessége
            tree.setColumnWidth(2, 70)  # Harmadik oszlop szélessége
            
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
        """
        Újraépíti a túrák összsúlyát a fák aktuális állapota alapján.
        Ha az Excel betöltés folyamatban van, azonnal kilép a lefagyás megelőzésére.
        """
        # ✨ HA AZ EXCEL BETÖLTÉS FUT, AZONNAL LÉPJEN KI (Ez akadályozza meg a fagyást!)
        if getattr(self, 'is_updating', False):
            return

        self.is_updating = True
        
        for tree in [self.tree_paratlan, self.tree_kozos, self.tree_paros]:
            root = tree.invisibleRootItem()
            if not root:
                continue
            
            for i in range(root.childCount()):
                tura_item = root.child(i)
                if not tura_item or tura_item.data(0, Qt.ItemDataRole.UserRole) != "TURA":
                    continue
                if "🗑 töröltek" in tura_item.text(0).lower():
                    continue

                tura_osszsuly = 0.0
                partner_szamlalo = 0
                
                # Végigmegyünk a túra pillanatnyi valós gyerekein
                for j in range(tura_item.childCount()):
                    partner_item = tura_item.child(j)
                    if not partner_item or partner_item.data(0, Qt.ItemDataRole.UserRole) != "PARTNER":
                        continue
                    
                    partner_szamlalo += 1
                    
                    # Közvetlenül a partner mellett megjelenített súlyt olvassuk le
                    suly_szoveg = partner_item.text(2).replace("kg", "").replace(",", ".").strip()
                    try:
                        partner_sulya = float(suly_szoveg) if suly_szoveg else 0.0
                    except ValueError:
                        partner_sulya = 0.0
                    
                    tura_osszsuly += partner_sulya

                uj_megallo_szoveg = f"{partner_szamlalo} megálló"
                uj_suly_szoveg = f"{int(round(tura_osszsuly))} kg"
                
                # Csak akkor írjuk át, ha ténylegesen változott az érték
                if tura_item.text(1) != uj_megallo_szoveg:
                    tura_item.setText(1, uj_megallo_szoveg)
                if tura_item.text(2) != uj_suly_szoveg:
                    tura_item.setText(2, uj_suly_szoveg)
                
                font = QFont()
                font.setBold(True)
                tura_item.setFont(0, font)
                tura_item.setFont(2, font)

        self.is_updating = False

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
        import os, pandas as pd, json, io, shutil, uuid
        from PyQt6.QtWidgets import QFileDialog, QMessageBox, QTreeWidgetItem
        from PyQt6.QtGui import QColor, QFont
        from PyQt6.QtCore import Qt, QTimer

        path, _ = QFileDialog.getOpenFileName(self, "Heti adatok betöltése", "", "Excel Files (*.xlsx)")
        if not path: 
            return

        biztonsagos_path = os.path.abspath(path)

        self.is_updating = True
        self.tree_paratlan.blockSignals(True)
        self.tree_kozos.blockSignals(True)
        self.tree_paros.blockSignals(True)

        try:
            with open(biztonsagos_path, "rb") as f:
                file_bytes = f.read()
                df = pd.read_excel(io.BytesIO(file_bytes), engine='openpyxl')

            self.tree_paratlan.clear()
            self.tree_kozos.clear()
            self.tree_paros.clear()
            
            # Előkészítjük a négy elkülönített memóriafészket
            turak_szotar = {
                "PARATLAN": {},
                "PAROS": {},
                "KOZOS": {},
                "TOROLT": {}
            }

            # Megnézzük, hogy létezik-e egyáltalán az 'E' oszlop a fájlban (Heti_Panel_Statusz néven vagy az 5. oszlopként)
            e_oszlop_kulcs = None
            if 'Heti_Panel_Statusz' in df.columns:
                e_oszlop_kulcs = 'Heti_Panel_Statusz'
            elif df.shape[1] > 4:
                # Ha név alapján nincs meg, de van legalább 5 oszlop, akkor a 4-es indexű (E) oszlopot nézzük
                e_oszlop_kulcs = df.columns[4]

            for _, row in df.iterrows():
                p = row.to_dict()
                t_nev = str(p.get('Túra neve') or p.get('Túra') or p.get('J', 'ISMERETLEN TÚRA')).strip()
                if t_nev.lower() in ['nan', '', 'none']: 
                    t_nev = 'ISMERETLEN TÚRA'
                
                p_nev = str(p.get('Partner', ''))
                p_cim = str(p.get('Cim') or p.get('Cím', ''))
                p_id = f"{p_nev}_{p_cim}".strip()
                if not p_id or p_id == "_": 
                    continue

                uj_tetelek = []
                json_adat = p.get('Tetel_JSON_FIX')
                if isinstance(json_adat, str) and json_adat.strip():
                    try: uj_tetelek = json.loads(json_adat)
                    except: pass
                p['Tetel'] = uj_tetelek

                if 'IRSZ' in p: 
                    p['IRSZ'] = str(p['IRSZ']).replace('.0', '').strip()

                # 🎯 A KÍVÁNT LOGIKA: Szigorúan az E oszlop tartalmát elemezzük magyar vagy angol kulcsszavakkal
                m_statusz_nyers = "KOZOS" # Alapértelmezett, ha a fájl még szűz
                
                if e_oszlop_kulcs:
                    cella_ertek = str(p.get(e_oszlop_kulcs, '')).upper().strip()
                    
                    if "PÁRATLAN" in cella_ertek or "PARATLAN" in cella_ertek: 
                        m_statusz_nyers = "PARATLAN"
                    elif "PÁROS" in cella_ertek or "PAROS" in cella_ertek: 
                        m_statusz_nyers = "PAROS"
                    elif "TÖRÖLT" in cella_ertek or "TOROLT" in cella_ertek: 
                        m_statusz_nyers = "TOROLT"
                    elif "KÖZÖS" in cella_ertek or "KOZOS" in cella_ertek: 
                        m_statusz_nyers = "KOZOS"
                    else:
                        # Ha van E oszlop, de az adott cella üres/érvénytelen, akkor is Közösbe kényszerítjük
                        m_statusz_nyers = "KOZOS"

                # Mentés a szigorúan meghatározott csoportba a memóriában
                if t_nev not in turak_szotar[m_statusz_nyers]:
                    turak_szotar[m_statusz_nyers][t_nev] = {}
                
                if p_id in turak_szotar[m_statusz_nyers][t_nev]:
                    if uj_tetelek: 
                        turak_szotar[m_statusz_nyers][t_nev][p_id]['Tetel'].extend(uj_tetelek)
                else: 
                    turak_szotar[m_statusz_nyers][t_nev][p_id] = p

            # 🎯 RAJZOLÁS PANELENKÉNT SZELETELVE
            for panel_kulcs, tura_csoportok in turak_szotar.items():
                
                # Kiválasztjuk a fizikai panel célpontját
                if panel_kulcs == "PARATLAN": 
                    target_tree = self.tree_paratlan
                elif panel_kulcs == "PAROS": 
                    target_tree = self.tree_paros
                else: 
                    # A Közös és a Törölt adatok is a középső panelre futnak rá
                    target_tree = self.tree_kozos

                for t_nev, partnerek_dict in tura_csoportok.items():
                    partnerek_listaja = list(partnerek_dict.values())
                    if not partnerek_listaja: 
                        continue

                    # Súly és darabszám kalkuláció a szétválasztott szeletre
                    ossz_suly = sum(float(p.get('Súly') or p.get('Alap_B') or p.get('A', 0)) for p in partnerek_listaja)
                    atlag_megallo = 0
                    for p in partnerek_listaja:
                        m_ertek = p.get('Átlag megálló') or p.get('Atlag_Megallo') or p.get('B')
                        if m_ertek and str(m_ertek).lower() != 'nan':
                            atlag_megallo = m_ertek
                            break

                    # Csomópont elhelyezése
                    if panel_kulcs == "TOROLT" or "töröltek" in t_nev.lower():
                        if hasattr(self, '_toroltek_csomopont_lekerese'):
                            root_item = self._toroltek_csomopont_lekerese()
                        else:
                            root_item = QTreeWidgetItem(target_tree)
                            root_item.setText(0, "🗑 töröltek")
                            root_item.setData(0, Qt.ItemDataRole.UserRole, "TURA")
                    else:
                        root_item = QTreeWidgetItem(target_tree)
                        root_item.setText(0, f"🚚 {t_nev}")
                        root_item.setText(1, f"Átlag: {atlag_megallo} cím")
                        root_item.setText(2, f"{int(ossz_suly)} kg")
                        root_item.setData(0, Qt.ItemDataRole.UserRole, "TURA")
                        root_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDropEnabled | Qt.ItemFlag.ItemIsDragEnabled)
                        for col in range(3): 
                            root_item.setBackground(col, QColor("#dfe6e9"))

                    # Partnerek hozzáadása
                    for p in partnerek_listaja:
                        p_item = QTreeWidgetItem(root_item)
                        p_nev = str(p.get('Partner', 'Ismeretlen'))
                        p_statusz = str(p.get('Partner statusza') or p.get('Statusz') or p.get('H', '')).upper().strip()
                        p_cim = str(p.get('Cim') or p.get('Cím', 'Nincs cím'))
                        
                        if 'ÚJ' in p_statusz:
                            p_item.setText(0, f"✨ [ÚJ] {p_nev} ({p_cim})")
                            p_item.setForeground(0, QColor("#3498db"))
                        else: 
                            p_item.setText(0, f"👤 {p_nev}")

                        p_item.setText(1, str(p.get('Intenzitás') or p.get('Intenz', '')))
                        p_item.setText(2, f"{int(p.get('Súly') or p.get('Alap_B') or p.get('A', 0))} kg")
                        
                        p_font = QFont()
                        p_font.setBold(True)
                        p_item.setFont(0, p_font)
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

                    if panel_kulcs != "TOROLT" and "töröltek" not in t_nev.lower():
                        root_item.setExpanded(False)

            # Mentési útvonalak fixálása a friss fájlra
            for var_name in ['aktualis_fajl_utvonal', 'current_file', 'fajl_utvonal', 'path']:
                if hasattr(self, var_name):
                    setattr(self, var_name, biztonsagos_path)

            QMessageBox.information(self, "Siker", "Az adatok szigorúan az Excel struktúra alapján betöltve!")

        except Exception as e:
            QMessageBox.critical(self, "Hiba", f"Beolvasási hiba: {e}")
            
        finally:
            self.tree_paratlan.blockSignals(False)
            self.tree_kozos.blockSignals(False)
            self.tree_paros.blockSignals(False)
            self.is_updating = False
            
            QTimer.singleShot(150, self.suly_frissites)

    def uj_tura_letrehozasa(self):
        """
        Egy új, üres túrafejléc létrehozása a felhasználó által megadott névvel és panelválasztással.
        """
        from PyQt6.QtWidgets import QInputDialog, QMessageBox, QTreeWidgetItem
        from PyQt6.QtGui import QColor, QFont
        from PyQt6.QtCore import Qt
        
        # 1. Bekérjük az új túra nevét
        tura_nev, ok = QInputDialog.getText(self, "Új túra", "Add meg az új túra nevét (pl. Budapest_3):")
        if not ok or not tura_nev.strip():
            return
            
        t_nev_tisztitott = tura_nev.strip()

        # 2. Megkérdezzük, hogy melyik panelre kerüljön
        panelek = ["Páratlan hét", "Közös panel", "Páros hét"]
        panel_valasztas, ok2 = QInputDialog.getItem(self, "Panel kiválasztása", 
                                                    f"Melyik panelen jöjjön létre a '{t_nev_tisztitott}' túra?", 
                                                    panelek, 1, False) # Alapértelmezetten a Közös (1-es index) van kijelölve
        if not ok2:
            return

        # Kiválasztjuk a fizikai célpanelt
        if panel_valasztas == "Páratlan hét":
            target_tree = self.tree_paratlan
        elif panel_valasztas == "Páros hét":
            target_tree = self.tree_paros
        else:
            target_tree = self.tree_kozos

        # 3. Duplikáció ellenőrzése az adott panelen
        root = target_tree.invisibleRootItem()
        for i in range(root.childCount()):
            if root.child(i).text(0).replace("🚚", "").strip() == t_nev_tisztitott:
                QMessageBox.warning(self, "Figyelem", f"Ezen a panelen már létezik '{t_nev_tisztitott}' nevű túra!")
                return

        # 4. A felületi elem felépítése és formázása az eredeti stílusod alapján
        uj_tura_item = QTreeWidgetItem(target_tree)
        uj_tura_item.setText(0, f"🚚 {t_nev_tisztitott}")
        uj_tura_item.setText(1, "0 megálló")
        uj_tura_item.setText(2, "0 kg")
        
        # Metaadatok és flag-ek beállítása a Drag & Drop-hoz
        uj_tura_item.setData(0, Qt.ItemDataRole.UserRole, "TURA")
        uj_tura_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | 
                              Qt.ItemFlag.ItemIsDropEnabled | Qt.ItemFlag.ItemIsDragEnabled)

        # Háttérszín szürkére állítása (#dfe6e9) a meglévő stílusod alapján
        for col in range(3): 
            uj_tura_item.setBackground(col, QColor("#dfe6e9"))
            
        font = QFont()
        font.setBold(True)
        uj_tura_item.setFont(0, font)
        uj_tura_item.setFont(2, font)

        # Kibontjuk, hogy ha behúzol egy partnert, azonnal látszódjon benne
        uj_tura_item.setExpanded(True)
        
        # Frissítjük a súlyokat
        self.suly_frissites()
        
        QMessageBox.information(self, "Siker", f"A(z) '{t_nev_tisztitott}' túra létrehozva a {panel_valasztas} listában!")

