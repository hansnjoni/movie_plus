import os, re, threading
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from plyer import call # <-- The Native Android Telecom Relay
import speech_recognition as sr
import google.generativeai as genai

# --- 🧠 THE TELECOM AI CONFIG ---
GEMINI_API_KEY = "AIzaSyDhKiyDBdicvNAdhQzET1b9W4vsotmfrAw" 
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

SYSTEM_PROMPT = (
    "You are JARVIS, a telecom control AI for Hans, a master electrician. "
    "1. Answer general questions briefly (1 paragraph max). "
    "2. If Hans asks to call someone, you MUST output this exact format: [CMD: CALL | Name] "
    "Example: 'Patching you through now, Hans. [CMD: CALL | Landlord]' "
    "Never speak the command tag out loud."
)

class StarkTelecomApp(App):
    def build(self):
        # 🌑 Blackout Mobile UI
        Window.clearcolor = (0.05, 0.05, 0.05, 1)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        # --- 📖 THE MOBILE DIRECTORY ---
        self.contacts = {
            "little woman": "555-0101",
            "dad": "555-0102",
            "landlord": "555-0103",
            "supply house": "555-0104"
        }

        self.chat_session = model.start_chat(history=[])

        # UI Elements
        self.status_label = Label(text="SYSTEM ONLINE", color=(0, 1, 0, 1), font_size='20sp', size_hint=(1, 0.2))
        self.layout.add_widget(self.status_label)

        self.mic_btn = Button(text="🎙️ PRESS TO COMMUNICATE", background_color=(0.5, 0, 0, 1), font_size='24sp', bold=True)
        self.mic_btn.bind(on_press=self.start_listening_thread)
        self.layout.add_widget(self.mic_btn)

        return self.layout

    def start_listening_thread(self, instance):
        self.mic_btn.text = "🔴 LISTENING..."
        self.mic_btn.background_color = (1, 0, 0, 1)
        self.status_label.text = "Awaiting command..."
        threading.Thread(target=self.listen_and_process, daemon=True).start()

    def listen_and_process(self):
        r = sr.Recognizer()
        r.energy_threshold = 3500
        
        try:
            with sr.Microphone() as source:
                audio = r.listen(source, timeout=5, phrase_time_limit=10)
            
            self.status_label.text = "Processing..."
            query = r.recognize_google(audio).lower()
            self.status_label.text = f"👤 You: {query}"
            
            # Send to Gemini
            response = self.chat_session.send_message(f"{SYSTEM_PROMPT}\nHans says: {query}").text
            self.execute_logic(response)

        except sr.WaitTimeoutError:
            self.reset_ui("Timeout. No speech detected.")
        except sr.UnknownValueError:
            self.reset_ui("Static on the line. Couldn't understand.")
        except Exception as e:
            self.reset_ui(f"Connection failed.")

    def execute_logic(self, answer):
        # Scan the AI's response for the telecom tag
        cmd_match = re.search(r'\[CMD:\s*CALL\s*\|\s*(.*?)\]', answer, re.IGNORECASE)
        
        if cmd_match:
            name_query = cmd_match.group(1).strip().lower()
            spoken_answer = re.sub(r'\[CMD:.*?\]', '', answer, flags=re.IGNORECASE).strip()
            
            self.status_label.text = f"🤖 JARVIS: {spoken_answer}"
            self.make_phone_call(name_query)
        else:
            self.status_label.text = f"🤖 JARVIS: {answer}"
            
        self.reset_ui_after_delay()

    def make_phone_call(self, name_query):
        contact_number = None
        for name, number in self.contacts.items():
            if name in name_query:
                contact_number = number
                break
                
        if contact_number:
            self.status_label.text = f"📞 DIALING: {name_query.upper()}..."
            try:
                # The Android API Call to physically dial the radio
                call.makecall(tel=contact_number)
            except Exception as e:
                self.status_label.text = "❌ Telecom permissions required."
        else:
            self.status_label.text = f"❌ Number not found for {name_query}."
            
        self.reset_ui_after_delay()

    def reset_ui(self, msg):
        self.status_label.text = msg
        self.mic_btn.text = "🎙️ PRESS TO COMMUNICATE"
        self.mic_btn.background_color = (0.5, 0, 0, 1)

    def reset_ui_after_delay(self):
        import time
        time.sleep(3)
        self.mic_btn.text = "🎙️ PRESS TO COMMUNICATE"
        self.mic_btn.background_color = (0.5, 0, 0, 1)

if __name__ == '__main__':
    StarkTelecomApp().run()
