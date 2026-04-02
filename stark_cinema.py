import sys, os, requests, threading, time, json, webbrowser, subprocess, random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# --- JARVIS IDENTITY ---
USER_DATA_FILE = "user_profile.json"
def load_user():
    default = {"name": "Hans", "partner": "the little woman"}
    if not os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'w') as f: json.dump(default, f)
        return default
    with open(USER_DATA_FILE, 'r') as f: return json.load(f)

USER = load_user()

# --- STABLE INITIALIZATION ---
STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"

try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                                 QLineEdit, QPushButton, QScrollArea, QLabel, QGridLayout, 
                                 QFrame, QTextEdit, QComboBox)
    from PyQt5.QtCore import Qt, pyqtSignal, QObject
    from PyQt5.QtGui import QPixmap, QIcon
except:
    print("Missing PyQt5. Run: pip install PyQt5")

class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int)
    log_signal = pyqtSignal(str); clear_signal = pyqtSignal(); search_trigger = pyqtSignal(str)

class StarkCinemaSingularity(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Stark Cinema - JARVIS Singularity")
        self.resize(1500, 950); self.current_mode = "movie"; self.is_live_mode = False
        self.speak_lock = threading.Lock(); self.task_counter = 0
        self.executor = ThreadPoolExecutor(max_workers=10); self.signals = SignalHandler()
        
        self.signals.item_signal.connect(self.add_item_to_ui)
        self.signals.log_signal.connect(lambda m: self.console.append(f"[{datetime.now().strftime('%H:%M')}] {m}"))
        self.signals.clear_signal.connect(self.clear_gallery)
        self.signals.search_trigger.connect(self.trigger_search)
        
        self.init_ui(); self.run_fresh_trending()
        self.speak(f"Systems Online. JARVIS is at your service, {USER['name']}.")

    def speak(self, text):
        def run_speech():
            with self.speak_lock:
                cmd = f'PowerShell -Command "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{text.replace("'", "")}\');"'
                subprocess.run(cmd, shell=True)
        threading.Thread(target=run_speech, daemon=True).start()

    def init_ui(self):
        # FORCED STEALTH COLORS
        self.setStyleSheet("""
            QMainWindow { background-color: #050505; }
            QFrame#Sidebar { background-color: #000000; border-right: 2px solid #ff0000; }
            QLabel { color: #ff0000; font-family: 'Segoe UI'; font-weight: bold; font-size: 14px; }
            QPushButton { background-color: #111; color: #ff0000; border: 1px solid #ff0000; border-radius: 5px; padding: 12px; font-weight: bold; }
            QPushButton:hover { border: 2px solid #00ff00; color: #00ff00; background-color: #001100; }
            QLineEdit { background-color: #000; border: 2px solid #ff0000; color: #00ff00; padding: 12px; font-size: 16px; }
            QTextEdit#Console { background-color: #000; color: #00ff00; border: 1px solid #333; font-family: 'Consolas'; }
            QComboBox { background-color: #111; color: #00ff00; border: 1px solid #ff0000; padding: 5px; }
        """)

        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central); layout.setContentsMargins(0,0,0,0)
        
        # SIDEBAR
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(280)
        side_layout = QVBoxLayout(self.sidebar)
        
        if os.path.exists("logo.png"):
            l = QLabel(); l.setPixmap(QPixmap("logo.png").scaled(240, 120, Qt.KeepAspectRatio)); side_layout.addWidget(l, alignment=Qt.AlignCenter)

        side_layout.addWidget(QLabel(" COMMANDS "))
        self.live_btn = QPushButton("🎙️ ACTIVATE JARVIS")
        self.live_btn.setStyleSheet("color: #00ff00; border-color: #00ff00;")
        self.live_btn.clicked.connect(self.toggle_live_mode); side_layout.addWidget(self.live_btn)

        side_layout.addWidget(QLabel("\n MODE "))
        self.mode_box = QComboBox(); self.mode_box.addItems(["Movies", "TV Shows"]); self.mode_box.currentTextChanged.connect(self.switch_mode); side_layout.addWidget(self.mode_box)

        side_layout.addWidget(QLabel("\n GENRES "))
        for name, gid in [("ACTION", 28), ("COMEDY", 35), ("HORROR", 27), ("TRUE CRIME", "80,99")]:
            b = QPushButton(name); b.clicked.connect(lambda ch, idx=gid: self.run_genre(idx)); side_layout.addWidget(b)

        side_layout.addStretch()
        self.console = QTextEdit(); self.console.setObjectName("Console"); self.console.setFixedHeight(220); side_layout.addWidget(self.console)
        layout.addWidget(self.sidebar)

        # MAIN CONTENT
        content = QWidget(); c_layout = QVBoxLayout(content)
        search_row = QHBoxLayout()
        self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("Direct Command Center..."); search_row.addWidget(self.search_bar)
        self.search_btn = QPushButton("GO"); self.search_btn.setFixedWidth(80); self.search_btn.clicked.connect(self.process_command); search_row.addWidget(self.search_btn)
        c_layout.addLayout(search_row)

        self.scroll = QScrollArea(); self.container = QWidget(); self.grid = QGridLayout(self.container)
        self.scroll.setWidget(self.container); self.scroll.setWidgetResizable(True); c_layout.addWidget(self.scroll)
        layout.addWidget(content)

    def toggle_live_mode(self):
        self.is_live_mode = not self.is_live_mode
        if self.is_live_mode:
            self.live_btn.setText("📡 LISTENING...")
            self.speak("Voice link established.")
            threading.Thread(target=self.live_voice_loop, daemon=True).start()
        else:
            self.live_btn.setText("🎙️ ACTIVATE JARVIS")
            self.speak("Standing down.")

    def live_voice_loop(self):
        import speech_recognition as sr
        r = sr.Recognizer(); r.energy_threshold = 3500
        while self.is_live_mode:
            try:
                with sr.Microphone() as src:
                    audio = r.listen(src, timeout=5, phrase_time_limit=8)
                    q = r.recognize_google(audio).lower()
                    self.signals.log_signal.emit(f"YOU: {q}")
                    
                    if "stop" in q: self.is_live_mode = False; break
                    if "who is in" in q:
                        self.fetch_cast(q.replace("who is in", "").strip()); continue
                    
                    if any(x in q for x in ["play", "find", "search"]):
                        target = q.replace("play", "").replace("find", "").replace("search", "").strip()
                        self.signals.search_trigger.emit(target); break
            except: continue

    def fetch_cast(self, movie_name):
        h = {"Authorization": f"Bearer {STARK_TOKEN}"}
        search = requests.get(f"https://api.themoviedb.org/3/search/movie?query={movie_name}", headers=h).json()
        if search['results']:
            m_id = search['results'][0]['id']
            credits = requests.get(f"https://api.themoviedb.org/3/movie/{m_id}/credits", headers=h).json()
            cast = [member['name'] for member in credits['cast'][:5]]
            self.speak(f"The cast includes {', '.join(cast)}.")

    def initiate_watch_protocol(self, item, mtype):
        url = f"https://vidsrc.me/embed/{mtype}?tmdb={item['id']}"; webbrowser.open(url)

    def switch_mode(self, text):
        self.current_mode = "movie" if text == "Movies" else "tv"; self.run_fresh_trending()

    def trigger_search(self, query): self.search_bar.setText(query); self.process_command()

    def process_command(self):
        cmd = self.search_bar.text().strip()
        if cmd: self.start_thread(f"https://api.themoviedb.org/3/search/{self.current_mode}?query={cmd}")

    def run_genre(self, g_id): self.start_thread(f"https://api.themoviedb.org/3/discover/{self.current_mode}?with_genres={g_id}&sort_by=popularity.desc")

    def run_fresh_trending(self): self.start_thread(f"https://api.themoviedb.org/3/trending/{self.current_mode}/day")

    def start_thread(self, url):
        self.task_counter += 1; self.signals.clear_signal.emit()
        threading.Thread(target=self.fetch_worker, args=(url, self.task_counter), daemon=True).start()

    def fetch_worker(self, url, t_id):
        try:
            h = {"Authorization": f"Bearer {STARK_TOKEN}"}
            res = requests.get(url, headers=h).json().get('results', [])
            for i, item in enumerate(res[:25]):
                if t_id == self.task_counter: self.executor.submit(self.img_worker, item, i+1, self.current_mode, t_id); time.sleep(0.05)
        except: pass

    def img_worker(self, item, rank, mtype, tid):
        try:
            raw = requests.get(f"https://image.tmdb.org/t/p/w300{item.get('poster_path')}").content
            pix = QPixmap(); pix.loadFromData(raw)
            self.signals.item_signal.emit(item, pix.scaled(150, 225), rank, mtype, tid)
        except: pass

    def add_item_to_ui(self, item, pix, rank, mtype, tid):
        if tid == self.task_counter: 
            card = MovieCard(item, pix, mtype, self); self.grid.addWidget(card, (rank-1)//5, (rank-1)%5)

    def clear_gallery(self):
        while self.grid.count():
            child = self.grid.takeAt(0);
            if child.widget(): child.widget().deleteLater()

class MovieCard(QFrame):
    def __init__(self, item, pix, mtype, app):
        super().__init__(); self.setFixedSize(175, 330); self.setObjectName("MovieCard")
        self.setStyleSheet("QFrame#MovieCard { border: 2px solid #ff0000; background: #000; } QFrame#MovieCard:hover { border: 2px solid #00ff00; }")
        layout = QVBoxLayout(self); lbl = QLabel(); lbl.setPixmap(pix); layout.addWidget(lbl)
        t = (item.get('title') or item.get('name'))[:15]
        layout.addWidget(QLabel(t))
        btn = QPushButton("WATCH"); btn.clicked.connect(lambda: app.initiate_watch_protocol(item, mtype)); layout.addWidget(btn)

if __name__ == "__main__":
    app = QApplication(sys.argv); win = StarkCinemaSingularity(); win.show(); sys.exit(app.exec_())
