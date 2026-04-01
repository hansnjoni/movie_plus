import sys, os, requests, threading, time, json, webbrowser
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QScrollArea, 
                             QLabel, QGridLayout, QFrame, QRadioButton, QTextEdit, QDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QImage
from concurrent.futures import ThreadPoolExecutor

# --- STARK SYSTEM SETTINGS ---
STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"
JASON_FILE = "status_cache.json"
FAVS_FILE = "favorites.json"

STYLESHEET = """
QMainWindow { background-color: #02040a; }
QFrame#Sidebar { background-color: #080808; border-right: 1px solid #222; }
QLabel { color: #00ff00; font-family: 'Segoe UI'; font-weight: bold; }
QLineEdit { background-color: #111; border: 1px solid #00ff00; border-radius: 5px; color: white; padding: 12px; }
QFrame#MovieCard { background-color: #1a0033; border-radius: 12px; border: 1px solid #330066; padding: 10px; }
QFrame#MovieCard:hover { border: 1px solid #00ff00; }
QPushButton { background-color: #0f0f0f; color: #00ff00; border: 1px solid #004400; border-radius: 8px; padding: 8px; font-weight: bold; }
QPushButton:hover { background-color: #00ff00; color: black; }
QTextEdit#Console { background-color: #050505; color: #00ff00; font-family: 'Consolas'; font-size: 11px; }
"""

def get_jason():
    if os.path.exists(JASON_FILE):
        with open(JASON_FILE, 'r') as f: return json.load(f)
    return {}

def save_jason(m_id, status):
    mem = get_jason()
    mem[str(m_id)] = {"status": status, "date": str(datetime.now().date())}
    if len(mem) > 2000:
        keys = sorted(mem, key=lambda k: mem[k].get('date', ''))
        for i in range(500): del mem[keys[i]]
    with open(JASON_FILE, 'w') as f: json.dump(mem, f)

class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str)
    log_signal = pyqtSignal(str)
    clear_signal = pyqtSignal()

class MoviePlusPro(QMainWindow):
    def __init__(self):
        super().__init__()
        self.task_id = 0
        self.mode = "movie"
        self.signals = SignalHandler()
        self.signals.item_signal.connect(self.add_item)
        self.signals.log_signal.connect(self.update_log)
        self.signals.clear_signal.connect(self.clear_grid)
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        self.setWindowTitle("STARK CINEMA V1.0")
        self.resize(1300, 900)
        self.setStyleSheet(STYLESHEET)
        
        # UI Setup
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        
        sidebar = QFrame(); sidebar.setObjectName("Sidebar"); sidebar.setFixedWidth(250)
        side_layout = QVBoxLayout(sidebar)
        side_layout.addWidget(QLabel("STARK CINEMA"), alignment=Qt.AlignCenter)
        
        btn_tr = QPushButton("🔥 TRENDING"); btn_tr.clicked.connect(self.run_trending)
        side_layout.addWidget(btn_tr)
        
        btn_fav = QPushButton("⭐ FAVORITES"); btn_fav.clicked.connect(self.run_favorites)
        side_layout.addWidget(btn_fav)
        
        self.movie_btn = QRadioButton("Movies"); self.movie_btn.setChecked(True)
        self.movie_btn.toggled.connect(lambda: self.set_mode("movie"))
        self.tv_btn = QRadioButton("TV Shows"); self.tv_btn.toggled.connect(lambda: self.set_mode("tv"))
        side_layout.addWidget(self.movie_btn); side_layout.addWidget(self.tv_btn)
        
        side_layout.addStretch()
        self.console = QTextEdit(); self.console.setObjectName("Console"); self.console.setReadOnly(True)
        side_layout.addWidget(self.console)
        layout.addWidget(sidebar)
        
        content = QWidget(); content_layout = QVBoxLayout(content)
        self.search = QLineEdit(); self.search.setPlaceholderText("Search..."); self.search.returnPressed.connect(self.run_search)
        content_layout.addWidget(self.search)
        
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.grid_widget = QWidget(); self.grid = QGridLayout(self.grid_widget)
        self.scroll.setWidget(self.grid_widget)
        content_layout.addWidget(self.scroll)
        layout.addWidget(content)
        
        self.run_trending()

    def update_log(self, msg): self.console.append(msg)
    def set_mode(self, m): self.mode = m; self.run_trending()
    def clear_grid(self): 
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w: w.deleteLater()

    def run_trending(self): self.start_work(f"https://api.themoviedb.org/3/trending/{self.mode}/week")
    def run_search(self): self.start_work(f"https://api.themoviedb.org/3/search/{self.mode}?query={self.search.text()}")
    
    def run_favorites(self):
        self.signals.clear_signal.emit()
        if os.path.exists(FAVS_FILE):
            with open(FAVS_FILE, 'r') as f:
                for i, item in enumerate(json.load(f), 1):
                    self.executor.submit(self.load_item, item, i, self.task_id)

    def start_work(self, url):
        self.task_id += 1
        self.signals.clear_signal.emit()
        threading.Thread(target=self.fetch_worker, args=(url, self.task_id), daemon=True).start()

    def fetch_worker(self, url, t_id):
        headers = {"Authorization": f"Bearer {STARK_TOKEN}"}
        res = requests.get(url, headers=headers).json().get('results', [])
        mem = get_jason()
        count = 1
        for item in res:
            if self.task_id != t_id: return
            m_id = str(item['id'])
            if m_id in mem and mem[m_id]['status'] == "Available":
                self.executor.submit(self.load_item, item, count, t_id)
                count += 1
            else:
                threading.Thread(target=self.ping, args=(item, count, t_id, mem), daemon=True).start()
                count += 1
            time.sleep(0.05)

    def ping(self, item, rank, t_id, mem):
        url = f"https://vidsrc.me/embed/{'movie' if self.mode=='movie' else 'tv'}?tmdb={item['id']}"
        try:
            if requests.head(url, timeout=5).status_code == 200:
                save_jason(item['id'], "Available")
                self.executor.submit(self.load_item, item, rank, t_id)
        except: pass

    def load_item(self, item, rank, t_id):
        if self.task_id != t_id: return
        pix = QPixmap()
        if item.get('poster_path'):
            img_data = requests.get(f"https://image.tmdb.org/t/p/w200{item['poster_path']}").content
            pix.loadFromData(img_data)
        self.signals.item_signal.emit(item, pix.scaled(150, 220), rank, self.mode)

    def add_item(self, item, pix, rank, m_type):
        f = QFrame(); f.setObjectName("MovieCard"); l = QVBoxLayout(f)
        p = QLabel(); p.setPixmap(pix); l.addWidget(p)
        b = QPushButton("WATCH"); b.clicked.connect(lambda: webbrowser.open(f"https://vidsrc.me/embed/{m_type}?tmdb={item['id']}"))
        l.addWidget(b)
        self.grid.addWidget(f, (rank-1)//5, (rank-1)%5)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MoviePlusPro(); win.show()
    sys.exit(app.exec_())
