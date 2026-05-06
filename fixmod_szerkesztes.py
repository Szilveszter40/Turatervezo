import json
import pandas as pd
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, 
                             QTreeWidgetItem, QLabel, QPushButton, QMessageBox, 
                             QListWidget, QListWidgetItem, QAbstractItemView, QFrame, 
                             QSizePolicy, QHeaderView)
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
        self.setIndentation(20) 
        self.setAnimated(True)

    def dropEvent(self, event):
        source_tree = event.source()
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
        
        if target_type == "TURA":
            dest_root = target_item
            index = dest_root.childCount()
        elif target_type == "PARTNER":
            dest_root = target_item.parent()
            index = dest_root.indexOfChild(target_item)
        else:
            partner_item = target_item.parent()
            dest_root = partner_item.parent()
            index = dest_root.indexOfChild(partner_item)

        if dest_root:
            self.window().partner_sor_letrehozas(dest_root, p_adat)
            new_row = dest_root.takeChild(dest_root.childCount()-1)
            dest_root.insertChild(index, new_row)
            if source_item.parent():
                source_item.parent().removeChild(source_item)
            event.accept()
            QTimer.singleShot(50, self.window().suly_frissites)
        else:
            event.ignore()

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
        
        top_row = QHBoxLayout()
        for title, attr in [("Bal oldali túrák:", "list_bal"), ("Jobb oldali túrák:", "list_jobb")]:
            f = QFrame()
            f.setStyleSheet("QFrame { border: 1px solid #ccc; background: #f9f9f9; border-radius: 5px; }")
            v = QVBoxLayout(f)
            v.addWidget(QLabel(f"<b>{title}</b>"))
            lw = QListWidget()
            lw.setMaximumHeight(100)
            for t in self.osszes_tura_neve:
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

        h_trees = QHBoxLayout()
        self.tree_bal = DraggableTree(self)
        self.tree_jobb = DraggableTree(self)
        for t in [self.tree_bal, self.tree_jobb]:
            t.setColumnCount(3)
            t.setHeaderLabels(["Partner / Tétel", "Intenzitás / Db", "Súly"])
            t.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            h_trees.addWidget(t)
        main_layout.addLayout(h_trees, 1)

        btn_save = QPushButton("💾 VÁLTOZÁSOK VÉGLEGESÍTÉSE")
        btn_save.setFixedHeight(50)
        btn_save.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        btn_save.clicked.connect(self.mentes_es_vissza)
        main_layout.addWidget(btn_save)

    def partner_sor_letrehozas(self, parent_item, p):
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
        
        p_font = QFont(); p_font.setBold(True); p_item.setFont(0, p_font)
        p_item.setData(0, Qt.ItemDataRole.UserRole, "PARTNER")
        p_item.setData(1, Qt.ItemDataRole.UserRole, p)
        p_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled)
        p_item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)

        # Tételek listázása a JSON-ból (nev, db, suly kulcsokkal)
        tetelek = []
        json_adat = p.get('Tetel_JSON_FIX', '')
        if isinstance(json_adat, str) and json_adat.strip():
            try:
                tetelek = json.loads(json_adat)
            except:
                pass

        if not tetelek:
            t_item = QTreeWidgetItem(p_item)
            t_item.setText(0, f"   📍 {p_cim}")
            t_item.setForeground(0, QColor("#95a5a6"))
            t_item.setData(0, Qt.ItemDataRole.UserRole, "TETEL")
        else:
            for t_adat in tetelek:
                t_item = QTreeWidgetItem(p_item)
                # Pontos kulcsok a beküldött kép alapján: nev, db, suly
                t_nev = t_adat.get('nev', 'Ismeretlen termék')
                t_db = t_adat.get('db', 0)
                t_suly = t_adat.get('suly', 0)
                
                t_item.setText(0, f"   📦 {t_nev}")
                t_item.setText(1, f"{t_db} db")
                t_item.setText(2, f"{t_suly} kg")
                t_item.setForeground(0, QColor("#2c3e50"))
                t_item.setData(0, Qt.ItemDataRole.UserRole, "TETEL")
        return p_item

    def adatok_betoltese(self):
        for tree, lw in [(self.tree_bal, self.list_bal), (self.tree_jobb, self.list_jobb)]:
            tree.clear()
            kijelolt = [lw.item(i).text() for i in range(lw.count()) if lw.item(i).checkState() == Qt.CheckState.Checked]
            for t_nev in kijelolt:
                root = QTreeWidgetItem(tree)
                root.setText(0, f"🚚 {t_nev}"); root.setData(0, Qt.ItemDataRole.UserRole, "TURA")
                root.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
                for c in range(3): root.setBackground(c, QColor("#dfe6e9"))
                root.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsDropEnabled)
                
                for p in self.main_parent.minden_partner_adat:
                    p_t = str(p.get('Túra', 'ISMERETLEN'))
                    if p_t.lower() in ['nan', '']: p_t = 'ISMERETLEN'
                    if p_t == t_nev:
                        self.partner_sor_letrehozas(root, p)
                root.setExpanded(True)
        self.suly_frissites()

    def suly_frissites(self):
        for tree in [self.tree_bal, self.tree_jobb]:
            for i in range(tree.topLevelItemCount()):
                root = tree.topLevelItem(i)
                total = sum(root.child(j).data(1, Qt.ItemDataRole.UserRole).get('Alap_B', 0) 
                            for j in range(root.childCount()) if root.child(j).data(0, Qt.ItemDataRole.UserRole) == "PARTNER")
                root.setText(2, f"Össz: {int(total)} kg")

    def mentes_es_vissza(self):
        for tree in [self.tree_bal, self.tree_jobb]:
            for i in range(tree.topLevelItemCount()):
                root = tree.topLevelItem(i)
                t_nev = root.text(0).replace("🚚 ", "").strip()
                for j in range(root.childCount()):
                    p_item = root.child(j)
                    p_adat = p_item.data(1, Qt.ItemDataRole.UserRole)
                    if p_adat: p_adat['Túra'] = t_nev
        QMessageBox.information(self, "Kész", "Változások mentve!")
        self.accept()

def indit_szerkeszto(parent):
    dialog = KeziszerkesztoAblak(parent)
    return dialog.exec()
