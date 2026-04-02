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

USER = load_vault("user_profile.json", {"name": "Hans", "birthday": "04-02"})
INTEL = load_vault("intelligence_vault.json", {"facts": []})
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
        self.setWindowTitle(f"Stark Cinema - Deep Link V76.0")
        self.resize(1500, 950); self.is_live_mode = False; self.task_counter = 0
        self.executor = ThreadPoolExecutor(max_workers=15); self.signals = SignalHandler()
        
        self.signals.item_signal.connect(self.add_item_to_ui); self.signals.log_signal.connect(lambda m: self.console.append(m))
        self.signals.clear_signal.connect(self.clear_gallery); self.signals.search_trigger.connect(self.trigger_search)
        
        self.init_ui(); self.run_fresh_trending()
        self.speak(f"Deep link protocols active. What are we watching, {USER['name']}?")

    def speak(self, text):
        def run_speech():
            clean_text = text.replace("'", "").replace('"', "")
            cmd = ["powershell", "-WindowStyle", "Hidden", "-Command", f"$s = New-Object -ComObject SAPI.SpVoice; $s.Speak('{clean_text}')"]
            subprocess.Popen(cmd)
        threading.Thread(target=run_speech, daemon=True).start()

    def init_ui(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #000000; }
            QFrame#Sidebar { background-color: #050505; border-right: 3px solid #FF0000; }
            QLabel { color: #FF0000; font-family: 'Segoe UI'; font-weight: bold; }
            QPushButton { background-color: #1a0000; color: #FF0000; border: 2px solid #FF0000; border-radius: 6px; padding: 12px; }
            QPushButton:hover { border: 2px solid #00FF00; color: #00FF00; background-color: #001100; }
            QLineEdit { background-color: #000; border: 2px solid #FF0000; color: #00FF00; padding: 12px; font-family: 'Consolas'; }
            QTextEdit#Console { background-color: #000; color: #00FF00; border: 1px solid #333; font-family: 'Consolas'; }
        """)
        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central); layout.setContentsMargins(0,0,0,0)
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(280); side_layout = QVBoxLayout(self.sidebar)
        self.live_btn = QPushButton("🎙️ ACTIVATE JARVIS"); self.live_btn.clicked.connect(self.toggle_live_mode); side_layout.addWidget(self.live_btn)
        side_layout.addStretch(); self.console = QTextEdit(); self.console.setObjectName("Console"); self.console.setFixedHeight(300); side_layout.addWidget(self.console)
        layout.addWidget(self.sidebar)
        content = QWidget(); c_layout = QVBoxLayout(content)
        self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("Specify Season/Episode for TV Shows..."); c_layout.addWidget(self.search_bar)
        self.scroll = QScrollArea(); self.container = QWidget(); self.grid = QGridLayout(self.container); self.scroll.setWidget(self.container); self.scroll.setWidgetResizable(True); c_layout.addWidget(self.scroll); layout.addWidget(content)

    def live_voice_loop(self):
        import speech_recognition as sr
        r = sr.Recognizer(); r.energy_threshold = 4000
        while self.is_live_mode:
            try:
                with sr.Microphone() as src:
                    r.adjust_for_ambient_noise(src, duration=0.8)
                    audio = r.listen(src, timeout=None, phrase_time_limit=12)
                    q = r.recognize_google(audio).lower()
                    self.signals.log_signal.emit(f"YOU: {q}")
                    
                    # --- DEEP LINK PARSING ---
                    season = 1; episode = 1; target = q
                    if "season" in q:
                        s_match = re.search(r'season (\d+)', q)
                        if s_match: season = int(s_match.group(1))
                        target = target.replace(f"season {season}", "")
                    if "episode" in q:
                        e_match = re.search(r'episode (\d+)', q)
                        if e_match: episode = int(e_match.group(1))
                        target = target.replace(f"episode {episode}", "")

                    if any(x in q for x in ["play", "watch", "find"]):
                        target = target.replace("play", "").replace("watch", "").replace("find", "").strip()
                        self.speak(f"On it, Hans. Locating {target} Season {season} Episode {episode}.")
                        self.signals.search_trigger.emit(target, season, episode)
                        break
            except: continue

    def trigger_search(self, query, s, e): 
        self.search_bar.setText(f"{query} (S{s}E{e})")
        # Search TV instead of Movie if S/E are present
        url = f"https://api.themoviedb.org/3/search/tv?query={query}"
        self.start_thread(url, s, e)

    def start_thread(self, url, s, e):
        self.task_counter += 1; self.signals.clear_signal.emit()
        threading.Thread(target=self.fetch_worker, args=(url, self.task_counter, s, e), daemon=True).start()

    def fetch_worker(self, url, t_id, s, e):
        try:
            h = {"Authorization": f"Bearer {STARK_TOKEN}"}
            res = requests.get(url, headers=h).json().get('results', [])
            for i, item in enumerate(res[:15]):
                if t_id == self.task_counter: self.executor.submit(self.img_worker, item, i+1, t_id, s, e)
        except: pass

    def img_worker(self, item, rank, tid, s, e):
        try:
            raw = requests.get(f"https://image.tmdb.org/t/p/w300{item.get('poster_path')}").content
            pix = QPixmap(); pix.loadFromData(raw)
            self.signals.item_signal.emit(item, pix.scaled(150, 225), rank, "tv", tid, s, e)
        except: pass

    def add_item_to_ui(self, item, pix, rank, mtype, tid, s, e):
        if tid == self.task_counter: 
            card = MovieCard(item, pix, mtype, self, s, e); self.grid.addWidget(card, (rank-1)//5, (rank-1)%5)

    def clear_gallery(self):
        while self.grid.count():
            child = self.grid.takeAt(0);
            if child.widget(): child.widget().deleteLater()

    def run_fresh_trending(self): self.start_thread(f"https://api.themoviedb.org/3/trending/tv/day", 1, 1)

    def toggle_live_mode(self):
        self.is_live_mode = not self.is_live_mode
        if self.is_live_mode: threading.Thread(target=self.live_voice_loop, daemon=True).start()

class MovieCard(QFrame):
    def __init__(self, item, pix, mtype, app, s, e):
        super().__init__(); self.setFixedSize(175, 330); self.setObjectName("MovieCard")
        self.setStyleSheet("QFrame#MovieCard { border: 2px solid #FF0000; background: #000; } QFrame#MovieCard:hover { border: 2px solid #00FF00; }")
        layout = QVBoxLayout(self); lbl = QLabel(); lbl.setPixmap(pix); layout.addWidget(lbl)
        t = (item.get('name') or item.get('title'))[:15]; layout.addWidget(QLabel(t))
        btn = QPushButton("WATCH NOW"); 
        # DEEP LINK URL GENERATION
        url = f"https://vidsrc.me/embed/tv?tmdb={item['id']}&season={s}&episode={e}"
        btn.clicked.connect(lambda: webbrowser.open(url)); layout.addWidget(btn)

if __name__ == "__main__":
    app = QApplication(sys.argv); win = StarkCinemaSingularity(); win.show(); sys.exit(app.exec_())
