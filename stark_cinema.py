import sys, os, requests, threading, time, json, webbrowser
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QScrollArea, 
                             QLabel, QGridLayout, QFrame, QRadioButton, QTextEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap

# --- MASTER SPECS ---
STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"
JASON_FILE = "status_cache.json"
SETTINGS_FILE = "settings.json"
LOGO_PATH = "logo.png"

# STARK RED INTERFACE CSS
STYLESHEET = """
QMainWindow { background-color: #050000; }
QFrame#Sidebar { background-color: #0a0000; border-right: 2px solid #ff0000; }
QRadioButton { color: #ff3333; font-weight: bold; font-size: 14px; background: transparent; }
QRadioButton::indicator { width: 14px; height: 14px; border-radius: 8px; border: 2px solid #aa0000; background: #000; }
QRadioButton::indicator:checked { background-color: #00ff00; border: 2px solid #ffffff; }
QLabel { color: #ff0000; font-family: 'Segoe UI'; font-weight: bold; }
QLineEdit { background-color: #111; border: 1px solid #ff0000; border-radius: 5px; color: white; padding: 12px; }
QScrollArea { background-color: #050000; border: none; }
QWidget#Gallery { background-color: #050000; } 
QFrame#MovieCard { background-color: #150000; border-radius: 10px; border: 1px solid #440000; padding: 5px; }
QPushButton { background-color: #111; color: #ff3333; border: 1px solid #aa0000; border-radius: 8px; padding: 8px; font-weight: bold; }
QPushButton:hover { border: 1px solid #00ff00; color: #00ff00; }
QPushButton#WatchBtn { background-color: #004400; color: #00ff00; border: 1px solid #00ff00; }
QTextEdit#Console { background-color: #000; color: #00ff00; border: 1px solid #ff0000; font-family: 'Consolas'; }
"""

def get_jason():
    if os.path.exists(JASON_FILE):
        try:
            with open(JASON_FILE, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_to_jason(m_id, status):
    mem = get_jason()
    mem[str(m_id)] = {"status": status, "last_checked": str(datetime.now().date())}
    with open(JASON_FILE, 'w') as f: json.dump(mem, f)

class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int)
    log_signal = pyqtSignal(str)
    clear_signal = pyqtSignal()

class MoviePlusPro(QMainWindow):
    def __init__(self):
        super().__init__()
        self.task_counter = 0; self.current_mode = "movie"
        self.settings = json.load(open(SETTINGS_FILE)) if os.path.exists(SETTINGS_FILE) else {"token": STARK_TOKEN}
        self.signals = SignalHandler()
        self.signals.item_signal.connect(self.add_item_to_ui)
        self.signals.log_signal.connect(self.update_log)
        self.signals.clear_signal.connect(self.clear_gallery)
        self.executor = ThreadPoolExecutor(max_workers=20)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Stark Cinema v5.0"); self.resize(1400, 950); self.setStyleSheet(STYLESHEET)
        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central)
        
        # Sidebar
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(260)
        side_layout = QVBoxLayout(self.sidebar)
        self.logo = QLabel("STARK CINEMA")
        if os.path.exists(LOGO_PATH): self.logo.setPixmap(QPixmap(LOGO_PATH).scaled(220, 120, Qt.KeepAspectRatio))
        side_layout.addWidget(self.logo, alignment=Qt.AlignCenter)
        
        btn_trend = QPushButton("🔥 TRENDING"); btn_trend.clicked.connect(self.run_trending); side_layout.addWidget(btn_trend)
        
        radio_c = QWidget(); radio_l = QHBoxLayout(radio_c)
        self.m_radio = QRadioButton("Movies"); self.m_radio.setChecked(True); self.m_radio.clicked.connect(lambda: self.set_mode("movie"))
        self.t_radio = QRadioButton("TV"); self.t_radio.clicked.connect(lambda: self.set_mode("tv"))
        radio_l.addWidget(self.m_radio); radio_l.addWidget(self.t_radio)
        side_layout.addWidget(radio_c)
        
        side_layout.addStretch()
        self.console = QTextEdit(); self.console.setObjectName("Console"); self.console.setReadOnly(True); self.console.setFixedHeight(150)
        side_layout.addWidget(self.console); layout.addWidget(self.sidebar)
        
        # Content
        content = QWidget(); c_layout = QVBoxLayout(content)
        self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("Search Actor or Title..."); self.search_bar.returnPressed.connect(self.run_search)
        c_layout.addWidget(self.search_bar)
        
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.container = QWidget(); self.container.setObjectName("Gallery"); self.grid = QGridLayout(self.container)
        self.scroll.setWidget(self.container); c_layout.addWidget(self.scroll)
        layout.addWidget(content); self.run_trending()

    def update_log(self, msg): self.console.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
    def set_mode(self, m): self.current_mode = m; self.run_trending()
    def clear_gallery(self): 
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w: w.deleteLater()

    def run_trending(self): self.start_thread(f"https://api.themoviedb.org/3/trending/{self.current_mode}/week")
    def run_search(self):
        q = self.search_bar.text().strip()
        if q: self.start_thread(f"https://api.themoviedb.org/3/search/multi?query={q}")

    def start_thread(self, url):
        self.task_counter += 1; self.signals.clear_signal.emit()
        threading.Thread(target=self.fetch_worker, args=(url, self.task_counter), daemon=True).start()

    def fetch_worker(self, url, t_id):
        try:
            h = {"Authorization": f"Bearer {self.settings['token']}"}
            mem = get_jason(); count = 1; page = 1; is_search = "search" in url
            
            while count <= 60 and page <= 15:
                p_url = f"{url}&page={page}" if "?" in url else f"{url}?page={page}"
                raw = requests.get(p_url, headers=h).json().get('results', [])
                if not raw: break
                
                for item in raw:
                    if t_id != self.task_counter or count > 60: return
                    if not is_search and 16 in item.get('genre_ids', []): continue # No random cartoons
                    
                    m_id = str(item['id']); m_type = item.get('media_type', self.current_mode)
                    
                    if m_id in mem and mem[m_id]['status'] == "Available":
                        self.executor.submit(self.img_worker, item, count, m_type, t_id); count += 1
                    elif self.recon_failover(m_id, m_type):
                        self.executor.submit(self.img_worker, item, count, m_type, t_id); count += 1
                page += 1
        except: pass

    def recon_failover(self, m_id, m_type):
        url = f"https://vidsrc.me/embed/{m_type}?tmdb={m_id}"
        try:
            if requests.head(url, timeout=2).status_code == 200:
                save_to_jason(m_id, "Available"); return True
            save_to_jason(m_id, "Theaters"); return False
        except: return False

    def img_worker(self, item, rank, m_type, t_id):
        if t_id != self.task_counter: return
        try:
            data = requests.get(f"https://image.tmdb.org/t/p/w300{item['poster_path']}").content
            pix = QPixmap(); pix.loadFromData(data)
            self.signals.item_signal.emit(item, pix.scaled(180, 260, Qt.KeepAspectRatio), rank, m_type, t_id)
        except: pass

    def add_item_to_ui(self, item, pix, rank, m_type, t_id):
        if t_id != self.task_counter: return
        f = QFrame(); f.setObjectName("MovieCard"); l = QVBoxLayout(f)
        p = QLabel(); p.setPixmap(pix); l.addWidget(p, alignment=Qt.AlignCenter)
        btn = QPushButton("WATCH"); btn.setObjectName("WatchBtn")
        btn.clicked.connect(lambda: webbrowser.open(f"https://vidsrc.me/embed/{m_type}?tmdb={item['id']}"))
        l.addWidget(btn); self.grid.addWidget(f, (rank-1)//5, (rank-1)%5)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MoviePlusPro(); win.show()
    sys.exit(app.exec_())
