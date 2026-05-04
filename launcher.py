import sys
import subprocess
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

class TuraLauncher(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Túra Rendszerindító v1.0')
        self.setFixedSize(450, 300)
        
        # Sötétszürke háttér az egész ablaknak
        self.setStyleSheet("background-color: #2c3e50; border-radius: 10px;")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(15)

        # Címsor stílusosabb megjelenéssel
        label = QLabel("TÚRATERVEZŐ RENDSZER")
        font = QFont('Segoe UI', 16)
        font.setBold(True)
        label.setFont(font)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #ecf0f1; margin-bottom: 10px;")
        layout.addWidget(label)

        # Választó vonal
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #34495e;")
        layout.addWidget(line)

        # Napi Túratervező Gomb (Zöld)
        self.btn_napi = QPushButton("NAPI TÚRATERVEZŐ")
        self.btn_napi.setFixedHeight(60)
        self.btn_napi.setStyleSheet(self.get_button_style("#27ae60", "#2ecc71"))
        self.btn_napi.clicked.connect(self.indit_napi)
        layout.addWidget(self.btn_napi)

        # Fix Tervező Gomb (Kék)
        self.btn_fix = QPushButton("FIX TERVEZŐ (ÚJ MODUL)")
        self.btn_fix.setFixedHeight(60)
        self.btn_fix.setStyleSheet(self.get_button_style("#2980b9", "#3498db"))
        self.btn_fix.clicked.connect(self.indit_fix)
        layout.addWidget(self.btn_fix)

        self.setLayout(layout)

    def get_button_style(self, main_color, hover_color):
        return f"""
            QPushButton {{
                background-color: {main_color};
                color: white;
                border-radius: 8px;
                font-family: 'Segoe UI';
                font-size: 13px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                border: 1px solid white;
            }}
            QPushButton:pressed {{
                background-color: #bdc3c7;
            }}
        """

    def indit_napi(self):
        subprocess.Popen([sys.executable, "tervezo_stabil.py"])
        self.close()

    def indit_fix(self):
        # Ha még nincs meg a fájl, létrehozzuk üresen
        with open("fix_tervezo.py", "a"): pass
        subprocess.Popen([sys.executable, "fix_tervezo.py"])
        self.close()
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = TuraLauncher()
    ex.show()
    sys.exit(app.exec())

