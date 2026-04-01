import sys, os, requests, threading, time, json, webbrowser
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor # <-- FIXED: The missing engine part
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QScrollArea, 
                             QLabel, QGridLayout, QFrame, QRadioButton, QTextEdit, QDialog, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap

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
QFrame#MovieCard { background-color: #1a0033; border-radius: 12px; border: 1px solid #330066; margin: 5px; padding: 10px; }
QFrame#MovieCard:hover { border: 1px solid #00ff00; }
QPushButton { background-color: #0f0f0f; color: #ff3333; border: 2px solid #aa0000; border-radius: 10px; padding: 8px; font-weight: bold; }
QPushButton:hover { background-color: #111; color: #ffffff; border: 2px solid #00ff00; }
QPushButton#WatchBtn { background-color: #004400; color: #00ff00; border: 2px solid #00ff00; }
QTextEdit#Console { background-color: #050505; color: #00ff00; border: 1px solid #330066; font-family: 'Consolas'; font-size: 11px; }
QComboBox { background: #111; color: white; border: 1px solid #ff0000; padding: 5px; }
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
    if len(mem) > 2000:
        keys = sorted(mem, key=lambda k: mem[k].get('last_checked', ''))
        for i in range(500): del mem[keys[i]]
    with open(JASON_FILE, 'w') as f: json.dump(mem, f)

class SettingsDialog(QDialog):
    def __init__(self, current_token, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Stark Settings")
        self.setFixedSize(450, 250); self.setStyleSheet(STYLESHEET)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("PASTE TMDB TOKEN / KEY:"))
        self.token_in = QTextEdit(); self.token_in.setPlainText(current_token)
        self.token_in.setStyleSheet("background:#111; color:white; border:1px solid #f00;")
        layout.addWidget(self.token_in)
        btn = QPushButton("💾 SAVE & REBOOT"); btn.clicked.connect(self.accept); layout.addWidget(btn)

class EpisodeSelector(QDialog):
    def __init__(self, show_id, show_name, total_seasons, history, parent=None):
        super().__init__(parent)
        self.show_id = str(show_id); self.history = history
        self.setWindowTitle(f"TV: {show_name}"); self.setStyleSheet(STYLESHEET); self.setFixedSize(400, 350)
        layout = QVBoxLayout(self)
        self.s_box = QComboBox()
        for i in range(1, total_seasons + 1): self.s_box.addItem(f"Season {i}", i)
        layout.addWidget(QLabel("SEASON")); layout.addWidget(self.s_box)
        self.e_box = QComboBox(); layout.addWidget(QLabel("EPISODE")); layout.addWidget(self.e_box)
        self.s_box.currentIndexChanged.connect(self.load_episodes); self.load_episodes()
        btn = QPushButton("🚀 LAUNCH"); btn.clicked.connect(self.accept); layout.addWidget(btn)

    def load_episodes(self):
        self.e_box.clear()
        s = self.s_box.currentData()
        url = f"https://api.themoviedb.org/3/tv/{self.show_id}/season/{s}?api_key=eb8e6998a40eabf4bfc8844b5abf6348"
        try:
            res = requests.get(url).json().get('episodes', [])
            watched = self.history.get(self.show_id, [])
            for ep in res:
                n = ep['episode_number']
                mark = " ✅" if f"S{s}E{n}" in watched else ""
                self.e_box.addItem(f"Ep {n}: {ep['name']}{mark}", n)
        except: self.e_box.addItem("Episode 1", 1)

class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int)
    log_signal = pyqtSignal(str); clear_signal = pyqtSignal()

class MoviePlusPro(QMainWindow):
    def __init__(self):
        super().__init__()
        self.task_counter = 0; self.current_mode = "movie"
        self.settings = json.load(open(SETTINGS_FILE)) if os.path.exists(SETTINGS_FILE) else {"token": STARK_TOKEN}
        self.history = json.load(open(HISTORY_FILE)) if os.path.exists(HISTORY_FILE) else {}
        self.signals = SignalHandler()
        self.signals.item_signal.connect(self.add_item_to_ui)
        self.signals.log_signal.connect(self.update_log); self.signals.clear_signal.connect(self.clear_gallery)
        self.executor = ThreadPoolExecutor(max_workers=15); self.init_ui()

    def init_ui(self):
        self.resize(1400, 950); self.setStyleSheet(STYLESHEET)
        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central)
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(260)
        side_layout = QVBoxLayout(self.sidebar)
        
        self.logo = QLabel("STARK CINEMA")
        if os.path.exists(LOGO_PATH): self.logo.setPixmap(QPixmap(LOGO_PATH).scaled(220, 120, Qt.KeepAspectRatio))
        side_layout.addWidget(self.logo, alignment=Qt.AlignCenter)
        
        for t, f in [("⚙️ SETTINGS", self.open_settings), ("🔥 TRENDING", self.run_trending), ("⭐ FAVORITES", self.run_favorites)]:
            b = QPushButton(t); b.clicked.connect(f); side_layout.addWidget(b)
        
        self.m_radio = QRadioButton("Movies"); self.m_radio.setChecked(True); self.m_radio.clicked.connect(lambda: self.set_mode("movie"))
        self.t_radio = QRadioButton("TV Shows"); self.t_radio.clicked.connect(lambda: self.set_mode("tv"))
        side_layout.addWidget(self.m_radio); side_layout.addWidget(self.t_radio)
        
        side_layout.addWidget(QLabel("\n   GENRES"))
        for n, i in [("ACTION", 28), ("COMEDY", 35), ("HORROR", 27), ("CRIME", 80), ("TRUE CRIME", "80,99")]:
            btn = QPushButton(n); btn.clicked.connect(lambda ch, idx=i: self.run_genre(idx)); side_layout.addWidget(btn)
            
        side_layout.addStretch()
        self.console = QTextEdit(); self.console.setObjectName("Console"); self.console.setReadOnly(True); side_layout.addWidget(self.console)
        layout.addWidget(self.sidebar)
        
        content = QWidget(); c_layout = QVBoxLayout(content)
        self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("Search Actor or Title..."); self.search_bar.returnPressed.connect(self.run_search)
        c_layout.addWidget(self.search_bar)
        
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.container = QWidget(); self.grid = QGridLayout(self.container)
        self.scroll.setWidget(self.container); c_layout.addWidget(self.scroll)
        layout.addWidget(content); self.run_trending()

    def open_settings(self):
        d = SettingsDialog(self.settings.get("token", STARK_TOKEN), self)
        if d.exec_():
            self.settings["token"] = d.token_in.toPlainText().strip()
            json.dump(self.settings, open(SETTINGS_FILE, 'w')); self.run_trending()

    def update_log(self, msg): self.console.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
    def set_mode(self, m): self.current_mode = m; self.run_trending()
    def clear_gallery(self): 
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w: w.deleteLater()

    def run_trending(self): self.start_thread(f"https://api.themoviedb.org/3/trending/{self.current_mode}/week")
    def run_genre(self, g_id): self.start_thread(f"https://api.themoviedb.org/3/discover/{self.current_mode}?with_genres={g_id}&sort_by=popularity.desc")
    
    def run_search(self):
        q = self.search_bar.text().strip()
        if q: self.start_thread(f"https://api.themoviedb.org/3/search/multi?query={q}")

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
            h = {"Authorization": f"Bearer {self.settings['token']}"}
            raw = requests.get(url, headers=h).json().get('results', [])
            items = []
            for r in raw:
                if r.get('media_type') == 'person':
                    p_url = f"https://api.themoviedb.org/3/person/{r['id']}/combined_credits"
                    items.extend(requests.get(p_url, headers=h).json().get('cast', []))
                else: items.append(r)
            
            mem = get_jason(); count = 1
            for item in sorted(items, key=lambda x: x.get('popularity', 0), reverse=True):
                if t_id != self.task_counter or count > 60: break
                if not item.get('poster_path'): continue
                m_id = str(item['id']); m_type = item.get('media_type', self.current_mode)
                self.executor.submit(self.img_worker, item, count, m_type, t_id)
                if m_id not in mem: threading.Thread(target=self.recon_failover, args=(m_id, m_type), daemon=True).start()
                count += 1; time.sleep(0.02)
        except: pass

    def recon_failover(self, m_id, m_type):
        u_a = f"https://vidsrc.me/embed/{m_type}?tmdb={m_id}"
        u_b = f"https://vidsrc.to/embed/{m_type}/{m_id}"
        try:
            if requests.head(u_a, timeout=3).status_code == 200 or requests.head(u_b, timeout=3).status_code == 200:
                save_to_jason(m_id, "Available")
            else: save_to_jason(m_id, "Theaters")
        except: pass

    def img_worker(self, item, rank, m_type, t_id):
        if t_id != self.task_counter: return
        pix = QPixmap()
        try:
            data = requests.get(f"https://image.tmdb.org/t/p/w200{item['poster_path']}").content
            pix.loadFromData(data)
        except: pass
        self.signals.item_signal.emit(item, pix.scaled(150, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation), rank, m_type, t_id)

    def add_item_to_ui(self, item, pix, rank, m_type, t_id):
        if t_id != self.task_counter: return
        f = QFrame(); f.setObjectName("MovieCard"); l = QVBoxLayout(f)
        p = QLabel(); p.setPixmap(pix); l.addWidget(p, alignment=Qt.AlignCenter)
        m_id = str(item['id']); mem = get_jason()
        r_dt_str = item.get('release_date') or item.get('first_air_date') or ""
        
        if m_id in mem and mem[m_id]['status'] == "Available":
            btn = QPushButton("WATCH"); btn.setObjectName("WatchBtn")
            btn.clicked.connect(lambda: self.handle_launch(item, m_type))
        else:
            try:
                r_dt = datetime.strptime(r_dt_str, '%Y-%m-%d'); d_dt = r_dt + timedelta(days=45)
                if datetime.now() > d_dt:
                    btn = QPushButton("WATCH"); btn.setObjectName("WatchBtn")
                    btn.clicked.connect(lambda: self.handle_launch(item, m_type))
                else:
                    btn = QPushButton(f"📅 {d_dt.strftime('%b %d')}"); btn.setEnabled(False); btn.setStyleSheet("color:#777; border:1px solid #444;")
            except:
                btn = QPushButton("WATCH"); btn.clicked.connect(lambda: self.handle_launch(item, m_type))

        row = QHBoxLayout(); row.addWidget(btn)
        fav = QPushButton("⭐"); fav.setFixedWidth(35); fav.clicked.connect(lambda: self.save_fav(item, m_type))
        row.addWidget(fav); l.addLayout(row)
        self.grid.addWidget(f, (rank-1)//5, (rank-1)%5)

    def handle_launch(self, item, m_type):
        m_id = str(item['id'])
        u_me = f"https://vidsrc.me/embed/{m_type}?tmdb={m_id}"
        u_to = f"https://vidsrc.to/embed/{m_type}/{m_id}"
        if m_type == "tv":
            det = requests.get(f"https://api.themoviedb.org/3/tv/{m_id}?api_key=eb8e6998a40eabf4bfc8844b5abf6348").json()
            sel = EpisodeSelector(m_id, item.get('name'), det.get('number_of_seasons', 1), self.history, self)
            if sel.exec_():
                s, e = sel.s_box.currentData(), sel.e_box.currentData()
                u_me = f"https://vidsrc.me/embed/tv?tmdb={m_id}&season={s}&episode={e}"
                u_to = f"https://vidsrc.to/embed/tv/{m_id}/{s}/{e}"
                if m_id not in self.history: self.history[m_id
