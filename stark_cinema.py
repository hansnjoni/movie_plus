import sys, os, requests, threading, time, json, webbrowser, traceback
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QScrollArea, 
                             QLabel, QGridLayout, QFrame, QRadioButton, QTextEdit, QDialog, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QImage
from concurrent.futures import ThreadPoolExecutor

# --- MASTER SPECS ---
STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"
SETTINGS_FILE = "settings.json"
JASON_FILE = "status_cache.json"
FAVS_FILE = "favorites.json"
HISTORY_FILE = "history.json"
LOGO_PATH = "logo.png"

STYLESHEET = """
QMainWindow { background-color: #02040a; }
QFrame#Sidebar { background-color: #080808; border-right: 1px solid #222; }
QLabel { color: #ff0000; font-family: 'Segoe UI'; font-weight: bold; }
QLineEdit { background-color: #111; border: 1px solid #ff0000; border-radius: 5px; color: white; padding: 12px; }
QLineEdit:hover { border: 1px solid #00ff00; }
QWidget#GalleryContainer { background-color: #02040a; }
QScrollArea { border: none; background-color: #02040a; }
QFrame#MovieCard { background-color: #1a0033; border-radius: 12px; border: 1px solid #330066; margin: 5px; padding: 10px; }
QFrame#MovieCard:hover { border: 1px solid #00ff00; }
QPushButton { background-color: #0f0f0f; color: #ff3333; border: 2px solid #aa0000; border-radius: 10px; padding: 8px; font-weight: bold; }
QPushButton:hover { background-color: #111; color: #ffffff; border: 2px solid #00ff00; }
QPushButton#WatchBtn { background-color: #004400; color: #00ff00; border: 2px solid #00ff00; }
QComboBox { background: #111; color: white; border: 1px solid #ff0000; padding: 5px; }
QTextEdit#Console { background-color: #050505; color: #00ff00; border: 1px solid #330066; font-family: 'Consolas'; font-size: 11px; }
"""

def save_jason(m_id, status):
    try:
        mem = json.load(open(JASON_FILE)) if os.path.exists(JASON_FILE) else {}
        mem[str(m_id)] = {"status": status, "date": str(datetime.now().date())}
        if len(mem) > 2000:
            keys = sorted(mem, key=lambda k: mem[k].get('date', ''))
            for i in range(500): del mem[keys[i]]
        json.dump(mem, open(JASON_FILE, 'w'))
    except: pass

class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Stark Systems - Settings")
        self.setStyleSheet(STYLESHEET)
        self.setFixedSize(450, 350)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("API READ ACCESS TOKEN:"))
        self.token_in = QTextEdit(); self.token_in.setPlainText(settings.get("token", STARK_TOKEN))
        layout.addWidget(self.token_in)
        layout.addWidget(QLabel("QUARANTINE DAYS (90 RECOMMENDED):"))
        self.q_in = QLineEdit(str(settings.get("quarantine", 90)))
        layout.addWidget(self.q_in)
        btn = QPushButton("💾 SAVE & REBOOT"); btn.clicked.connect(self.accept)
        layout.addWidget(btn)

class EpisodeSelector(QDialog):
    def __init__(self, show_id, show_name, total_seasons, history, parent=None):
        super().__init__(parent)
        self.show_id = str(show_id)
        self.history = history
        self.setWindowTitle(f"Stark TV: {show_name}")
        self.setStyleSheet(STYLESHEET)
        self.setFixedSize(400, 350)
        layout = QVBoxLayout(self)
        self.s_box = QComboBox()
        for i in range(1, total_seasons + 1): self.s_box.addItem(f"Season {i}", i)
        layout.addWidget(QLabel("SELECT SEASON")); layout.addWidget(self.s_box)
        self.e_box = QComboBox(); layout.addWidget(QLabel("SELECT EPISODE")); layout.addWidget(self.e_box)
        self.s_box.currentIndexChanged.connect(self.load_episodes); self.load_episodes()
        btn = QPushButton("🚀 LAUNCH STREAM"); btn.clicked.connect(self.accept); layout.addWidget(btn)

    def load_episodes(self):
        self.e_box.clear()
        s = self.s_box.currentData()
        url = f"https://api.themoviedb.org/3/tv/{self.show_id}/season/{s}?api_key=eb8e6998a40eabf4bfc8844b5abf6348"
        try:
            res = requests.get(url).json().get('episodes', [])
            watched = self.history.get(self.show_id, [])
            for ep in res:
                num = ep['episode_number']
                marker = " ✅" if f"S{s}E{num}" in watched else ""
                self.e_box.addItem(f"Ep {num}: {ep['name']}{marker}", num)
        except: self.e_box.addItem("Episode 1", 1)

class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int)
    log_signal = pyqtSignal(str)
    clear_signal = pyqtSignal()

class MoviePlusPro(QMainWindow):
    def __init__(self):
        super().__init__()
        self.task_counter = 0
        self.current_mode = "movie"
        self.settings = json.load(open(SETTINGS_FILE)) if os.path.exists(SETTINGS_FILE) else {"token": STARK_TOKEN, "quarantine": 90}
        self.history = json.load(open(HISTORY_FILE)) if os.path.exists(HISTORY_FILE) else {}
        self.signals = SignalHandler()
        self.signals.item_signal.connect(self.add_item_to_ui)
        self.signals.log_signal.connect(self.update_log); self.signals.clear_signal.connect(self.clear_gallery)
        self.executor = ThreadPoolExecutor(max_workers=15)
        
        self.resize(1400, 950); self.setStyleSheet(STYLESHEET)
        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central)
        
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(260)
        side_layout = QVBoxLayout(self.sidebar)
        
        self.logo = QLabel()
        if os.path.exists(LOGO_PATH): self.logo.setPixmap(QPixmap(LOGO_PATH).scaled(220, 120, Qt.KeepAspectRatio))
        else: self.logo.setText("STARK CINEMA"); self.logo.setStyleSheet("font-size: 24px; color: #ff0000; padding: 10px;")
        side_layout.addWidget(self.logo, alignment=Qt.AlignCenter)
        
        btn_set = QPushButton("⚙️ SETTINGS"); btn_set.clicked.connect(self.open_settings); side_layout.addWidget(btn_set)
        btn_fav = QPushButton("⭐ FAVORITES"); btn_fav.clicked.connect(self.run_favorites); side_layout.addWidget(btn_fav)
        btn_tr = QPushButton("🔥 TRENDING"); btn_tr.clicked.connect(self.run_trending); side_layout.addWidget(btn_tr)
        
        self.m_radio = QRadioButton("Movies"); self.m_radio.setChecked(True); self.m_radio.clicked.connect(lambda: self.set_mode("movie"))
        self.t_radio = QRadioButton("TV Shows"); self.t_radio.clicked.connect(lambda: self.set_mode("tv"))
        side_layout.addWidget(self.m_radio); side_layout.addWidget(self.t_radio)
        
        side_layout.addWidget(QLabel("\n   GENRES"))
        for n, i in [("ACTION", 28), ("COMEDY", 35), ("HORROR", 27), ("CRIME", 80), ("TRUE CRIME", "80,99")]:
            btn = QPushButton(n); btn.clicked.connect(lambda checked, idx=i: self.run_genre(idx)); side_layout.addWidget(btn)
            
        side_layout.addStretch()
        self.console = QTextEdit(); self.console.setObjectName("Console"); self.console.setReadOnly(True); side_layout.addWidget(self.console)
        layout.addWidget(self.sidebar)
        
        content = QWidget(); c_layout = QVBoxLayout(content)
        self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("Search..."); self.search_bar.returnPressed.connect(self.run_search)
        c_layout.addWidget(self.search_bar)
        
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.container = QWidget(); self.container.setObjectName("GalleryContainer"); self.grid = QGridLayout(self.container)
        self.scroll.setWidget(self.container); c_layout.addWidget(self.scroll)
        layout.addWidget(content)
        self.run_trending()

    def open_settings(self):
        d = SettingsDialog(self.settings, self)
        if d.exec_():
            self.settings = {"token": d.token_in.toPlainText().strip(), "quarantine": int(d.q_in.text())}
            json.dump(self.settings, open(SETTINGS_FILE, 'w')); self.run_trending()

    def update_log(self, msg): self.console.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
    def set_mode(self, m): self.current_mode = m; self.run_trending()
    def clear_gallery(self): 
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w: w.deleteLater()

    def run_trending(self): self.start_thread(f"https://api.themoviedb.org/3/trending/{self.current_mode}/week")
    def run_search(self): self.start_thread(f"https://api.themoviedb.org/3/search/{self.current_mode}?query={self.search_bar.text()}")
    def run_genre(self, g_id): self.start_thread(f"https://api.themoviedb.org/3/discover/{self.current_mode}?with_genres={g_id}&sort_by=popularity.desc")
    
    def run_favorites(self):
        self.signals.clear_signal.emit()
        if os.path.exists(FAVS_FILE):
            for i, item in enumerate(json.load(open(FAVS_FILE)), 1):
                self.executor.submit(self.img_worker, item, i, item.get('m_type', 'movie'), self.task_counter)

    def start_thread(self, url):
        self.task_counter += 1; self.signals.clear_signal.emit()
        threading.Thread(target=self.fetch_worker, args=(url, self.task_counter), daemon=True).start()

    def fetch_worker(self, url, t_id):
        try:
            res = requests.get(url, headers={"Authorization": f"Bearer {self.settings['token']}"}).json().get('results', [])
            mem = json.load(open(JASON_FILE)) if os.path.exists(JASON_FILE) else {}
            count = 1
            for item in res:
                if t_id != self.task_counter: return
                m_id = str(item['id'])
                if m_id in mem and mem[m_id]['status'] == "Available":
                    self.executor.submit(self.img_worker, item, count, self.current_mode, t_id)
                    count += 1
                else:
                    threading.Thread(target=self.recon, args=(item, count, t_id), daemon=True).start()
                    count += 1
                time.sleep(0.05)
        except: pass

    def recon(self, item, rank, t_id):
        url = f"https://vidsrc.me/embed/{'movie' if self.current_mode=='movie' else 'tv'}?tmdb={item['id']}"
        try:
            if requests.head(url, timeout=5).status_code == 200:
                save_jason(item['id'], "Available")
                self.executor.submit(self.img_worker, item, rank, self.current_mode, t_id)
        except: pass

    def img_worker(self, item, rank, m_type, t_id):
        if t_id != self.task_counter: return
        pix = QPixmap()
        if item.get('poster_path'):
            try:
                data = requests.get(f"https://image.tmdb.org/t/p/w200{item['poster_path']}").content
                pix.loadFromData(data)
            except: pass
        self.signals.item_signal.emit(item, pix.scaled(150, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation), rank, m_type, t_id)

    def add_item_to_ui(self, item, pix, rank, m_type, t_id):
        if t_id != self.task_counter: return
        f = QFrame(); f.setObjectName("MovieCard"); l = QVBoxLayout(f)
        p = QLabel(); p.setPixmap(pix); l.addWidget(p, alignment=Qt.AlignCenter)
        row = QHBoxLayout()
        wb = QPushButton("WATCH"); wb.setObjectName("WatchBtn"); wb.clicked.connect(lambda: self.handle_launch(item, m_type))
        fb = QPushButton("⭐"); fb.setFixedWidth(40); fb.clicked.connect(lambda: self.save_fav(item, m_type))
        row.addWidget(wb); row.addWidget(fb); l.addLayout(row)
        self.grid.addWidget(f, (rank-1)//5, (rank-1)%5)

    def handle_launch(self, item, m_type):
        if m_type == "movie": webbrowser.open(f"https://vidsrc.me/embed/movie?tmdb={item['id']}")
        else:
            det = requests.get(f"https://api.themoviedb.org/3/tv/{item['id']}?api_key=eb8e6998a40eabf4bfc8844b5abf6348").json()
            sel = EpisodeSelector(item['id'], item.get('name'), det.get('number_of_seasons', 1), self.history, self)
            if sel.exec_():
                s, e = sel.s_box.currentData(), sel.e_box.currentData(); sid = str(item['id'])
                if sid not in self.history: self.history[sid] = []
                if f"S{s}E{e}" not in self.history[sid]: self.history[sid].append(f"S{s}E{e}")
                json.dump(self.history, open(HISTORY_FILE, 'w'))
                webbrowser.open(f"https://vidsrc.me/embed/tv?tmdb={item['id']}&season={s}&episode={e}")

    def save_fav(self, item, m_type):
        favs = json.load(open(FAVS_FILE)) if os.path.exists(FAVS_FILE) else []
        if item['id'] not in [f['id'] for f in favs]:
            item['m_type'] = m_type; favs.append(item); json.dump(favs, open(FAVS_FILE, 'w'))
            self.update_log(f"⭐ Saved: {item.get('title') or item.get('name')}")

if __name__ == "__main__":
    app = QApplication(sys.argv); win = MoviePlusPro(); win.show(); sys.exit(app.exec_())
