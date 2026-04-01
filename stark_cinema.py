import sys, os, requests, threading, time, json, webbrowser
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QScrollArea, 
                             QLabel, QGridLayout, QFrame, QRadioButton, QTextEdit, 
                             QSystemTrayIcon, QMenu, QAction)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QIcon

# --- PREVIOUS SPECS REMAIN (STARK_TOKEN, JASON_FILE, etc.) ---
STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"
JASON_FILE = "status_cache.json"

class MoviePlusPro(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stark Cinema - Command Center v7.8")
        self.resize(1550, 950)
        
        # Track State
        self.current_mid = None
        self.current_mtype = None
        self.current_source = "Alpha"

        # 1. SETUP ENHANCED SYSTEM TRAY
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(60)) # Uses a default System Icon
            
        self.tray_menu = QMenu()
        
        # SOURCE SWITCHER
        self.switch_action = QAction("⚡ SWITCH SOURCE (ALPHA -> BRAVO)", self)
        self.switch_action.triggered.connect(self.toggle_source_from_tray)
        self.tray_menu.addAction(self.switch_action)

        # COPY LINK
        self.copy_action = QAction("📋 COPY DIRECT STREAM LINK", self)
        self.copy_action.triggered.connect(self.copy_link_to_clipboard)
        self.tray_menu.addAction(self.copy_action)

        self.tray_menu.addSeparator()

        # JASON MEMORY CONTROL
        self.cache_action = QAction("🗑️ JASON: WIPE MEMORY (CACHE RESET)", self)
        self.cache_action.triggered.connect(self.reset_jason_cache)
        self.tray_menu.addAction(self.cache_action)

        # QUICK GENRE SUB-MENU
        self.genre_menu = self.tray_menu.addMenu("📁 QUICK LAUNCH GENRE")
        for g_name, g_id in [("Action", 28), ("Horror", 27), ("Comedy", 35), ("True Crime", "80,99")]:
            action = QAction(g_name, self)
            action.triggered.connect(lambda ch, idx=g_id: self.run_genre(idx))
            self.genre_menu.addAction(action)

        self.tray_menu.addSeparator()
        
        # SHOW/HIDE UI
        self.view_action = QAction("👁️ SHOW/HIDE MAIN CONSOLE", self)
        self.view_action.triggered.connect(self.toggle_ui_visibility)
        self.tray_menu.addAction(self.view_action)

        self.exit_action = QAction("❌ EXIT SYSTEM", self)
        self.exit_action.triggered.connect(sys.exit)
        self.tray_menu.addAction(self.exit_action)
        
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()
        
        # (Standard UI/Logic Initialization continues below...)
        # ... [Previous init_ui, fetch_worker, etc. logic] ...

    # --- NEW TRAY FUNCTIONS ---

    def toggle_source_from_tray(self):
        if not self.current_mid: return
        self.current_source = "Bravo" if self.current_source == "Alpha" else "Alpha"
        self.switch_action.setText(f"⚡ SWITCH SOURCE ({self.current_source} MODE)")
        self.launch_movie(self.current_mid, self.current_mtype, auto_switch=True)

    def copy_link_to_clipboard(self):
        if not self.current_mid: return
        url = f"https://vidsrc.me/embed/{self.current_mtype}?tmdb={self.current_mid}" if self.current_source == "Alpha" else f"https://vidsrc.to/embed/{self.current_mtype}/{self.current_mid}"
        QApplication.clipboard().setText(url)
        self.tray_icon.showMessage("Stark Systems", "Link Copied to Clipboard", QSystemTrayIcon.Information, 2000)

    def reset_jason_cache(self):
        if os.path.exists(JASON_FILE):
            os.remove(JASON_FILE)
            self.tray_icon.showMessage("Stark Systems", "Jason's Cache Cleared", QSystemTrayIcon.Critical, 2000)

    def toggle_ui_visibility(self):
        if self.isVisible(): self.hide()
        else: self.show(); self.raise_(); self.activateWindow()

    def launch_movie(self, mid, mtype, auto_switch=False):
        """Standard Launch with Tray Update."""
        self.current_mid = mid; self.current_mtype = mtype
        url = f"https://vidsrc.me/embed/{mtype}?tmdb={mid}" if self.current_source == "Alpha" else f"https://vidsrc.to/embed/{mtype}/{mid}"
        webbrowser.open(url)
        if not auto_switch:
            self.tray_icon.showMessage("Stark Cinema", "Movie Launched. Right-click icon for Source Switch.", QSystemTrayIcon.Information, 3000)
