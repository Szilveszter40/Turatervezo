import pandas as pd
import re
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, 
                             QTreeWidgetItem, QLabel, QPushButton, QMessageBox, 
                             QListWidget, QListWidgetItem, QAbstractItemView, QFrame)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont

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
        # Ha partnerre dobnák, a szülő túrára (🚚) irányítjuk a Drop-ot
        if target_item:
            data = target_item.data(0, Qt.ItemDataRole.UserRole)
            if data in ["PARTNER", "TETEL"]:
                parent_item = target_item.parent()
                if parent_item:
                    self.setCurrentItem(parent_item)
        
        super().dropEvent(event)
        # Súlyfrissítés késleltetve a stabilitásért
        if hasattr(self.window(), 'suly_frissites'):
            QTimer.singleShot(100, self.window().suly_frissites)

class KeziszerkesztoAblak(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_parent = parent
        self.setWindowTitle("Kézi Túra Szerkesztő - Végleges Verzió")
        
        # Teljes képernyő kényszerítése
        self.setMinimumSize(1200, 800)
        self.showMaximized()
        
        if not hasattr(self.main_parent, 'minden_partner_adat'):
            QMessageBox.critical(self, "Hiba", "Nincsenek adatok a szerkesztéshez!")
            QTimer.singleShot(0, self.reject)
            return

        self.osszes_tura_neve = sorted(list(set(str(p['Túra']) for p in self.main_parent.minden_partner_adat)))
        self.initUI()

    def showEvent(self, event):
        super().showEvent(event)
        self.setWindowState(Qt.WindowState.WindowMaximized)

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # --- FELSŐ VÁLASZTÓ SÁV ---
        top_layout = QHBoxLayout()
        top_layout.setSpacing(15)
        
        # Stílus a választó konténerekhez és a jelölőnégyzetekhez
        container_style = """
            QFrame {
                background-color: #f1f2f6;
                border: 1px solid #ced4da;
                border-radius: 8px;
            }
            QLabel { border: none; color: #2f3640; font-weight: bold; }
            QListWidget {
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
            }
            QListWidget::indicator {
                width: 18px; height: 18px;
                border: 1px solid #3498db;
                border-radius: 3px;
                background-color: white;
            }
            QListWidget::indicator:checked {
                background-color: #3498db;
                border: 1px solid #2980b9;
            }
        """
        
        for title, attr in [("Bal oldali túrák:", "list_bal"), ("Jobb oldali túrák:", "list_jobb")]:
            container = QFrame()
            container.setStyleSheet(container_style)
            l = QVBoxLayout(container)
            l.setContentsMargins(10, 8, 10, 10)
            l.setSpacing(5)
            l.addWidget(QLabel(title))
            lw = QListWidget()
            lw.setMaximumHeight(100)
            for tura in self.osszes_tura_neve:
                item = QListWidgetItem(str(tura))
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                lw.addItem(item)
            setattr(self, attr, lw)
            l.addWidget(lw)
            top_layout.addWidget(container)
            
        main_layout.addLayout(top_layout)

        # Frissítő gomb
        self.btn_load = QPushButton("🔄 KIJELÖLT TÚRÁK MEGJELENÍTÉSE")
        self.btn_load.setStyleSheet("""
            QPushButton {
                height: 35px; background-color: #3498db; color: white; 
                font-weight: bold; border-radius: 5px; font-size: 13px;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.btn_load.clicked.connect(self.adatok_betoltese)
        main_layout.addWidget(self.btn_load)

        # --- TÁBLÁZATOK ---
        h_layout = QHBoxLayout()
        self.tree_bal = self.setup_tree()
        self.tree_jobb = self.setup_tree()
        h_layout.addWidget(self.tree_bal)
        h_layout.addWidget(self.tree_jobb)
        main_layout.addLayout(h_layout, 1)

        # --- ALSÓ GOMBOK ---
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("💾 MÓDOSÍTÁSOK VÉGLEGESÍTÉSE")
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; color: white; font-weight: bold; 
                height: 45px; border-radius: 5px; font-size: 14px;
            }
            QPushButton:hover { background-color: #219150; }
        """)
        btn_save.clicked.connect(self.mentes_es_vissza)
        
        btn_cancel = QPushButton("MÉGSE")
        btn_cancel.setStyleSheet("height: 45px; font-weight: bold; border-radius: 5px;")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        main_layout.addLayout(btn_layout)

    def setup_tree(self):
        tree = DraggableTree(self)
        tree.setColumnCount(3)
        tree.setHeaderLabels(["Partner / Tétel", "Intenzitás / Db", "Súly"])
        tree.setColumnWidth(0, 450)
        tree.setStyleSheet("QTreeWidget { border: 1px solid #dcdde1; border-radius: 5px; background-color: white; }")
        return tree

    def adatok_betoltese(self):
        self.frissit_fat(self.tree_bal, self.list_bal)
        self.frissit_fat(self.tree_jobb, self.list_jobb)

    def frissit_fat(self, tree, list_widget):
        try:
            tree.clear()
            kijelolt = [list_widget.item(i).text() for i in range(list_widget.count()) 
                        if list_widget.item(i).checkState() == Qt.CheckState.Checked]
        except RuntimeError: return

        for tura_nev in kijelolt:
            root = QTreeWidgetItem(tree)
            root.setText(0, f"🚚 {tura_nev}")
            root.setData(0, Qt.ItemDataRole.UserRole, "TURA")
            
            # Túra sor kiemelése
            for col in range(3):
                root.setBackground(col, QColor("#dfe6e9"))
            f = root.font(0)
            f.setBold(True)
            root.setFont(0, f)
            
            root.setFlags(root.flags() & ~Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled)
            root.setExpanded(True)
            
            s = 0
            for p in self.main_parent.minden_partner_adat:
                if str(p.get('Túra')) == tura_nev:
                    p_item = QTreeWidgetItem(root)
                    p_item.setText(0, f"{'✨ [ÚJ] ' if p.get('Statusz')=='ÚJ' else '👤 '}{p['Partner']}")
                    p_item.setText(1, str(p.get('Intenz', '')))
                    p_item.setText(2, f"{int(p['Alap_B'])} kg")
                    p_item.setData(1, Qt.ItemDataRole.UserRole, p)
                    p_item.setData(0, Qt.ItemDataRole.UserRole, "PARTNER")
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
                            # Tétel dőlt betű
                            it_f = t_item.font(0)
                            it_f.setItalic(True)
                            t_item.setFont(0, it_f)
                    s += p['Alap_B']
            root.setText(2, f"Össz: {int(s)} kg")
            root.setBackground(2, QColor("#ffcccc") if s > 2100 else QColor("#dfe6e9"))

    def suly_frissites(self):
        for tree in [self.tree_bal, self.tree_jobb]:
            for i in range(tree.topLevelItemCount()):
                root = tree.topLevelItem(i)
                s = 0
                for j in range(root.childCount()):
                    p_item = root.child(j)
                    d = p_item.data(1, Qt.ItemDataRole.UserRole)
                    if d: s += d['Alap_B']
                root.setText(2, f"Össz: {int(s)} kg")
                root.setBackground(2, QColor("#ffcccc") if s > 2100 else QColor("#dfe6e9"))

    def mentes_es_vissza(self):
        for tree in [self.tree_bal, self.tree_jobb]:
            for i in range(tree.topLevelItemCount()):
                root = tree.topLevelItem(i)
                t_nev = root.text(0).replace("🚚 ", "").strip()
                for j in range(root.childCount()):
                    p_item = root.child(j)
                    d = p_item.data(1, Qt.ItemDataRole.UserRole)
                    if d: d['Túra'] = t_nev
        QMessageBox.information(self, "Kész", "Módosítások mentve a memóriába!")
        self.accept()
