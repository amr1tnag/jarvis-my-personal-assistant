import speech_recognition as sr
import pyttsx3


class VoiceIO:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.engine = pyttsx3.init()

    def listen(self) -> str | None:
        with sr.Microphone() as source:
            print("Listening...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
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

    def speak(self, text: str) -> None:
        print(f"Jarvis: {text}")
        self.engine.say(text)
        self.engine.runAndWait()
