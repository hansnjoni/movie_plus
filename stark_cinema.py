import sys, os, requests, threading, time, json, webbrowser, subprocess, re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# --- PERMANENT MEMORY ---
MEMORY_DIR = "jarvis_memory"
if not os.path.exists(MEMORY_DIR): os.makedirs(MEMORY_DIR)

def save_vault(filename, data):
    with open(os.path.join(MEMORY_DIR, filename), 'w') as f:
        json.dump(data, f, indent=4)

def load_vault(filename, default):
    path = os.path.join(MEMORY_DIR, filename)
    if not os.path.exists(path): save_vault(filename, default); return default
    with open(path, 'r') as f: return json.load(f)

# Grounding the User Data
USER = load_vault("user_profile.json", {"name": "Hans", "birthday": "04-02"})
STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QScrollArea, QLabel, QGridLayout, 
                             QFrame, QTextEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap

class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int, int, int)
    log_signal = pyqtSignal(str); clear_signal = pyqtSignal(); search_trigger = pyqtSignal(str, int, int)

class StarkCinemaSingularity(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Stark Cinema - Booster Station V93.2")
        self.resize(1500, 950)
        
        # --- CIRCUIT INITIALIZATION ---
        self.task_counter = 0 
        self.is_live_mode = False
        self.is_speaking = False
        self.executor = ThreadPoolExecutor(max_workers=20)
        self.signals = SignalHandler()
        
        # Mapping the Signal Lines
        self.signals.item_signal.connect(self.add_item_to_ui)
        self.signals.log_signal.connect(lambda m: self.console.append(m))
        self.signals.clear_signal.connect(self.clear_gallery)
        self.signals.search_trigger.connect(self.trigger_search)
        
        self.init_ui()
        self.run_fresh_trending()
        self.signals.log_signal.emit("⚡ [SYSTEM READY]: All Booster Stations Grounded and Operational.")

    def speak(self, text):
        self.signals.log_signal.emit(f"JARVIS: {text}")
        def run_speech():
            self.is_speaking = True
            clean_text = text.replace("'", "").replace('"', "")
            # Direct Access to SAPI with High CPU Priority
            cmd = ["powershell", "-WindowStyle", "Hidden", "-Command", 
                   f"$s = New-Object -ComObject SAPI.SpVoice; $s.Priority = 2; $s.Speak('{clean_text}')"]
            subprocess.run(cmd) 
            self.is_speaking = False
        threading.Thread(target=run_speech, daemon=True).start()

    def init_ui(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #000000; }
            QFrame#Sidebar { background-color: #050505; border-right: 3px solid #FF0000; }
            QLabel { color: #FF0000; font-family: 'Segoe UI'; font-weight: bold; }
            QPushButton { background-color: #1a0000; color: #FF0000; border: 2px solid #FF0000; border-radius: 6px; padding: 12px; }
            QPushButton:hover { border: 2px solid #00FF00; color: #00FF00; }
            QLineEdit { background-color: #000; border: 2px solid #FF0000; color: #00FF00; padding: 12px; font-family: 'Consolas'; }
            QTextEdit#Console { background-color: #000; color: #00FF00; border: 1px solid #333; font-family: 'Consolas'; font-size: 11px; }
        """)
        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central); layout.setContentsMargins(0,0,0,0)
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(280); side_layout = QVBoxLayout(self.sidebar)
        self.live_btn = QPushButton("🎙️ ACTIVATE BOOSTER"); self.live_btn.clicked.connect(self.toggle_live_mode); side_layout.addWidget(self.live_btn)
        side_layout.addStretch(); self.console = QTextEdit(); self.console.setObjectName("Console"); self.console.setFixedHeight(350); side_layout.addWidget(self.console)
        layout.addWidget(self.sidebar)
        content = QWidget(); c_layout = QVBoxLayout(content)
        self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("High-pressure line monitoring active..."); c_layout.addWidget(self.search_bar)
        self.scroll = QScrollArea(); self.container = QWidget(); self.grid = QGridLayout(self.container); self.scroll.setWidget(self.container); self.scroll.setWidgetResizable(True); c_layout.addWidget(self.scroll); layout.addWidget(content)

    def live_voice_loop(self):
        import speech_recognition as sr
        r = sr.Recognizer()
        r.energy_threshold = 3500
        # SNAP-ACTION TIMING (The Faucet Valve)
        r.phrase_threshold = 0.3 
        r.non_speaking_duration = 0.2
        
        while self.is_live_mode:
            if self.is_speaking:
                time.sleep(0.05)
                continue
            try:
                with sr.Microphone() as src:
                    audio = r.listen(src, timeout=None, phrase_time_limit=10)
                    q = r.recognize_google(audio).lower()
                    self.signals.log_signal.emit(f"INPUT LOGGED: {q}")
                    
                    # TRIGGERING THE CLOSED LOOP
                    if any(x in q for x in ["play", "watch", "find", "search"]):
                        target = re.sub(r'play|watch|find|search|season \d+|episode \d+', '', q).strip()
                        self.signals.search_trigger.emit(target, 1, 1)
                        self.speak(f"Signal confirmed. Releasing {target} from the vault.")
                    elif "hi jarvis" in q or "you there" in q:
                        self.speak("Booster station is at full pressure, Hans.")
                    else:
                        self.speak(f"Acknowledged: {q}")
            except: continue

    def trigger_search(self, query, s, e): 
        self.start_thread(f"https://api.themoviedb
