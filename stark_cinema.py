def launch_stealth(self, m_id, m_type, s=1, e=1):
        import webbrowser
        try:
            ts = int(time.time())
            sub = "1" if self.subtitles else "0"
            
            if m_type == "movie":
                u = f"https://vidsrc.me/embed/movie?tmdb={m_id}&t={ts}&sub={sub}"
            else:
                u = f"https://vidsrc.me/embed/tv?tmdb={m_id}&season={s}&episode={e}&t={ts}&sub={sub}"
                
            self.update_log(f"🎬 Initiating Chrome Trojan Horse...")
            
            # 🛡️ Launching via your PC's default browser (Chrome) to bypass codec limits!
            webbrowser.open(u)
            
        except Exception as e:
            self.update_log(f"⚠️ CINEMA ERROR: {str(e)}")
