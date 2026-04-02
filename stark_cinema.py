def live_voice_loop(self):
        r = sr.Recognizer()
        r.energy_threshold = 4000 # High threshold to ignore background noise
        while self.is_live_mode:
            if self.speak_lock.locked():
                time.sleep(1)
                continue
            for mic in MIC_INVENTORY:
                try:
                    with sr.Microphone(device_index=mic['id']) as src:
                        r.adjust_for_ambient_noise(src, duration=0.6) # Filters background hum
                        self.signals.log_signal.emit("🎤 Listening...")
                        audio = r.listen(src, timeout=4, phrase_time_limit=8)
                        q = r.recognize_google(audio).lower()
                        self.signals.log_signal.emit(f"🗣️ YOU: {q}")
                        
                        # --- JARVIS IDENTITY & INTENT ENGINE ---
                        if "stop" in q:
                            self.is_live_mode = False
                            self.signals.log_signal.emit("🛑 Standby initiated.")
                            self.speak("Going to sleep. I'll be here if you need me.")
                            return

                        if "who are you" in q or "your name" in q or "what's your name" in q:
                            self.speak("I am JARVIS. The Just A Rather Very Intelligent System. Ready for your command, Boss.")
                            break

                        if "horror" in q: self.run_genre(27); break
                        if "comedy" in q: self.run_genre(35); break
                        if "true crime" in q or "girlfriend" in q: 
                            self.speak("Accessing the Syndicate True Crime archives.")
                            self.run_genre("80,99"); 
                            break
                        
                        self.auto_pilot = "play" in q
                        target = q.replace("play", "").replace("movie", "").strip()
                        self.signals.search_trigger.emit(target)
                        break
                except: continue
            time.sleep(0.5)
