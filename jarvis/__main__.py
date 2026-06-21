import argparse
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from jarvis.core.voice import VoiceIO
from jarvis.core.agent import JarvisAgent
from jarvis.ui.overlay import JarvisOverlay

# How long (seconds) to stay in conversation mode after last reply
CONVO_TIMEOUT = 20

_EXIT_PHRASES = (
    "goodbye jarvis", "bye jarvis", "see you jarvis",
    "go to sleep jarvis", "go off to sleep jarvis",
    "stand by jarvis", "standby jarvis",
    "jarvis shut down", "jarvis shutdown",
    "jarvis go to sleep", "jarvis stand by",
    "turn off jarvis", "switch off jarvis",
)


def _startup_greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        part = "morning"
    elif hour < 17:
        part = "afternoon"
    else:
        part = "evening"
    return f"Good {part}, sir. Jarvis online. What do you need?"


SHUTDOWN_LINE = "Shutting down. Have a good one, sir."


def main():
    parser = argparse.ArgumentParser(description="Jarvis personal AI assistant")
    parser.add_argument("--text", action="store_true", help="Use text input instead of voice")
    parser.add_argument("--no-wake", action="store_true", help="Skip wake word, listen immediately")
    parser.add_argument("--tray", action="store_true", help="Show system tray icon")
    args = parser.parse_args()

    overlay = JarvisOverlay()
    overlay.start()

    def set_state(state: str):
        overlay.set_state(state)

    if args.tray:
        from jarvis.ui.tray import TrayIcon
        import os

        def _on_exit():
            os._exit(0)

        tray = TrayIcon(on_exit=_on_exit)
        _tray_set_state = tray.set_state

        def set_state(state: str):  # noqa: F811
            overlay.set_state(state)
            _tray_set_state(state)

        tray.run_detached()

    voice_io = VoiceIO(on_state_change=set_state)
    agent = JarvisAgent(on_state_change=set_state)

    # Startup
    try:
        voice_io.sfx.startup()
    except Exception:
        pass
    time.sleep(0.4)
    greeting = _startup_greeting()
    if not args.text:
        voice_io.speak(greeting)
    else:
        print(f"Jarvis: {greeting}")

    no_wake = args.no_wake

    try:
        while True:
            try:
                if args.text:
                    # ── text mode ──────────────────────────────────────────
                    user_input = input("You: ").strip()
                    if not user_input:
                        continue
                else:
                    # ── voice mode ─────────────────────────────────────────
                    if not no_wake:
                        voice_io.wait_for_wake_word()

                    # First command after wake word
                    user_input = voice_io.listen()
                    if not user_input:
                        continue

                # Exit check
                if any(cmd in user_input.lower() for cmd in _EXIT_PHRASES):
                    if args.text:
                        print(f"Jarvis: {SHUTDOWN_LINE}")
                    else:
                        voice_io.speak(SHUTDOWN_LINE)
                    break

                response = agent.chat(user_input)
                if args.text:
                    print(f"Jarvis: {response}")
                else:
                    voice_io.speak(response)

                # ── conversation mode: keep listening without wake word ──
                if not args.text and not no_wake:
                    convo_deadline = time.time() + CONVO_TIMEOUT
                    while time.time() < convo_deadline:
                        follow_up = voice_io.listen()
                        if not follow_up:
                            # Nothing heard — stay in convo window but keep waiting
                            continue

                        # If they say the wake word again, just strip it and continue
                        import re
                        cleaned = re.sub(
                            r"^(hey jarvis|jarvis|ok jarvis|okay jarvis)[,\s]*",
                            "", follow_up.lower()
                        ).strip()
                        if not cleaned:
                            # Just the wake word, nothing else — reset timer
                            convo_deadline = time.time() + CONVO_TIMEOUT
                            continue

                        if any(cmd in follow_up.lower() for cmd in _EXIT_PHRASES):
                            voice_io.speak(SHUTDOWN_LINE)
                            return

                        response = agent.chat(cleaned or follow_up)
                        if args.text:
                            print(f"Jarvis: {response}")
                        else:
                            voice_io.speak(response)
                        # Reset conversation timer after each reply
                        convo_deadline = time.time() + CONVO_TIMEOUT

            except EOFError:
                break
            except Exception as e:
                print(f"[Error: {e}]")
                time.sleep(1)
                continue

    except KeyboardInterrupt:
        print(f"\nJarvis: {SHUTDOWN_LINE}")


if __name__ == "__main__":
    main()
