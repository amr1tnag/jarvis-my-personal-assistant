import argparse
import time
from dotenv import load_dotenv

load_dotenv()

from jarvis.core.voice import VoiceIO
from jarvis.core.agent import JarvisAgent


STARTUP_GREETING = "Good day. J.A.R.V.I.S. online. All systems operational. How may I assist you?"
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
    args = parser.parse_args()

    voice_io = VoiceIO()
    agent = JarvisAgent()

    # Startup sequence
    voice_io.sfx.startup()
    time.sleep(0.4)
    if args.text:
        print(f"Jarvis: {STARTUP_GREETING}")
    else:
        voice_io.speak(STARTUP_GREETING)

    idle_count = 0

    try:
        while True:
            if args.text:
                try:
                    user_input = input("You: ").strip()
                except EOFError:
                    break
                if not user_input:
                    continue
            else:
                if not args.no_wake:
                    voice_io.wait_for_wake_word()

                user_input = voice_io.listen()
                if not user_input:
                    idle_count += 1
                    if idle_count % 5 == 0:
                        msg = IDLE_PROMPTS[(idle_count // 5 - 1) % len(IDLE_PROMPTS)]
                        voice_io.speak(msg)
                    continue
                idle_count = 0

            # Check for exit commands
            if any(cmd in user_input.lower() for cmd in ("goodbye jarvis", "shut down", "shutdown", "exit", "quit")):
                voice_io.sfx.shutdown() if not args.text else None
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

    except KeyboardInterrupt:
        print(f"\nJarvis: {SHUTDOWN_LINE}")


if __name__ == "__main__":
    main()
