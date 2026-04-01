# --- JASON'S MEMORY FUNCTIONS ---
def get_jason_memory():
    """Ask Jason what he remembers about the movies."""
    file_name = "status_cache.json"
    if os.path.exists(file_name):
        try:
            with open(file_name, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_to_jason(m_id, status):
    """Tell Jason to remember a new movie result."""
    memory = get_jason_memory()
    m_id = str(m_id)
    
    # Record the result and the date
    memory[m_id] = {
        "status": status,
        "last_checked": str(datetime.now().date())
    }
    
    # THE 2000 LIMIT: If Jason gets too full, he forgets the oldest 500
    if len(memory) > 2000:
        sorted_keys = sorted(memory, key=lambda k: memory[k].get('last_checked', ''))
        for i in range(500):
            if i < len(sorted_keys):
                del memory[sorted_keys[i]]
            
    with open("status_cache.json", "w") as f:
        json.dump(memory, f)

# --- THE UPDATED WORKER (THE SNIPER) ---
def worker(self, url, task_id):
    """The main loop that sends out the Recon Spies."""
    res = self.api_call(url)
    results = res.get('results', [])
    
    # Load Jason's memory once at the start
    jason_memory = get_jason_memory()
    
    self.update_log(f"🕵️ Recon: Jason remembers {len(jason_memory)} movies.")
    
    count = 1
    for item in results:
        if self.task_counter != task_id: return
        m_id = str(item['id'])
        
        # 1. Check Jason first
        if m_id in jason_memory:
            if jason_memory[m_id]['status'] == "Available":
                # Jason says it's good! Show it immediately.
                self.executor.submit(self.load_image_worker, item, count, self.current_mode, task_id)
                count += 1
                continue
            elif jason_memory[m_id]['status'] == "Theaters":
                # Jason says it's a 'Cam' version. Skip it.
                continue

        # 2. If Jason doesn't know, send a Ping Recon
        threading.Thread(target=self.ping_recon, args=(item, count, task_id), daemon=True).start()
        count += 1
        time.sleep(0.05) # Keep it smooth

def ping_recon(self, item, rank, task_id):
    """The Ghost Sniper checks if the video actually exists."""
    m_id = str(item['id'])
    # Construct the test link
    if self.current_mode == "movie":
        test_url = f"https://vidsrc.me/embed/movie?tmdb={m_id}"
    else:
        test_url = f"https://vidsrc.me/embed/tv?tmdb={m_id}&season=1&episode=1"
        
    try:
        # We check the 'Header' to see if the server has the file (Code 200)
        response = requests.head(test_url, timeout=5)
        if response.status_code == 200:
            save_to_jason(m_id, "Available")
            self.executor.submit(self.load_image_worker, item, rank, self.current_mode, task_id)
        else:
            save_to_jason(m_id, "Theaters")
    except:
        # If the server is down, we don't save anything so we can check again later
        pass
