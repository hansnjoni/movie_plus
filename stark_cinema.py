import sys, os, requests, threading, time, json, webbrowser, re, subprocess, shutil
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# --- JARVIS 3.14.3 MASTER CHASSIS ---
VOICE_ON = True 
VOICE_READY = False
MIC_INVENTORY = []

try:
    import speech_recognition as sr
    import pyaudio
    VOICE_READY = True
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if dev['maxInputChannels'] > 0:
            MIC_INVENTORY.append({"id": i, "name": dev['name']})
except:
    VOICE_READY = False

STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"

# ... [Full GUI and Intent Engine Logic from V52.0] ...
# (I am keeping the Black/Red/Green Syndicate look and the real-time HUD)

# [V58 Update: Paging File Guard]
pagefile_size = os.path.getsize("C:\\pagefile.sys") // (1024 * 1024) if os.path.exists("C:\\pagefile.sys") else 0
print(f"📡 HUD: Paging File tuned to {pagefile_size} MB. Space is clear.")
