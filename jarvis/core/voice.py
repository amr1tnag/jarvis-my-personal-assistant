import os
import threading
import time
import wave
import struct
import math
import io
import tempfile

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

# Whisper (faster-whisper) for local, offline, faster STT
_whisper_model = None
try:
    from faster_whisper import WhisperModel
    print("[STT] Loading Whisper tiny model...")
    _whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
    print("[STT] Whisper ready")
except Exception as _e:
    print(f"[STT] Whisper unavailable ({_e}) — using Google STT")

try:
    import pygame
    pygame.mixer.init()
    _PYGAME_AVAILABLE = True
except Exception:
    _PYGAME_AVAILABLE = False

import subprocess
import queue

# ------------------------------------------------------------------ #
# ElevenLabs TTS (used when ELEVENLABS_API_KEY is set)               #
# ------------------------------------------------------------------ #
_ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
_ELEVEN_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "")   # paste your Vikram voice ID here
_ELEVEN_MODEL = os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")
_eleven_client = None

if _ELEVEN_API_KEY:
    try:
        from elevenlabs import ElevenLabs
        _eleven_client = ElevenLabs(api_key=_ELEVEN_API_KEY)
        print("[TTS] ElevenLabs ready")
    except Exception as e:
        print(f"[TTS] ElevenLabs init failed: {e} — falling back to PowerShell")


def _elevenlabs_speak(text: str):
    try:
        audio_iter = _eleven_client.text_to_speech.convert(
            voice_id=_ELEVEN_VOICE_ID,
            text=text,
            model_id=_ELEVEN_MODEL,
            output_format="mp3_44100_128",
        )
        audio_bytes = b"".join(audio_iter)
        if _PYGAME_AVAILABLE:
            pygame.mixer.music.load(io.BytesIO(audio_bytes), "mp3")
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
        else:
            # Write to temp file and play via Windows
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(audio_bytes)
                tmp = f.name
            subprocess.run(
                ["powershell", "-c", f"(New-Object Media.SoundPlayer '{tmp}').PlaySync()"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            os.unlink(tmp)
    except Exception as e:
        print(f"[ElevenLabs TTS error: {e}] — falling back to PowerShell")
        _powershell_speak(text)


# ------------------------------------------------------------------ #
# PowerShell TTS fallback                                             #
# ------------------------------------------------------------------ #
def _powershell_speak(text: str):
    safe = text.replace("'", "''")
    cmd = (
        f"Add-Type -AssemblyName System.Speech; "
        f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.Rate = 2; $s.Speak('{safe}'); $s.Dispose()"
    )
    try:
        proc = subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", cmd],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        proc.wait(timeout=30)
    except Exception:
        pass


_tts_done = threading.Event()
_tts_queue: queue.Queue = queue.Queue()
_tts_ready = threading.Event()

def _tts_worker():
    _tts_ready.set()
    while True:
        text = _tts_queue.get()
        if text is None:
            break
        _tts_done.clear()
        if _eleven_client:
            _elevenlabs_speak(text)
        else:
            _powershell_speak(text)
        _tts_done.set()

_tts_thread = threading.Thread(target=_tts_worker, daemon=True)
_tts_thread.start()
_tts_ready.wait(timeout=3)

def _speak_sapi(text: str):
    _tts_done.clear()
    _tts_queue.put(text)
    _tts_done.wait(timeout=60)


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
    def __init__(self, on_state_change=None):
        self.sfx = SoundFX()
        self._on_state_change = on_state_change

        if _SR_AVAILABLE:
            self.recognizer = sr.Recognizer()
            self.recognizer.dynamic_energy_threshold = True
            # Calibrate once at startup instead of before every command
            try:
                with sr.Microphone() as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
            except Exception:
                self.recognizer.energy_threshold = 300

    def _set_state(self, state: str):
        if self._on_state_change:
            try:
                self._on_state_change(state)
            except Exception:
                pass

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

    def _transcribe(self, audio: "sr.AudioData") -> str | None:
        """Transcribe AudioData using Whisper (local) or Google STT as fallback."""
        if _whisper_model:
            try:
                wav_bytes = audio.get_wav_data()
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    f.write(wav_bytes)
                    tmp = f.name
                segments, _ = _whisper_model.transcribe(tmp, language="en", beam_size=1)
                os.unlink(tmp)
                text = " ".join(s.text for s in segments).strip()
                return text if text else None
            except Exception as e:
                print(f"[Whisper error: {e}] — falling back to Google")
        try:
            return self.recognizer.recognize_google(audio)
        except (sr.UnknownValueError, sr.RequestError):
            return None

    def _listen_once(self, timeout: int = 5, phrase_limit: int = 10) -> str | None:
        """Used only for wake word — always uses Google STT (fast, short phrase)."""
        try:
            with sr.Microphone() as source:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            return self.recognizer.recognize_google(audio).lower().strip()
        except (sr.WaitTimeoutError, sr.UnknownValueError, sr.RequestError):
            return None
        except OSError:
            return None

    def wait_for_wake_word(self):
        """Block until a wake word is detected."""
        print("Waiting for wake word ('Hey Jarvis')...")
        self._set_state("idle")
        while True:
            text = self._listen_once(timeout=10, phrase_limit=4)
            if text and any(w in text for w in WAKE_WORDS):
                self.sfx.listen()
                print("[Wake word detected]")
                self._set_state("listening")
                time.sleep(0.3)
                return

    def listen(self) -> str | None:
        """Listen for a command after wake word."""
        if not _SR_AVAILABLE:
            print("You: ", end="", flush=True)
            return input().strip() or None

        self._set_state("listening")
        try:
            with sr.Microphone() as source:
                print("Listening...", flush=True)
                audio = self.recognizer.listen(source, timeout=8, phrase_time_limit=15)
            text = self._transcribe(audio)
            if text:
                print(f"You: {text}")
                return text
            print("[Didn't catch that]", flush=True)
            return None
        except sr.WaitTimeoutError:
            print("[No speech detected]", flush=True)
            return None
        except OSError as e:
            print(f"[Mic error: {e}]", flush=True)
            print("You: ", end="", flush=True)
            return input().strip() or None
        except Exception as e:
            print(f"[Listen error: {type(e).__name__}: {e}]", flush=True)
            return None
        finally:
            self._set_state("idle")

    def speak(self, text: str) -> None:
        print(f"Jarvis: {text}", flush=True)
        self._set_state("speaking")
        _speak_sapi(text)
        self._set_state("idle")
