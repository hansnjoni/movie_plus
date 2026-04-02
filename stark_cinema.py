def live_voice_loop(self):
        import speech_recognition as sr
        r = sr.Recognizer()
        
        # --- SPEED OPTIMIZED SETTINGS ---
        r.energy_threshold = 4000      # High sensitivity for clear voice
        r.pause_threshold = 0.8       # FAST RESPONSE: Wait only 0.8s of silence
        r.non_speaking_duration = 0.4  # Quick rejection of shop noise
        
        while self.is_live_mode:
            try:
                with sr.Microphone() as src:
                    # Quick room calibration
                    r.adjust_for_ambient_noise(src, duration=0.5) 
                    self.signals.log_signal.emit("📡 JARVIS: Ready...")
                    
                    # Listen - No timeout so he stays open
                    audio = r.listen(src, timeout=None, phrase_time_limit=10)
                    
                    # --- INSTANT PROCESSING ---
                    q = r.recognize_google(audio).lower()
                    self.signals.log_signal.emit(f"YOU: {q}")
                    
                    # CHECK FOR COMMANDS FIRST
                    if any(x in q for x in ["play", "find", "search", "show me"]):
                        target = q.replace("play", "").replace("find", "").replace("search", "").replace("show me", "").strip()
                        if target:
                            # TRIGGER VOICE IMMEDIATELY FOR SPEED FEEL
                            self.speak(f"On it, Hans. Pulling up {target}.")
                            self.signals.search_trigger.emit(target)
                            break 

                    # CHECK FOR CONVERSATION
                    if any(x in q for x in ["how are you", "status", "how's it going"]):
                        self.speak(random.choice(RESPONSES["greetings"]))
                        continue

                    if any(x in q for x in ["tired", "work", "job", "pipes", "wire"]):
                        self.speak(random.choice(RESPONSES["work_talk"]))
                        continue

            except sr.UnknownValueError:
                continue 
            except Exception as e:
                self.signals.log_signal.emit(f"⚠️ Link Error: {str(e)}")
                continue
