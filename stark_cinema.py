STYLESHEET = """
QMainWindow { background-color: #050000; }
QFrame#Sidebar { background-color: #0a0000; border-right: 2px solid #ff0000; }

/* The Movie/TV Radio Button Text - Now STARK RED */
QRadioButton { 
    color: #ff3333; 
    font-weight: bold; 
    font-size: 14px; 
    background: transparent;
}

/* Custom Radio Button Circles */
QRadioButton::indicator { 
    width: 14px; height: 14px; 
    border-radius: 8px; 
    border: 2px solid #aa0000; 
    background: #000;
}
QRadioButton::indicator:checked { 
    background-color: #00ff00; 
    border: 2px solid #ffffff; 
}

QLabel { color: #ff0000; font-family: 'Segoe UI'; font-weight: bold; }
QLineEdit { background-color: #111; border: 1px solid #ff0000; border-radius: 5px; color: white; padding: 12px; }
QScrollArea { background-color: #050000; border: none; }
QWidget#Gallery { background-color: #050000; } 

QFrame#MovieCard { background-color: #150000; border-radius: 10px; border: 1px solid #440000; padding: 5px; }

QPushButton { 
    background-color: #111; 
    color: #ff3333; 
    border: 1px solid #aa0000; 
    border-radius: 8px; 
    padding: 8px; 
    font-weight: bold; 
}
QPushButton:hover { border: 1px solid #00ff00; color: #00ff00; }
QPushButton#WatchBtn { background-color: #004400; color: #00ff00; border: 1px solid #00ff00; }

QTextEdit#Console { background-color: #000; color: #00ff00; border: 1px solid #ff0000; font-family: 'Consolas'; }
"""
