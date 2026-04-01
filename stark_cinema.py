import sys, os, requests, threading, time, json, webbrowser
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# --- JARVIS VOICE CHECK (FAIL-SAFE) ---
VOICE_READY = False
try:
    import speech_recognition as sr
    import pyaudio
    VOICE_READY = True
except ImportError:
    sr = None

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QScrollArea, 
                             QLabel, QGridLayout, QFrame, QRadioButton, QTextEdit, 
                             QSystemTrayIcon, QMenu, QAction, QStyle, QActionGroup)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QPixmap, QIcon, QFont

class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int)
    log_signal = pyqtSignal(str); clear_signal = pyqtSignal()

STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"
LOGO_PATH = "logo.png"

STYLESHEET = """
QMainWindow { background-color: #1a0033; }
QFrame#Sidebar { background-color: #0f001a; border-right: 2px solid #ff0000; }
QLabel { color: #ff0000; font-family: 'Segoe UI'; font-weight: bold; }
QScrollArea { background-color: #1a0033; border: none; }
QWidget#Gallery { background-color: #2e004b; padding-right: 10px; }

QFrame#MovieCard { 
    background-color: #1a0000; 
    border-radius: 10px; 
    border: 2px solid #ff0000; 
    padding: 5px; 
}
QFrame#MovieCard:hover { border: 2px solid #00ff00; background-color: #001a00; }

QLineEdit { background-color: #111; border: 2px solid #ff0000; border-radius: 8px; color: #00ff00; padding: 12px; font-family: 'Consolas'; }
QPushButton { background-color: #111; color: #ff3333; border: 1px solid #aa0000; border-radius: 8px; padding: 8px; font-weight: bold; }
QPushButton:hover { border: 1px solid #00ff00; color: #00ff00; }
QPushButton#VoiceBtn { background-color: #330033; color: #ff00ff; border: 1px solid #ff00ff; }
QTextEdit#Console { background-color: #000; color: #00ff00; border: 1px solid #ff0000; font-family: 'Consolas'; font-size: 11px; }
* { outline: none; }
"""

class MovieCard(QFrame):
    def __init__(self, item, pix, mtype, parent_app):
        super().__init__()
        self.setObjectName("MovieCard"); self.setFixedSize(170, 300)
        self.item = item; self.parent_app = parent_app; self.mtype = mtype
        layout = QVBoxLayout(self)
        
        self.poster = QLabel(); self.poster.setPixmap(pix); layout.addWidget(self.poster, alignment=Qt.AlignCenter)
        title_str = (item.get('title') or item.get('name'))[:18]
        self.title = QLabel(title_str); self.title.setStyleSheet("color: white; font-size: 10px;"); layout.addWidget(self.title, alignment=Qt.AlignCenter)
        
        self.btn = QPushButton("WATCH"); self.btn.clicked.connect(lambda: parent_app.launch_movie(item['id'], mtype))
        layout.addWidget(self.btn)

    def enterEvent(self, event):
        # Intel Protocol: Show metadata on hover
        rating = self.item.get('vote_average', 'N/A')
        date = self.item.get('release_date') or self.item.get('first_air_date') or 'Unknown'
        overview = self.item.get('overview', 'No data available.')[:150] + "..."
        msg = f"🔍 INTEL: {self.title.text()}\n⭐ Rating: {rating} | 📅 {date}\n📝 {overview}"
        self.parent_app.signals.log_signal.emit(msg)

class MoviePlusPro(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stark Cinema - Vision V12.0")
        self.resize(1500, 920); self.setStyleSheet(STYLESHEET)
        
        self.current_source = "Alpha"
        self.sources = {"Alpha": "vidsrc.me", "Bravo": "vidsrc.to", "Gamma": "vidsrc.cc", "Delta": "embed.su"}
        
        self.shown_ids = set(); self.task_counter = 0; self.current_mode = "movie"
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.signals = SignalHandler()
        self.signals.item_signal.connect(self.add_item_to_ui)
        self.signals.log_signal.connect(lambda m: self.console.append(f"[{datetime.now().strftime('%H:%M:%S')}] {m}"))
        self.signals.clear_signal.connect(self.clear_gallery)
        
        self.setup_tray(); self.init_ui()
        self.signals.log_signal.emit("⚡ Vision Intelligence Systems: ONLINE")

    def init_ui(self):
        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central); layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(280); side_layout = QVBoxLayout(self.sidebar)
        
        side_layout.addWidget(QLabel(" COMMAND CENTER "))
        btn_trend = QPushButton("🔥 TRENDING"); btn_trend.clicked.connect(self.run_trending); side_layout.addWidget(btn_trend)
        
        self.v_btn = QPushButton("🎙️ VOICE COMMAND"); self.v_btn.setObjectName("VoiceBtn")
        self.v_btn.clicked.connect(self.start_voice_thread); side_layout.addWidget(self.v_btn)
        
        self.console = QTextEdit(); self.console.setObjectName("Console"); self.console.setReadOnly(True); self.console.setFixedHeight(300); side_layout.addStretch(); side_layout.addWidget(self.console); layout.addWidget(self.sidebar)
        
        content = QWidget(); c_layout = QVBoxLayout(content)
        self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("Type 'play [movie]' or search here..."); self.search_bar.returnPressed.connect(self.process_command); c_layout.addWidget(self.search_bar)
        
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.container = QWidget(); self.container.setObjectName("Gallery"); self.grid = QGridLayout(self.container); self.grid.setSpacing(10); self.scroll.setWidget(self.container); c_layout.addWidget(self.scroll); layout.addWidget(content); self.run_trending()

    def process_command(self):
        cmd = self.search_bar.text().lower().strip()
        if cmd.startswith("play "):
            movie = cmd.replace("play ", "")
            self.signals.log_signal.emit(f"🚀 Auto-Pilot: Hunting for '{movie}'...")
            self.auto_pilot = True; self.run_search(movie)
        else:
            self.run_search(cmd)

    def launch_movie(self, mid, mtype):
        self.signals.log_signal.emit(f"🎬 Launching {mtype} ID: {mid} via {self.current_source}...")
        url = f"https://vidsrc.me/embed/{mtype}?tmdb={mid}"
        webbrowser.open(url)

    def add_item_to_ui(self, item, pix, rank, mtype, tid):
        if tid != self.task_counter: return
        card = MovieCard(item, pix, mtype, self)
        self.grid.addWidget(card, (rank-1)//5, (rank-1)%5, alignment=Qt.AlignCenter)
        
        if hasattr(self, 'auto_pilot') and self.auto_pilot and rank == 1:
            self.auto_pilot = False
            self.launch_movie(item['id'], mtype)

    def start_voice_thread(self):
        if not VOICE_READY:
            self.signals.log_signal.emit("❌ Hardware Error: PyAudio missing. Use Command Line instead.")
            return
        threading.Thread(target=self.voice_worker, daemon=True).start()

    def voice_worker(self):
        r = sr.Recognizer()
        with sr.Microphone() as source:
            self.signals.log_signal.emit("🎙️ Listening...")
            try:
                audio = r.listen(source, timeout=5)
                query = r.recognize_google(audio)
                self.signals.log_signal.emit(f"🗣️ Found: '{query}'")
                self.search_bar.setText(f"play {query}"); self.process_command()
            except Exception as e:
                self.signals.log_signal.emit(f"⚠️ Voice Error: {str(e)}")

    def run_trending(self): self.start_thread(f"https://api.themoviedb.org/3/trending/{self.current_mode}/week")
    def run_search(self, q=None):
        query = q or self.search_bar.text().strip()
        if query: self.start_thread(f"https://api.themoviedb.org/3/search/multi?query={query}")

    def start_thread(self, url):
        self.task_counter += 1; self.signals.clear_signal.emit()
        threading.Thread(target=self.fetch_worker, args=(url, self.task_counter), daemon=True).start()

    def fetch_worker(self, url, t_id):
        try:
            h = {"Authorization": f"Bearer {STARK_TOKEN}"}
            res = requests.get(url, headers=h).json().get('results', [])
            for i, item in enumerate(res[:60]):
                if t_id != self.task_counter: return
                self.executor.submit(self.img_worker, item, i+1, self.current_mode, t_id)
                time.sleep(0.25)
        except: pass

    def img_worker(self, item, rank, mtype, tid):
        try:
            url = f"https://image.tmdb.org/t/p/w300{item['poster_path']}"
            pix = QPixmap(); pix.loadFromData(requests.get(url).content)
            self.signals.item_signal.emit(item, pix.scaled(155, 230, Qt.KeepAspectRatio), rank, mtype, tid)
        except: pass

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self); self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        menu = QMenu(); menu.addAction("👁️ SHOW").triggered.connect(lambda: self.show_normal())
        menu.addAction("❌ EXIT").triggered.connect(sys.exit)
        self.tray_icon.setContextMenu(menu); self.tray_icon.show()

    def show_normal(self): self.show(); self.raise_(); self.activateWindow()
    def clear_gallery(self): 
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w: w.deleteLater()

if __name__ == "__main__":
    app = QApplication(sys.argv); app.setQuitOnLastWindowClosed(False)
    win = MoviePlusPro(); win.show(); sys.exit(app.exec_())
