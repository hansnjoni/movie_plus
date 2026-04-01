import sys
import os
import requests
import threading
import time
import json
import zipfile
import io
import traceback
import webbrowser
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QScrollArea, 
                             QLabel, QGridLayout, QFrame, QCheckBox, QRadioButton, 
                             QButtonGroup, QDialog, QComboBox, QTextEdit, QShortcut)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer, QUrl
from PyQt5.QtGui import QPixmap, QImage, QFont, QKeySequence
from concurrent.futures import ThreadPoolExecutor

from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineProfile

# --- CATCH SILENT CRASHES ---
def global_exception_handler(exc_type, exc_value, exc_traceback):
    print("\n💥 CRITICAL SYSTEM FAILURE CAUGHT 💥")
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    print("--------------------------------------------------\n")
sys.excepthook = global_exception_handler

# --- HANS' PRIVATE MASTER SPECS ---
STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"

SETTINGS_FILE = "settings.json"
HISTORY_FILE = "history.json"
LOGO_PATH = "logo.png"
REPO_URL = "https://github.com/mmohamedemy/TMDB-Embed-API/archive/refs/heads/main.zip"

STYLESHEET = """
QMainWindow { background-color: #02040a; }
QFrame#Sidebar { background-color: #080808; border-right: 1px solid #222; }
QLabel { color: #ff0000; font-family: 'Segoe UI'; font-weight: bold; }
QLineEdit { background-color: #111; border: 1px solid #ff0000; border-radius: 5px; color: white; padding: 12px; margin-right: 30px; }
QTextEdit#Manual { background-color: #050505; color: #00ff00; border: 1px solid #330066; font-family: 'Segoe UI'; font-size: 14px; }

QWidget#GalleryContainer { background-color: #02040a; }
QScrollArea { border: none; background-color: #02040a; }
QWidget#ContentArea { background-color: #02040a; }

QFrame#MovieCard { 
    background-color: #1a0033; 
    border-radius: 12px; 
    border: 1px solid #330066;
    margin: 5px;
    padding: 10px;
    min-width: 170px;
    max-width: 170px;
}

QPushButton { 
    background-color: #0f0f0f; 
    color: #ff3333; 
    border: 2px solid #aa0000; 
    border-radius: 10px; 
    padding: 8px; 
    font-weight: bold; 
}
QPushButton:hover { background-color: #111; color: #ffffff; border: 2px solid #00ff00; }
QPushButton#WatchBtn { background-color: #008800; color: white; border: 2px solid #00ff00; }
QPushButton#WatchBtn:hover { background-color: #00ff00; color: black; }
QRadioButton { color: #888; font-weight: bold; }
QRadioButton:checked { color: #00ff00; }
QComboBox { background: #111; color: white; border: 1px solid #ff0000; padding: 5px; }
QCheckBox { color: #ff3333; font-weight: bold; }

QTextEdit#Console {
    background-color: #050505;
    color: #00ff00;
    border: 1px solid #330066;
    border-radius: 5px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 11px;
    padding: 5px;
    margin-top: 10px;
}

QTextEdit#Blueprint {
    background-color: #050505;
    color: #00ffff;
    border: 1px solid #330066;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    padding: 10px;
}
"""

class SignalHandler(QObject):
    log_signal = pyqtSignal(str)
    item_signal = pyqtSignal(dict, QPixmap, int, str, int)
    clear_signal = pyqtSignal()

class DeveloperSwitchboard(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎛️ DEVELOPER SWITCHBOARD (Internal Overrides)")
        self.setFixedSize(500, 400)
        self.setStyleSheet(STYLESHEET)
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("⚠️ WARNING: ADVANCED PERFORMANCE CONTROLS"))
        
        self.turbo_check = QCheckBox("🏎️ V8 Turbo Engine (Use 20 background threads instead of 5)")
        self.turbo_check.setChecked(settings.get("dev_turbo", False))
        layout.addWidget(self.turbo_check)
        
        self.data_check = QCheckBox("📡 Data Saver Mode (Disable all image/poster downloading)")
        self.data_check.setChecked(settings.get("dev_datasaver", False))
        layout.addWidget(self.data_check)
        
        self.silent_check = QCheckBox("🔕 Silent Running (Turn off UI Telemetry to save rendering CPU)")
        self.silent_check.setChecked(settings.get("dev_silent", False))
        layout.addWidget(self.silent_check)
        
        self.boot_check = QCheckBox("⚡ Fast Boot (Bypass GitHub provider checks on startup)")
        self.boot_check.setChecked(settings.get("dev_fastboot", False))
        layout.addWidget(self.boot_check)
        
        layout.addWidget(QLabel("\n⏳ QUARANTINE WINDOW (Days before Vidsrc gets digital copy):"))
        self.quarantine_input = QLineEdit(str(settings.get("quarantine_days", 90)))
        layout.addWidget(self.quarantine_input)
        
        layout.addStretch()
        
        save = QPushButton("💾 APPLY OVERRIDES AND REBOOT ENGINE")
        save.setObjectName("WatchBtn")
        save.clicked.connect(self.accept)
        layout.addWidget(save)

class HelpManual(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("STARK SYSTEMS - OPERATING MANUAL")
        self.setFixedSize(650, 600)
        self.setStyleSheet(STYLESHEET)
        layout = QVBoxLayout(self)
        self.text = QTextEdit()
        self.text.setObjectName("Manual")
        self.text.setReadOnly(True)
        self.text.setHtml("""
<h2 style='color: #00ff00;'>STARK CINEMA SETUP GUIDE</h2>
<p><b>STEP 1: THE TOKEN</b><br>Paste your LONG 'Read Access Token' from themoviedb.org into the Token box in Settings.</p>
<p><b>STEP 2: FULL SCREEN</b><br>The movie will now launch perfectly in your browser so you can adjust the resolution.</p>
        """)
        layout.addWidget(self.text)
        btn = QPushButton("CLOSE")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("System Settings")
        self.setFixedSize(550, 400)
        self.setStyleSheet(STY
