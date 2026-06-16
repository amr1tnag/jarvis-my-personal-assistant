import argparse
from dotenv import load_dotenv

load_dotenv()

from jarvis.core.voice import VoiceIO
from jarvis.core.agent import JarvisAgent


def main():
    parser = argparse.ArgumentParser(description="Jarvis personal AI assistant")
    parser.add_argument("--text", action="store_true", help="Use text input instead of voice")
    args = parser.parse_args()

    voice_io = VoiceIO()
    agent = JarvisAgent()

    print("Jarvis is ready. Press Ctrl+C to exit.")

    try:
        while True:
            if args.text:
                user_input = input("You: ").strip()
                if not user_input:
                    continue
            else:
                user_input = voice_io.listen()
                if not user_input:
                    continue

            response = agent.chat(user_input)

            if args.text:
                print(f"Jarvis: {response}")
            else:
                voice_io.speak(response)

    except KeyboardInterrupt:
        print("\nGoodbye!")


if __name__ == "__main__":
    main()
