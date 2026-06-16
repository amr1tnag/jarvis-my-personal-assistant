import pyttsx3
engine = pyttsx3.init()
voices = engine.getProperty('voices')
print(f"Found {len(voices)} voices:")
for i, v in enumerate(voices):
    print(f"  [{i}] {v.name} | {v.id}")
print("\nTesting speech...")
engine.say("Hello sir, Jarvis is online.")
engine.runAndWait()
print("Done.")
