import argparse
import time
from dotenv import load_dotenv

load_dotenv()

from jarvis.core.voice import VoiceIO
from jarvis.core.agent import JarvisAgent
from jarvis.ui.overlay import JarvisOverlay


STARTUP_GREETING = "Good day. Jarvis online. All systems operational. How may I assist you?"
SHUTDOWN_LINE = "Shutting down. Have a good one."
IDLE_PROMPTS = [
    "Still here. What do you need?",
    "Standing by.",
    "Ready when you are.",
]


def main():
    parser = argparse.ArgumentParser(description="Jarvis personal AI assistant")
    parser.add_argument("--text", action="store_true", help="Use text input instead of voice")
    parser.add_argument("--no-wake", action="store_true", help="Skip wake word, listen immediately")
    parser.add_argument("--tray", action="store_true", help="Show system tray icon")
    args = parser.parse_args()

    tray = None
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

    # Startup sequence
    try:
        voice_io.sfx.startup()
    except Exception:
        pass
    time.sleep(0.4)
    if not args.text:
        try:
            voice_io.speak(STARTUP_GREETING)
        except Exception as e:
            print(f"Jarvis: {STARTUP_GREETING}")
    else:
        print(f"Jarvis: {STARTUP_GREETING}")


    idle_count = 0
    no_wake = args.no_wake

    try:
        while True:
            try:
                if args.text:
                    user_input = input("You: ").strip()
                    if not user_input:
                        continue
                else:
                    if not no_wake:
                        voice_io.wait_for_wake_word()
                    user_input = voice_io.listen()
                    if not user_input:
                        idle_count += 1
                        if idle_count % 5 == 0:
                            msg = IDLE_PROMPTS[(idle_count // 5 - 1) % len(IDLE_PROMPTS)]
                            voice_io.speak(msg)
                        continue
                    idle_count = 0

                # Check for exit commands — must be clearly directed at Jarvis
                _EXIT_PHRASES = (
                    "goodbye jarvis", "bye jarvis", "see you jarvis",
                    "go to sleep jarvis", "go off to sleep jarvis",
                    "stand by jarvis", "standby jarvis",
                    "jarvis shut down", "jarvis shutdown",
                    "jarvis go to sleep", "jarvis stand by",
                    "turn off jarvis", "switch off jarvis",
                )
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
