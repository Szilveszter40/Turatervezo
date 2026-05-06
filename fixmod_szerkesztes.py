import pandas as pd
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, 
                             QTreeWidgetItem, QLabel, QPushButton, QMessageBox, 
                             QListWidget, QListWidgetItem, QAbstractItemView, QFrame)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

class DraggableTree(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDropIndicatorShown(True)

    def dropEvent(self, event):
        target_item = self.itemAt(event.position().toPoint())
        # Ha partnerre dobnák, a szülő túrára irányítjuk a Drop-ot
        if target_item:
            data = target_item.data(0, Qt.ItemDataRole.UserRole)
            if data in ["PARTNER", "TETEL"]:
                self.setCurrentItem(target_item.parent())
        
        super().dropEvent(event)
        # Késleltetett frissítés a stabilitásért
        QTimer.singleShot(100, self.window().suly_frissites)

class KeziszerkesztoAblak(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_parent = parent
        self.setWindowTitle("Kézi Túra Szerkesztő - Stabilizált verzió")
        
        self.setMinimumSize(1200, 800)
        self.showMaximized()
        
        if not hasattr(self.main_parent, 'minden_partner_adat'):
            QMessageBox.critical(self, "Hiba", "Nincsenek adatok!")
            self.reject()
            return

        self.osszes_tura = sorted(list(set(str(p['Túra']) for p in self.main_parent.minden_partner_adat)))
        
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        
        # --- FELSŐ VEZÉRLŐK ---
        top_layout = QHBoxLayout()
        
        self.list_bal = self.create_selector_list("Bal oldali túrák:")
        self.list_jobb = self.create_selector_list("Jobb oldali túrák:")
        
        top_layout.addWidget(self.list_bal.parent())
        top_layout.addWidget(self.list_jobb.parent())
        main_layout.addLayout(top_layout)

        # Frissítés gomb (biztonságosabb, mint az automata frissítés)
        self.btn_refresh = QPushButton("🔄 KIJELÖLT TÚRÁK MEGJELENÍTÉSE")
        self.btn_refresh.setStyleSheet("height: 35px; background-color: #3498db; color: white; font-weight: bold;")
        self.btn_refresh.clicked.connect(self.teljes_frissites)
        main_layout.addWidget(self.btn_refresh)

        # --- TÁBLÁZATOK ---
        h_layout = QHBoxLayout()
        self.tree_bal = DraggableTree(self)
        self.tree_jobb = DraggableTree(self)
        
        for t in [self.tree_bal, self.tree_jobb]:
            t.setColumnCount(3)
            t.setHeaderLabels(["Partner / Tétel", "Intenzitás", "Súly"])
            t.setColumnWidth(0, 400)
            h_layout.addWidget(t)
            
        main_layout.addLayout(h_layout)

        # --- ALSÓ GOMBOK ---
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("💾 MÓDOSÍTÁSOK VÉGLEGESÍTÉSE")
        btn_save.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; height: 50px;")
        btn_save.clicked.connect(self.mentes_es_vissza)
        
        btn_cancel = QPushButton("MÉGSE")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        main_layout.addLayout(btn_layout)

    def create_selector_list(self, title):
        container = QFrame()
        l = QVBoxLayout(container)
        l.addWidget(QLabel(f"<b>{title}</b>"))
        lw = QListWidget()
        lw.setMaximumHeight(120)
        for tura in self.osszes_tura:
            item = QListWidgetItem(str(tura))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            lw.addItem(item)
        l.addWidget(lw)
        return lw

    def teljes_frissites(self):
        """Manuálisan hívható frissítés, ami elkerüli az objektum-törlési hibát."""
        self.frissit_oldal(self.tree_bal, self.list_bal)
        self.frissit_oldal(self.tree_jobb, self.list_jobb)

    def frissit_oldal(self, tree, list_widget):
        tree.clear()
        # Biztonságos elem-lekérés: csak akkor megyünk tovább, ha a list_widget létezik
        try:
            kijelolt_turak = []
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                if item and item.checkState() == Qt.CheckState.Checked:
                    kijelolt_turak.append(item.text())
        except RuntimeError: return

        for tura_nev in kijelolt_turak:
            root = QTreeWidgetItem(tree)
            root.setText(0, f"🚚 {tura_nev}")
            root.setData(0, Qt.ItemDataRole.UserRole, "TURA")
            root.setFlags(root.flags() & ~Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled)
            root.setExpanded(True)
            
            osszsuly = 0
            for p in self.main_parent.minden_partner_adat:
                if str(p['Túra']) == tura_nev:
                    p_item = QTreeWidgetItem(root)
                    p_item.setText(0, f"{'✨ [ÚJ] ' if p.get('Statusz')=='ÚJ' else '👤 '}{p['Partner']}")
                    p_item.setText(1, str(p.get('Intenz', '')))
                    p_item.setText(2, f"{int(p['Alap_B'])} kg")
                    p_item.setData(0, Qt.ItemDataRole.UserRole, "PARTNER")
                    p_item.setData(1, Qt.ItemDataRole.UserRole, p)
                    p_item.setFlags(p_item.flags() | Qt.ItemFlag.ItemIsDragEnabled)
                    p_item.setFlags(p_item.flags() & ~Qt.ItemFlag.ItemIsDropEnabled)
                    
                    if p.get('Statusz') == 'ÚJ': p_item.setForeground(0, QColor("#3498db"))
                    
                    if 'Tetel' in p:
                        for t in p['Tetel']:
                            t_item = QTreeWidgetItem(p_item)
                            t_item.setText(0, f"  📦 {t['nev']}")
                            t_item.setText(1, f"{t['db']} db")
                            t_item.setText(2, f"{int(t['suly'])} kg")
                            t_item.setData(0, Qt.ItemDataRole.UserRole, "TETEL")
                            t_item.setFlags(t_item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled & ~Qt.ItemFlag.ItemIsDropEnabled)
                    osszsuly += p['Alap_B']
            root.setText(2, f"Össz: {int(osszsuly)} kg")

    def suly_frissites(self):
        for tree in [self.tree_bal, self.tree_jobb]:
            for i in range(tree.topLevelItemCount()):
                root = tree.topLevelItem(i)
                suly = 0
                for j in range(root.childCount()):
                    p_item = root.child(j)
                    p_adat = p_item.data(1, Qt.ItemDataRole.UserRole)
                    if p_adat: suly += p_adat['Alap_B']
                root.setText(2, f"Össz: {int(suly)} kg")

    def mentes_es_vissza(self):
        for tree in [self.tree_bal, self.tree_jobb]:
            for i in range(tree.topLevelItemCount()):
                root = tree.topLevelItem(i)
                tura_nev = root.text(0).replace("🚚 ", "").strip()
                for j in range(root.childCount()):
                    p_item = root.child(j)
                    p_adat = p_item.data(1, Qt.ItemDataRole.UserRole)
                    if p_adat: p_adat['Túra'] = tura_nev
        QMessageBox.information(self, "Kész", "Változások rögzítve!")
        self.accept()
