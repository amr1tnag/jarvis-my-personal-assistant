try:
    import speech_recognition as sr
    _SR_AVAILABLE = True
except ImportError:
    _SR_AVAILABLE = False

try:
    import pyttsx3
    _TTS_AVAILABLE = True
except ImportError:
    _TTS_AVAILABLE = False


class VoiceIO:
    def __init__(self):
        if _SR_AVAILABLE:
            self.recognizer = sr.Recognizer()
        if _TTS_AVAILABLE:
            self.engine = pyttsx3.init()

    def listen(self) -> str | None:
        if not _SR_AVAILABLE:
            print("[Voice unavailable] Type your message: ", end="")
            return input().strip() or None

        try:
            with sr.Microphone() as source:
                print("Listening...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=5)
                text = self.recognizer.recognize_google(audio)
                print(f"You: {text}")
                return text
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"Speech recognition error: {e}")
            return None
        except OSError:
            print("[No microphone detected] Type your message: ", end="")
            return input().strip() or None

    def speak(self, text: str) -> None:
        print(f"Jarvis: {text}")
        if _TTS_AVAILABLE:
            self.engine.say(text)
            self.engine.runAndWait()
