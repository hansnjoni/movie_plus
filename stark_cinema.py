import sys, os, requests, threading, time, json, webbrowser, subprocess, re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# --- SYSTEM CONSTANTS ---
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
        self.setWindowTitle(f"Stark Cinema - Snap-Action V93.0")
        self.resize(1500, 950); self.is_live_mode = False; self.is_speaking = False
        self.executor = ThreadPoolExecutor(max_workers=20); self.signals = SignalHandler()
        
        self.signals.item_signal.connect(self.add_item_to_ui)
        self.signals.log_signal.connect(lambda m: self.console.append(m))
        self.signals.clear_signal.connect(self.clear_gallery)
        self.signals.search_trigger.connect(self.trigger_search)
        
        self.init_ui(); self.run_fresh_trending()
        self.signals.log_signal.emit("⚡ [SNAP-ACTION ACTIVE]: Zero-latency relay engaged.")

    def speak(self, text):
        self.signals.log_signal.emit(f"JARVIS: {text}")
        def run_speech():
            self.is_speaking = True
            clean_text = text.replace("'", "").replace('"', "")
            # Priority 2 + Detached process for instant 'Mouth'
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
        self.live_btn = QPushButton("🎙️ ACTIVATE RELAY"); self.live_btn.clicked.connect(self.toggle_live_mode); side_layout.addWidget(self.live_btn)
        side_layout.addStretch(); self.console = QTextEdit(); self.console.setObjectName("Console"); self.console.setFixedHeight(350); side_layout.addWidget(self.console)
        layout.addWidget(self.sidebar)
        content = QWidget(); c_layout = QVBoxLayout(content)
        self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("High-pressure line active..."); c_layout.addWidget(self.search_bar)
        self.scroll = QScrollArea(); self.container = QWidget(); self.grid = QGridLayout(self.container); self.scroll.setWidget(self.container); self.scroll.setWidgetResizable(True); c_layout.addWidget(self.scroll); layout.addWidget(content)

    def live_voice_loop(self):
        import speech_recognition as sr
        r = sr.Recognizer(); 
        r.energy_threshold = 3500
        # SNAP-ACTION TIMING:
        r.phrase_threshold = 0.3 # Reduced from 0.8 for instant cutoff
        r.non_speaking_duration = 0.2
        
        while self.is_live_mode:
            if self.is_speaking:
                time.sleep(0.05)
                continue
            try:
                with sr.Microphone() as src:
                    audio = r.listen(src, timeout=None, phrase_time_limit=10)
                    q = r.recognize_google(audio).lower()
                    self.signals.log_signal.emit(f"LOGGED: {q}")
                    
                    # --- INSTANT FIRE ---
                    if any(x in q for x in ["play", "watch", "find"]):
                        target = re.sub(r'play|watch|find', '', q).strip()
                        # Visuals fire first
                        self.signals.search_trigger.emit(target, 1, 1)
                        # Voice fires immediately after
                        self.speak(f"Displaying {target}.")
                    elif "hi jarvis" in q or "you there" in q:
                        self.speak("Standing by.")
                    else:
                        self.speak(f"Acknowledge: {q}")
            except: continue

    def trigger_search(self, query, s, e): 
        self.start_thread(f"https://api.themoviedb.org/3/search/multi?query={query}", s, e)

    def start_thread(self, url, s, e):
        self.task_counter += 1; self.signals.clear_signal.emit()
        threading.Thread(target=self.fetch_worker, args=(url, self.task_counter, s, e), daemon=True).start()

    def fetch_worker(self, url, t_id, s, e):
        try:
            h = {"Authorization": f"Bearer {STARK_TOKEN}"}
            res = requests.get(url, headers=h).json().get('results', [])
            for i, item in enumerate(res[:20]):
                if t_id == self.task_counter:
                    mtype = item.get('media_type', 'movie')
                    self.executor.submit(self.img_worker, item, i+1, t_id, s, e, mtype)
        except: pass

    def img_worker(self, item, rank, tid, s, e, mtype):
        try:
            path = item.get('poster_path')
            if not path: return
            raw = requests.get(f"https://image.tmdb.org/t/p/w300{path}").content
            pix = QPixmap(); pix.loadFromData(raw)
            self.signals.item_signal.emit(item, pix.scaled(150, 225), rank, mtype, tid, s, e)
        except: pass

    def add_item_to_ui(self, item, pix, rank, mtype, tid, s, e):
        if tid == self.task_counter: 
            card = MovieCard(item, pix, mtype, self, s, e); self.grid.addWidget(card, (rank-1)//5, (rank-1)%5)
            QApplication.processEvents()

    def clear_gallery(self):
        while self.grid.count():
            child = self.grid.takeAt(0);
            if child.widget(): child.widget().deleteLater()
        QApplication.processEvents()

    def run_fresh_trending(self): self.start_thread(f"https://api.themoviedb.org/3/trending/all/day", 1, 1)

    def toggle_live_mode(self):
        self.is_live_mode = not self.is_live_mode
        if self.is_live_mode: threading.Thread(target=self.live_voice_loop, daemon=True).start()

class MovieCard(QFrame):
    def __init__(self, item, pix, mtype, app, s, e):
        super().__init__(); self.setFixedSize(175, 330); self.setObjectName("MovieCard")
        self.setStyleSheet("QFrame#MovieCard { border: 2px solid #FF0000; background: #000; } QFrame#MovieCard:hover { border: 2px solid #00FF00; }")
        layout = QVBoxLayout(self); lbl = QLabel(); lbl.setPixmap(pix); layout.addWidget(lbl)
        t = (item.get('name') or item.get('title'))[:15]; layout.addWidget(QLabel(t))
        btn = QPushButton("WATCH"); 
        url = f"https://vidsrc.me/embed/{mtype}?tmdb={item['id']}"
        btn.clicked.connect(lambda: webbrowser.open(url)); layout.addWidget(btn)

if __name__ == "__main__":
    app = QApplication(sys.argv); win = StarkCinemaSingularity(); win.show(); sys.exit(app.exec_())
