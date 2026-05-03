import pandas as pd
import re
import sys
import os
if getattr(sys, 'frozen', False):
    # ELŐSZÖR: Adjuk hozzá a belső mappát a modulok miatt
    if sys._MEIPASS not in sys.path:
        sys.path.append(sys._MEIPASS)
    
    # MÁSODSZOR: Ugorjunk az EXE mellé a mentések miatt
    os.chdir(os.path.dirname(sys.executable))
else:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

# CSAK EZUTÁN jöhetnek a modulok és a PyQt6 importok!
import importlib.util
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QFileDialog, QMessageBox, 
                             QTreeWidget, QTreeWidgetItem, QAbstractItemView, QSplitter, 
                             QHeaderView, QInputDialog, QLineEdit, QMenu, QDialog, 
                             QListWidget, QLabel, QComboBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QTextDocument, QPageLayout, QAction
from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewDialog

# --- 1. ADATFELDOLGOZÓ MOTOR ---
class AdatMotor:
    SZORZOK = {
        "K-K10DB": 10, "K-K20DB": 20, "K-P10DB": 10, "K-P5DB": 5,
        "K-SPECDB": 10, "K-PALMADB": 20, "IBC": 1000, "HSO": 60, "ZSÍR": 60, "ÉH": 60
    }
    
    @staticmethod
    def tiszta_sor(text):
        if text is None or str(text) == "nan": return ""
        return " ".join(str(text).replace('\r', ' ').replace('\n', ' ').split())

    @staticmethod
    def kinyer_cim_es_megj(text):
        try:
            t = AdatMotor.tiszta_sor(text)
            if not t: return "", ""
            hu_match = re.search(r'HU\s+(\d{4})', t); hu_kod = hu_match.group(1) if hu_match else ""
            munka = t.split("//")[0].strip()
            ir_m = re.search(r'\d{4}', munka); ir_v = ir_m.end() if ir_m else 0
            v_p = -1; szamok = list(re.finditer(r'\d{1,4}', munka))
            for m in szamok:
                if m.start() >= ir_v and len(m.group()) <= 3:
                    v_p = m.end()
                    while v_p < len(munka) and munka[v_p] in "/ABCa-z. ": v_p += 1
                    break
            cim, megj = (munka[:v_p].strip(), munka[v_p:].strip()) if v_p != -1 else (munka, "")
            if "//" in t: megj = f"{megj} | {t.split('//')[-1].strip()}".strip(" | ")
            return f"{hu_kod} - {cim}" if hu_kod else cim, megj
        except: return str(text), ""

    @staticmethod
    def nyers_adat_tisztitas(df):
        import json
        import pandas as pd
        
        df = df.dropna(how='all').copy()
        col_cnt = len(df.columns)

        def tetel_tiszt(t):
            t = str(t).upper()
            if "HASZNÁLT SÜTŐOLAJ" in t or "HSO" in t: return "HSO"
            if "ÉTKEZÉSI" in t or "ÉH" in t: return "ÉH"
            if "VIZES ZSÍR" in t or "ZSÍR" in t: return "ZSÍR"
            return t

        feldolgozott = []
        for _, row in df.iterrows():
            # ÚJ: Túranév kinyerése (Excel A oszlop = 0. index)
            t_nev = AdatMotor.tiszta_sor(row.iloc[0]) if col_cnt > 0 else "ISMERETLEN"
            
            cim, megj = AdatMotor.kinyer_cim_es_megj(str(row.iloc[3]) if col_cnt > 3 else "")
            p_nev = AdatMotor.tiszta_sor(row.iloc[2] if col_cnt > 2 else "Ismeretlen")
            tetel = tetel_tiszt(row.iloc[5] if col_cnt > 5 else "ISMERETLEN")
            
            db, r_tal = 0.0, False
            for i in range(7, 11):
                if col_cnt > i:
                    val = str(row.iloc[i])
                    if ":" in val:
                        try: 
                            db += float(val.split(":")[-1])
                            r_tal = True
                        except: pass
            
            if not r_tal:
                if col_cnt > 6:
                    try: 
                        v = row.iloc[6]
                        db = float(v) if pd.notnull(v) and str(v).strip() != "" else 1.0
                    except: db = 1.0
                else: db = 1.0
            
            kg = db * AdatMotor.SZORZOK.get(tetel, 0)
            
            # ÚJ: A 'Tura' mezőt is hozzáadjuk az adatokhoz
            feldolgozott.append({
                'Tura': t_nev,
                'PartnerKulcs': f"{p_nev} ({cim})", 
                'Megj': str(megj), 
                'Tetel': tetel, 
                'Db': db, 
                'Kg': kg
            })

        # --- ÚJ: Mentés az ideiglenes JSON fájlba a mod_turak_excelbol számára ---
        try:
            with open("temp_excel_adatok.json", "w", encoding="utf-8") as f:
                json.dump(feldolgozott, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Hiba az ideiglenes mentésnél: {e}")
        # -----------------------------------------------------------------------

        f_df = pd.DataFrame(feldolgozott)
        # Megjegyzés: A visszatérési érték a GUI listához csoportosít, de a JSON-ban minden sor benne marad
        return f_df.groupby(['PartnerKulcs', 'Megj', 'Tetel'], as_index=False).agg({'Db':'sum', 'Kg':'sum'}) if not f_df.empty else f_df


# --- FŐ ALKALMAZÁS ---
class TuraApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ProLog Tervező v1.1 - MODULÁRIS")
        self.autok_p = "autok.txt"
        self.sofor_p = "soforok.txt"
        self.txt_p = "turanevek.txt"
        self.alap_m = r"C:\Users\User\Downloads"
        self.bold_f = QFont(); self.bold_f.setBold(True)
        
        self.setStyleSheet("""
            QLineEdit { border: 2px solid #0078d7; padding: 5px; } 
            QTreeWidget { show-decoration-selected: 1; outline: 0; }
            QTreeWidget::item { border-bottom: 1px solid #eee; border-right: 1px solid #eee; padding: 6px; }
            QTreeWidget::item:selected { background-color: #d4edda; color: black; border: 1px solid #c3e6cb; }
        """)

        c = QWidget(); self.setCentralWidget(c); l = QVBoxLayout(c)
        t_b = QHBoxLayout()
        self.mod_b = QPushButton("☰ MODULOK"); self.mod_b.setStyleSheet("background-color: #8e44ad; color: white; font-weight: bold; padding: 8px;")
        self.mod_menu = QMenu(self)
        self.mod_menu.addAction("🚗 Rendszámok").triggered.connect(lambda: self.lista_sz("Rendszámok", self.autok_p))
        self.mod_menu.addAction("👤 Sofőrök").triggered.connect(lambda: self.lista_sz("Sofőrök", self.sofor_p))
        self.mod_b.setMenu(self.mod_menu)
        
        self.i_b = QPushButton("EXCEL BETÖLTÉSE"); self.i_b.setStyleSheet("background-color: #FF8C00; color: white; font-weight: bold; padding: 8px;")
        self.e_b = QPushButton("TÚRÁK MENTÉSE"); self.e_b.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.p_b = QPushButton("NYOMTATÁS"); self.p_b.setStyleSheet("background-color: #0078d7; color: white; font-weight: bold; padding: 8px;")
        self.i_b.clicked.connect(self.betoltes); self.e_b.clicked.connect(self.mentes_ex); self.p_b.clicked.connect(self.show_print)
        t_b.addWidget(self.mod_b); t_b.addWidget(self.i_b); t_b.addWidget(self.e_b); t_b.addStretch(); t_b.addWidget(self.p_b); l.addLayout(t_b)

        self.s = QSplitter(Qt.Orientation.Horizontal)
        l_p = QWidget(); l_l = QVBoxLayout(l_p); self.s_l = QLineEdit(); self.s_l.setPlaceholderText("Keresés..."); l_l.addWidget(self.s_l)
        self.left_tree = QTreeWidget(); self.left_tree.setHeaderLabels(["Partner / Cím", "Tétel", "Db", "Kg", "Megjegyzés"]); self.left_tree.setDragEnabled(True); l_l.addWidget(self.left_tree); self.s.addWidget(l_p)
        r_p = QWidget(); r_l = QVBoxLayout(r_p); self.s_r = QLineEdit(); self.s_r.setPlaceholderText("Keresés..."); r_l.addWidget(self.s_r)
        b_b = QHBoxLayout()
        self.a_b = QPushButton("+ Új Túra"); self.a_b.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; padding: 6px;")
        self.v_b = QPushButton("Vissza balra"); self.v_b.setStyleSheet("background-color: #bdc3c7; color: black; font-weight: bold; padding: 6px;")
        self.d_b = QPushButton("Túra törlése"); self.d_b.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold; padding: 6px;")
        self.a_b.clicked.connect(self.tura_val); self.v_b.clicked.connect(self.visszakuldes_balra); self.d_b.clicked.connect(self.tura_torl)
        b_b.addWidget(self.a_b); b_b.addWidget(self.v_b); b_b.addWidget(self.d_b); r_l.addLayout(b_b)
        self.right_tree = QTreeWidget(); self.right_tree.setColumnCount(8); self.right_tree.setHeaderLabels(["Partner / Cím", "Ki", "Be", "Db", "Kg", "Megjegyzés", "Rendszám", "Sofőr"])
        self.right_tree.setAcceptDrops(True); self.right_tree.setDragEnabled(True); self.right_tree.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop); self.right_tree.dropEvent = self.treeDrop
        r_l.addWidget(self.right_tree); self.s.addWidget(r_p); l.addWidget(self.s)
        self.s_l.textChanged.connect(self.szures_bal); self.s_r.textChanged.connect(self.szures_jobb)

        # --- MODULBETÖLTŐ RENDSZER ---
        self.betoltott_modulok = []
        self.automatikus_modul_kereses()
        
        QTimer.singleShot(200, self.beallit_aranyokat); self.showMaximized()

    def automatikus_modul_kereses(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        for fn in os.listdir(base_dir):
            if fn.startswith("mod_") and fn.endswith(".py"):
                mod_name = fn[:-3]
                try:
                    spec = importlib.util.spec_from_file_location(mod_name, os.path.join(base_dir, fn))
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, 'ModulInit'):
                        self.betoltott_modulok.append(mod.ModulInit(self))
                except Exception as e: print(f"Modul hiba ({mod_name}): {e}")

    def beallit_aranyokat(self):
        sz = self.width(); egy_h = sz // 3; self.s.setSizes([egy_h, sz - egy_h])
        self.left_tree.setColumnWidth(0, 200); self.right_tree.setColumnWidth(0, 250)

    def betolt_lst(self, p): return [l.strip() for l in open(p, "r", encoding="utf-8") if l.strip()] if os.path.exists(p) else ["Válassz..."]
    def lista_sz(self, n, p):
        t, ok = QInputDialog.getMultiLineText(self, n, f"{n}:", "\n".join(self.betolt_lst(p)))
        if ok: open(p, "w", encoding="utf-8").write(t); self.frissit_cb()

    def frissit_cb(self):
        for i in range(self.right_tree.topLevelItemCount()):
            t = self.right_tree.topLevelItem(i)
            if t.data(0, Qt.ItemDataRole.UserRole) == "TURA":
                cb_r = self.right_tree.itemWidget(t, 6); cb_s = self.right_tree.itemWidget(t, 7)
                if cb_r: a = cb_r.currentText(); cb_r.clear(); cb_r.addItems(self.betolt_lst(self.autok_p)); cb_r.setCurrentText(a)
                if cb_s: a = cb_s.currentText(); cb_s.clear(); cb_s.addItems(self.betolt_lst(self.sofor_p)); cb_s.setCurrentText(a)

    def add_tura_item(self, n):
        it = QTreeWidgetItem(self.right_tree, [n, "", "", "", "0.0 kg", "", "", ""])
        it.setData(0, Qt.ItemDataRole.UserRole, "TURA"); it.setExpanded(True); it.setFont(0, self.bold_f); it.setFont(4, self.bold_f); it.setBackground(0, QColor("#e9ecef"))
        cb_r = QComboBox(); cb_r.addItems(self.betolt_lst(self.autok_p)); self.right_tree.setItemWidget(it, 6, cb_r)
        cb_s = QComboBox(); cb_s.addItems(self.betolt_lst(self.sofor_p)); self.right_tree.setItemWidget(it, 7, cb_s)
        return it

    def tura_val(self):
        # 1. Beolvassuk a neveket a txt-ből
        nevek = []
        if os.path.exists(self.txt_p):
           with open(self.txt_p, "r", encoding="utf-8") as f:
               nevek = sorted(list(set([l.strip() for l in f if l.strip()])))

        d = TuraValasztoDialog(nevek, self)
        if d.exec():
            # ÚJ TÚRA LÉTREHOZÁSA
            if d.valasztott == "__UJ__":
                u, ok = QInputDialog.getText(self, "Új túra", "Név:")
                if ok and u.strip():
                    nev = u.strip()
                    if nev not in nevek:
                       with open(self.txt_p, "a", encoding="utf-8") as f:
                           f.write(nev + "\n")
                self.add_tura_item(nev)
        
            # TÖRLÉS A LISTÁBÓL
            elif d.muvelet == "TORLES" and d.valasztott:
                valasz = QMessageBox.question(self, "Megerősítés", f"Biztosan törlöd a(z) '{d.valasztott}' túrát a listából?")
                if valasz == QMessageBox.StandardButton.Yes:
                   nevek.remove(d.valasztott)
                   with open(self.txt_p, "w", encoding="utf-8") as f:
                       f.write("\n".join(nevek) + "\n")
                   QMessageBox.information(self, "Siker", "Túra törölve a listából.")

            # ÁTNEVEZÉS A LISTÁBAN
            elif d.muvelet == "ATNEVEZES" and d.valasztott:
                u, ok = QInputDialog.getText(self, "Átnevezés", f"Új név a(z) '{d.valasztott}' helyett:", text=d.valasztott)
                if ok and u.strip():
                   uj_nev = u.strip()
                   nevek = [uj_nev if n == d.valasztott else n for n in nevek]
                   with open(self.txt_p, "w", encoding="utf-8") as f:
                       f.write("\n".join(nevek) + "\n")
                   QMessageBox.information(self, "Siker", "Túra átnevezve.")

            # SIMA KIVÁLASZTÁS ÉS HOZZÁADÁS
            elif d.valasztott:
                self.add_tura_item(d.valasztott)

    def treeDrop(self, e):
        target = self.right_tree.itemAt(e.position().toPoint())
        if e.source() == self.left_tree:
            if not target and self.right_tree.topLevelItemCount() > 0: target = self.right_tree.topLevelItem(self.right_tree.topLevelItemCount()-1)
            if not target: return
            while target.parent(): target = target.parent()
            for it in list(self.left_tree.selectedItems()):
                p = it if it.data(0, Qt.ItemDataRole.UserRole) == "PARENT" else it.parent()
                if p:
                    ex = None
                    for i in range(target.childCount()):
                        if target.child(i).text(0) == p.text(0): ex = target.child(i); break
                    if not ex:
                        ex = QTreeWidgetItem(target, [p.text(0), "", "", p.text(2), p.text(3), p.text(4), "", ""])
                        ex.setData(0, Qt.ItemDataRole.UserRole, "PARTNER"); ex.setData(0, Qt.ItemDataRole.UserRole + 1, p.text(4))
                    while p.childCount() > 0:
                        c = p.takeChild(0); tt = c.text(1); ki, be = (tt, "") if tt.startswith("K-") else ("", tt)
                        ex.addChild(QTreeWidgetItem(["", ki, be, c.text(2), c.text(3), "", "", ""]))
                    self.left_tree.takeTopLevelItem(self.left_tree.indexOfTopLevelItem(p))
            self.recalculate(); e.acceptProposedAction()
        elif e.source() == self.right_tree:
            sel = self.right_tree.selectedItems(); p_items = [i for i in sel if i.data(0, Qt.ItemDataRole.UserRole) == "PARTNER"]
            if not p_items or not target: return
            t_tura = target if target.data(0, Qt.ItemDataRole.UserRole) == "TURA" else target.parent()
            idx = t_tura.indexOfChild(target) if target != t_tura else 0
            for p in p_items:
                if p.parent(): p.parent().takeChild(p.parent().indexOfChild(p))
                t_tura.insertChild(idx, p)
            self.recalculate(); e.acceptProposedAction()

    def recalculate(self):
        for i in range(self.right_tree.topLevelItemCount()):
            t = self.right_tree.topLevelItem(i)
            if t.data(0, Qt.ItemDataRole.UserRole) == "TURA":
                ts = 0.0
                for j in range(t.childCount()):
                    p = t.child(j); ps = sum(float(p.child(k).text(4).replace(" kg", "")) for k in range(p.childCount()))
                    ts += ps
                t.setText(4, f"{ts:.1f} kg")

    def betoltes(self):
        fix_utvonal = "C:\\Users\\szilv\\Downloads"
        path, _ = QFileDialog.getOpenFileName(self, "Excel", fix_utvonal, "Excel (*.xlsx *.xlsm)")
        if path:
            try:
                df = AdatMotor.nyers_adat_tisztitas(pd.read_excel(path)); self.left_tree.clear()
                for _, group in df.groupby('PartnerKulcs'):
                    p_name = str(group['PartnerKulcs'].iloc[0]); megj = str(group['Megj'].iloc[0]); pkg = sum(group['Kg'])
                    p_item = QTreeWidgetItem(self.left_tree, [p_name, "", "", f"{pkg:.1f} kg", megj])
                    p_item.setData(0, Qt.ItemDataRole.UserRole, "PARENT"); p_item.setFont(0, self.bold_f)
                    for _, r in group.iterrows(): QTreeWidgetItem(p_item, ["", r['Tetel'], f"{r['Db']:.0f}", f"{r['Kg']:.1f} kg", ""])
                self.left_tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)
            except Exception as e: QMessageBox.critical(self, "Hiba", str(e))

    def szures_bal(self, t):
        for i in range(self.left_tree.topLevelItemCount()): self.left_tree.topLevelItem(i).setHidden(t.lower() not in self.left_tree.topLevelItem(i).text(0).lower())
    def szures_jobb(self, t):
        for i in range(self.right_tree.topLevelItemCount()):
            it = self.right_tree.topLevelItem(i)
            if it.data(0, Qt.ItemDataRole.UserRole) == "TURA": it.setHidden(t.lower() not in it.text(0).lower())

    def tura_torl(self):
        t = self.right_tree.currentItem()
        if t and t.data(0, Qt.ItemDataRole.UserRole) == "TURA":
            if QMessageBox.question(self, "Törlés", "Törlöd?") == QMessageBox.StandardButton.Yes:
                while t.childCount() > 0: self.visszakuldes_balra(t.child(0))
                self.right_tree.takeTopLevelItem(self.right_tree.indexOfTopLevelItem(t))

    def visszakuldes_balra(self, item=None):
        it = item if item else self.right_tree.currentItem()
        if it and it.data(0, Qt.ItemDataRole.UserRole) == "PARTNER":
            osszsuly = 0.0; rows = []
            while it.childCount() > 0:
                c = it.takeChild(0); s = float(c.text(4).replace(" kg", "")); osszsuly += s
                rows.append([c.text(1) if c.text(1) else c.text(2), c.text(3), c.text(4)])
            lp = QTreeWidgetItem(self.left_tree, [it.text(0), "", "", f"{osszsuly:.1f} kg", it.data(0, Qt.ItemDataRole.UserRole+1)])
            lp.setData(0, Qt.ItemDataRole.UserRole, "PARENT"); lp.setFont(0, self.bold_f)
            for r in rows: QTreeWidgetItem(lp, ["", r[0], r[1], r[2], ""])
            it.parent().removeChild(it); self.left_tree.sortByColumn(0, Qt.SortOrder.AscendingOrder); self.recalculate()

    def mentes_ex(self):
        p, _ = QFileDialog.getSaveFileName(self, "Mentés", "Turak.xlsx", "Excel (*.xlsx)")
        if p:
            with pd.ExcelWriter(p, engine='xlsxwriter') as wr:
                for i in range(self.right_tree.topLevelItemCount()):
                    t = self.right_tree.topLevelItem(i)
                    if t.childCount() > 0:
                        cb_r = self.right_tree.itemWidget(t, 6); rsz = cb_r.currentText() if cb_r else ""
                        rows = []
                        for j in range(t.childCount()):
                            part = t.child(j)
                            for k in range(part.childCount()):
                                c = part.child(k); rows.append([part.text(0), c.text(1), c.text(2), c.text(3), c.text(4), part.data(0, Qt.ItemDataRole.UserRole+1)])
                        pd.DataFrame(rows, columns=['Partner', 'Ki', 'Be', 'Db', 'Kg', 'Megj']).to_excel(wr, sheet_name=t.text(0)[:20], index=False)

    def show_print(self):
        pr = QPrinter(QPrinter.PrinterMode.HighResolution); pr.setPageOrientation(QPageLayout.Orientation.Landscape)
        dlg = QPrintPreviewDialog(pr, self); dlg.paintRequested.connect(self.handle_p); dlg.showMaximized(); dlg.exec()

    def handle_p(self, p):
        doc = QTextDocument()
        style = "<style>@page { margin: 0.5cm; } body { font-family: sans-serif; font-size: 9pt; } .t-block { page-break-before: always; border: 2px solid #333; padding: 10px; } table { width: 100%; border-collapse: collapse; } th, td { border: 1px solid #333; padding: 4px; } .sum-t { margin-top: 10px; width: 450px; border: 2px solid #0078d7; }</style>"
        html = ""
        for i in range(self.right_tree.topLevelItemCount()):
            t = self.right_tree.topLevelItem(i)
            if t.childCount() == 0: continue
            rsz = self.right_tree.itemWidget(t, 6).currentText() if self.right_tree.itemWidget(t, 6) else ""
            sof = self.right_tree.itemWidget(t, 7).currentText() if self.right_tree.itemWidget(t, 7) else ""
            tk, kisz, besz = 0.0, {}, {}
            kisz_sum, besz_sum = 0.0, 0.0
            table = f"<div class='t-block'><h2>Túra: {t.text(0)} | Rendszám: {rsz} | Sofőr: {sof}</h2><table><tr><th>Partner</th><th>KI</th><th>BE</th><th>Db</th><th>Kg</th><th>Megjegyzés</th></tr>"
            for j in range(t.childCount()):
                pi = t.child(j)
                for k in range(pi.childCount()):
                    c = pi.child(k); ki, be = c.text(1), c.text(2)
                    try:
                        db_v = float(c.text(3).replace(" db", "")); kg_v = float(c.text(4).replace(" kg", ""))
                    except: db_v, kg_v = 0.0, 0.0
                    tk += kg_v
                    if ki: 
                        d = kisz.get(ki, {'db':0, 'kg':0}); d['db']+=db_v; d['kg']+=kg_v; kisz[ki] = d; kisz_sum += kg_v
                    if be: 
                        d = besz.get(be, {'db':0, 'kg':0}); d['db']+=db_v; d['kg']+=kg_v; besz[be] = d; besz_sum += kg_v
                    table += f"<tr><td>{pi.text(0) if k==0 else ''}</td><td>{ki}</td><td>{be}</td><td>{db_v:.0f}</td><td>{kg_v:.1f}</td><td>{pi.data(0, Qt.ItemDataRole.UserRole+1) if k==0 else ''}</td></tr>"
            table += f"<tr><td colspan='4' align='right'>Összesen:</td><td>{tk:.1f} kg</td><td></td></tr></table>"
            sum_h = "<table class='sum-t'><tr><th colspan='3' style='background:#0078d7;color:white'>TÉTEL ÖSSZESÍTŐ</th></tr>"
            if kisz:
                sum_h += f"<tr style='background:#f2f9ff'><td colspan='2'><b>KISZÁLLÍTÁS ÖSSZESEN:</b></td><td><b>{kisz_sum:.1f} kg</b></td></tr>"
                for k, v in sorted(kisz.items()): sum_h += f"<tr><td>{k}</td><td>{v['db']:.0f} db</td><td>{v['kg']:.1f} kg</td></tr>"
            if besz:
                sum_h += f"<tr style='background:#f2f9ff'><td colspan='2'><b>BESZÁLLÍTÁS ÖSSZESEN:</b></td><td><b>{besz_sum:.1f} kg</b></td></tr>"
                for k, v in sorted(besz.items()): sum_h += f"<tr><td>{k}</td><td>{v['db']:.0f} db</td><td>{v['kg']:.1f} kg</td></tr>"
            html += table + sum_h + "</table></div>"
        doc.setHtml(f"<html><head>{style}</head><body>{html}</body></html>"); doc.print(p)

class TuraValasztoDialog(QDialog):
    def __init__(self, nevek, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Túra választása")
        self.valasztott = None
        self.muvelet = "HOZZAAD" # Alapértelmezett művelet
        
        layout = QVBoxLayout(self)
        self.listbox = QListWidget()
        self.listbox.addItems(nevek)
        layout.addWidget(self.listbox)
        
        btn_layout = QHBoxLayout()
        
        # Hozzáadás gomb
        ok_btn = QPushButton("Kiválasztás")
        ok_btn.clicked.connect(self.accept)
        
        # Új gomb
        uj_btn = QPushButton("+ Új")
        uj_btn.clicked.connect(self.uj_tura)
        
        # Átnevezés gomb
        atn_btn = QPushButton("✎")
        atn_btn.clicked.connect(self.atnevezes)
        
        # Törlés gomb
        del_btn = QPushButton("🗑")
        del_btn.clicked.connect(self.torles)
        
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(uj_btn)
        btn_layout.addWidget(atn_btn)
        btn_layout.addWidget(del_btn)
        layout.addLayout(btn_layout)

    def uj_tura(self):
        self.valasztott = "__UJ__"
        self.accept()

    def atnevezes(self):
        if self.listbox.currentItem():
            self.valasztott = self.listbox.currentItem().text()
            self.muvelet = "ATNEVEZES"
            self.accept()

    def torles(self):
        if self.listbox.currentItem():
            self.valasztott = self.listbox.currentItem().text()
            self.muvelet = "TORLES"
            self.accept()

    def accept(self):
        if not self.valasztott and self.listbox.currentItem():
            self.valasztott = self.listbox.currentItem().text()
        super().accept()

if __name__ == "__main__":
    app = QApplication(sys.argv); win = TuraApp(); win.show(); sys.exit(app.exec())