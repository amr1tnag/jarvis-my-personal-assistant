import os
import threading
import time
import wave
import struct
import math

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

import subprocess

def _speak_sapi(text: str):
    """Use Windows SAPI via PowerShell — releases audio device immediately."""
    safe = text.replace("'", "''")
    cmd = (
        f"Add-Type -AssemblyName System.Speech; "
        f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.Rate = -1; "
        f"$s.Speak('{safe}'); "
        f"$s.Dispose()"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
    except Exception as e:
        print(f"[TTS error: {e}]", flush=True)


def _generate_tone(filename: str, freq: float, duration: float, volume: float = 0.3, sample_rate: int = 44100):
    """Generate a simple sine wave tone and save as WAV."""
    n_samples = int(sample_rate * duration)
    with wave.open(filename, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        for i in range(n_samples):
            t = i / sample_rate
            fade = min(1.0, min(t / 0.01, (duration - t) / 0.01))
            val = int(volume * fade * 32767 * math.sin(2 * math.pi * freq * t))
            f.writeframes(struct.pack('<h', val))


def _play_wav(filename: str):
    try:
        import pyaudio
        wf = wave.open(filename, 'rb')
        p = pyaudio.PyAudio()
        stream = p.open(
            format=p.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True,
        )
        data = wf.readframes(1024)
        while data:
            stream.write(data)
            data = wf.readframes(1024)
        stream.stop_stream()
        stream.close()
        p.terminate()
    except Exception:
        pass


class SoundFX:
    _dir = os.path.join(os.path.dirname(__file__), "_sounds")

    def __init__(self):
        os.makedirs(self._dir, exist_ok=True)
        self._startup = os.path.join(self._dir, "startup.wav")
        self._listen = os.path.join(self._dir, "listen.wav")
        self._process = os.path.join(self._dir, "process.wav")
        self._shutdown = os.path.join(self._dir, "shutdown.wav")
        self._generate_sounds()

    def _generate_sounds(self):
        # Startup: ascending two-tone chime
        if not os.path.exists(self._startup):
            _generate_tone(self._startup + ".1.wav", 880, 0.15, 0.25)
            _generate_tone(self._startup + ".2.wav", 1318, 0.25, 0.25)
            self._merge([self._startup + ".1.wav", self._startup + ".2.wav"], self._startup)

        if not os.path.exists(self._listen):
            _generate_tone(self._listen, 660, 0.1, 0.2)

        if not os.path.exists(self._process):
            _generate_tone(self._process, 440, 0.08, 0.15)

        if not os.path.exists(self._shutdown):
            _generate_tone(self._shutdown + ".1.wav", 1318, 0.15, 0.2)
            _generate_tone(self._shutdown + ".2.wav", 880, 0.2, 0.2)
            self._merge([self._shutdown + ".1.wav", self._shutdown + ".2.wav"], self._shutdown)

    def _merge(self, files: list, out: str, gap_ms: int = 80):
        """Concatenate WAV files with a small gap."""
        import struct, wave
        gap_samples = int(44100 * gap_ms / 1000)
        gap = struct.pack('<' + 'h' * gap_samples, *([0] * gap_samples))
        with wave.open(out, 'w') as wout:
            wout.setnchannels(1)
            wout.setsampwidth(2)
            wout.setframerate(44100)
            for i, f in enumerate(files):
                with wave.open(f, 'rb') as win:
                    wout.writeframes(win.readframes(win.getnframes()))
                if i < len(files) - 1:
                    wout.writeframes(gap)
        for f in files:
            try:
                os.remove(f)
            except Exception:
                pass

    def startup(self):
        threading.Thread(target=_play_wav, args=(self._startup,), daemon=True).start()

    def listen(self):
        threading.Thread(target=_play_wav, args=(self._listen,), daemon=True).start()

    def process(self):
        threading.Thread(target=_play_wav, args=(self._process,), daemon=True).start()

    def shutdown(self):
        _play_wav(self._shutdown)


WAKE_WORDS = {"hey jarvis", "jarvis", "ok jarvis", "okay jarvis"}


class VoiceIO:
    def __init__(self):
        self.sfx = SoundFX()

        if _SR_AVAILABLE:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True

        if _TTS_AVAILABLE:
            self.engine = pyttsx3.init()
            self._setup_voice()

    def _setup_voice(self):
        voices = self.engine.getProperty('voices')
        # Prefer a male British/English voice
        preferred = None
        for v in voices:
            name = (v.name or "").lower()
            lang = (getattr(v, 'languages', None) or [])
            lang_str = " ".join(str(l) for l in lang).lower() if lang else ""
            if any(k in name for k in ("david", "mark", "george", "james", "daniel", "zira")):
                preferred = v
                break
            if "en" in lang_str and preferred is None:
                preferred = v
        if preferred:
            self.engine.setProperty('voice', preferred.id)
        # Slightly slower, deeper feel
        self.engine.setProperty('rate', 165)
        self.engine.setProperty('volume', 1.0)

    def _listen_once(self, timeout: int = 5, phrase_limit: int = 10) -> str | None:
        try:
            with sr.Microphone() as source:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            return self.recognizer.recognize_google(audio).lower().strip()
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return None
        except sr.RequestError as e:
            print(f"[Speech error: {e}]")
            return None
        except OSError:
            return None

    def wait_for_wake_word(self):
        """Block until a wake word is detected."""
        print("Waiting for wake word ('Hey Jarvis')...")
        while True:
            text = self._listen_once(timeout=10, phrase_limit=4)
            if text and any(w in text for w in WAKE_WORDS):
                self.sfx.listen()
                print("[Wake word detected]")
                return

    def listen(self) -> str | None:
        """Listen for a command after wake word."""
        if not _SR_AVAILABLE:
            print("You: ", end="", flush=True)
            return input().strip() or None

        print("Opening mic...", flush=True)
        try:
            with sr.Microphone() as source:
                print("Listening...", flush=True)
                audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=15)
            print("Processing...", flush=True)
            text = self.recognizer.recognize_google(audio)
            print(f"You: {text}")
            return text
        except sr.UnknownValueError:
            print("[Didn't catch that]", flush=True)
            return None
        except sr.RequestError as e:
            print(f"[Speech error: {e}]", flush=True)
            return None
        except OSError as e:
            print(f"[Mic error: {e}]", flush=True)
            print("You: ", end="", flush=True)
            return input().strip() or None
        except Exception as e:
            print(f"[Listen error: {type(e).__name__}: {e}]", flush=True)
            return None

    def speak(self, text: str) -> None:
        print(f"Jarvis: {text}")
        self.sfx.process()
        time.sleep(0.1)
        _speak_sapi(text)
        time.sleep(0.3)
