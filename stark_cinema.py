
import sys, os, requests, threading, time, json, webbrowser, re, subprocess
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# --- JARVIS SUBSYSTEM INITIALIZATION ---
VOICE_ON = True 
VOICE_READY = False
try:
    import speech_recognition as sr
    import pyaudio
    VOICE_READY = True
except: pass

YT_READY = False
try:
    from youtubesearchpython import VideosSearch
    YT_READY = True
except: pass

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QScrollArea, 
                             QLabel, QGridLayout, QFrame, QTextEdit, 
                             QSystemTrayIcon, QMenu, QAction, QStyle)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap

# --- SIGNAL HANDLER ---
class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int)
    log_signal = pyqtSignal(str); clear_signal = pyqtSignal()
    voice_status = pyqtSignal(str)

STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"

class MovieCard(QFrame):
    def __init__(self, item, pix, mtype, parent_app):
        super().__init__()
        self.setObjectName("MovieCard"); self.setFixedSize(170, 300)
        self.item = item; self.parent_app = parent_app; self.mtype = mtype
        layout = QVBoxLayout(self)
        self.poster = QLabel(); self.poster.setPixmap(pix); layout.addWidget(self.poster, alignment=Qt.AlignCenter)
        self.title_str = (item.get('title') or item.get('name'))[:18]
        self.title_lbl = QLabel(self.title_str); self.title_lbl.setStyleSheet("color: white; font-size: 10px;"); layout.addWidget(self.title_lbl, alignment=Qt.AlignCenter)
        self.btn = QPushButton("WATCH"); self.btn.clicked.connect(lambda: parent_app.initiate_watch_protocol(item, mtype))
        layout.addWidget(self.btn)

    def enterEvent(self, event):
        # VISION INTEL: Live metadata dump on hover
        rating = self.item.get('vote_average', 'N/A')
        summary = self.item.get('overview', 'No data available.')[:150] + "..."
        self.parent_app.signals.log_signal.emit(f"🔍 INTEL: {self.title_str} | ⭐ {rating}\n📝 {summary}")

class StarkCinemaSingularity(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stark Cinema - The Singularity V30.0")
        self.resize(1500, 920)
        self.setStyleSheet("""
            QMainWindow { background-color: #1a0033; }
            QFrame#Sidebar { background-color: #0f001a; border-right: 2px solid #ff0000; }
            QLabel { color: #ff0000; font-family: 'Segoe UI'; font-weight: bold; }
            QScrollArea { background-color: #1a0033; border: none; }
            QWidget#Gallery { background-color: #2e004b; padding-right: 10px; }
            QFrame#MovieCard { background-color: #1a0000; border-radius: 10px; border: 2px solid #ff0000; padding: 5px; }
            QFrame#MovieCard:hover { border: 2px solid #00ff00; background-color: #001a00; }
            QLineEdit { background-color: #111; border: 2px solid #ff0000; border-radius: 8px; color: #00ff00; padding: 12px; }
            QPushButton { background-color: #111; color: #ff3333; border: 1px solid #aa0000; border-radius: 8px; padding: 8px; font-weight: bold; }
            QPushButton#LiveOn { background-color: #004400; color: #00ff00; border: 2px solid #00ff00; }
            QPushButton#LiveOff { background-color: #330000; color: #ff0000; border: 1px solid #ff0000; }
            QTextEdit#Console { background-color: #000; color: #00ff00; border: 1px solid #ff0000; font-family: 'Consolas'; font-size: 11px; }
        """)
        
        self.is_live_mode = False; self.auto_pilot = False
        self.speak_lock = threading.Lock() 
        self.task_counter = 0; self.current_mode = "movie"
        self.current_title = None; self.current_mid = None; self.current_mtype = None
        
        self.executor = ThreadPoolExecutor(max_workers=15)
        self.signals = SignalHandler()
        self.signals.item_signal.connect(self.add_item_to_ui)
        self.signals.log_signal.connect(lambda m: self.console.append(f"[{datetime.now().strftime('%H:%M:%S')}] {m}"))
        self.signals.clear_signal.connect(self.clear_gallery)
        
        self.init_ui(); self.setup_tray(); self.run_fresh_trending()
        self.speak("Singularity Build online. Welcome back, Boss.")

    def speak(self, text):
        if not VOICE_ON: return
        def run_speech():
            with self.speak_lock: 
                clean_text = text.replace("'", "")
                cmd = f'PowerShell -Command "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{clean_text}\');"'
                subprocess.run(cmd, shell=True)
        threading.Thread(target=run_speech, daemon=True).start()

    def toggle_live_mode(self):
        self.is_live_mode = not self.is_live_mode
        if self.is_live_mode:
            self.live_btn.setText("🎙️ LIVE MODE: ACTIVE"); self.live_btn.setObjectName("LiveOn")
            self.speak("Live link established. I'm listening.")
            threading.Thread(target=self.live_voice_loop, daemon=True).start()
        else:
            self.live_btn.setText("🎙️ LIVE MODE: STANDBY"); self.live_btn.setObjectName("LiveOff")
            self.speak("Live link terminated.")
        self.setStyleSheet(self.styleSheet())

    def live_voice_loop(self):
        r = sr.Recognizer()
        while self.is_live_mode:
            if self.speak_lock.locked(): 
                time.sleep(0.5); continue
            with sr.Microphone() as src:
                try:
                    audio = r.listen(src, timeout=3, phrase_time_limit=5)
                    q = r.recognize_google(audio).lower()
                    self.signals.log_signal.emit(f"🗣️ Live Input: '{q}'")
                    
                    if any(x in q for x in ["stop", "off", "standby"]):
                        self.is_live_mode = False; break
                    
                    if "play" in q:
                        self.auto_pilot = True
                        target = q.replace("play", "").replace("the movie", "").strip()
                        self.speak(f"Processing command. Hunting for {target}.")
                        self.search_bar.setText(target)
                    else:
                        self.speak(f"Searching for {q}.")
                        self.search_bar.setText(q)
                    self.process_command()
                except: pass
            time.sleep(0.1)

    def initiate_watch_protocol(self, item, mtype):
        self.current_mid = item['id']; self.current_mtype = mtype
        self.current_title = item.get('title') or item.get('name')
        self.speak(f"Running link health check for {self.current_title}.")
        threading.Thread(target=self.sentinel_worker, daemon=True).start()

    def sentinel_worker(self):
        mirrors = [
            f"https://vidsrc.me/embed/{self.current_mtype}?tmdb={self.current_mid}",
            f"https://vidsrc.to/embed/{self.current_mtype}/{self.current_mid}",
            f"https://vidsrc.cc/v2/embed/{self.current_mtype}/{self.current_mid}"
        ]
        for url in mirrors:
            try:
                if requests.head(url, timeout=1.5).status_code == 200:
                    self.speak("Link secured. Enjoy.")
                    webbrowser.open(url); return
            except: continue
        
        self.speak("Primary mirrors failed. Running YouTube Ghost Recon.")
        threading.Thread(target=self.yt_worker, daemon=True).start()

    def yt_worker(self):
        try:
            # GHOST RECON: Prioritizes links from the last 30 days
            query = f"{self.current_title} full movie 2026 new link"
            search = VideosSearch(query, limit=5)
            results = search.result()['result']
            for video in results:
                pub = video.get('publishedTime', 'unknown').lower()
                if any(x in pub for x in ["month", "year"]): continue
                
                links = re.findall(r'(https?://[^\s]+)', "".join([d['text'] for d in video.get('descriptionSnippet', [])]))
                if links:
                    self.speak("Fresh social link detected. Launching.")
                    webbrowser.open(links[0]); return
            self.speak(f"I'm sorry Boss, no live links found for {self.current_title}.")
        except: pass

    def init_ui(self):
        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central); layout.setContentsMargins(0,
