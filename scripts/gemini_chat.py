#!/usr/bin/env python3
import sys
from google import genai
#!/usr/bin/env python3
import sys
from pathlib import Path
from dotenv import load_dotenv
import os
from google import genai

# ---- load .env ----
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("Error: GEMINI_API_KEY not set in .env")
    sys.exit(1)

if len(sys.argv) != 3:
    print("Usage: gemini_chat.py <initial_context.txt> <history_log.txt>")
    sys.exit(1)

initial_path = Path(sys.argv[1])
history_path = Path(sys.argv[2])

# ---- load initial context ----
initial_context = initial_path.read_text(encoding="utf-8").strip()

# ---- init Gemini client ----
client = genai.Client(api_key=API_KEY)

# ---- initialize history ----
if history_path.exists():
    history = history_path.read_text(encoding="utf-8").strip()
else:
    history = initial_context
    history_path.write_text(history + "\n", encoding="utf-8")

print("Initial context loaded.")
print(f"History file: {history_path.resolve()}")
print("Ctrl+C to exit.\n")

while True:
    try:
        user_input = input("You: ").strip()
        if not user_input:
            continue

        prompt = f"""{history}

User:
{user_input}

Assistant:"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        reply = response.text.strip()
        print(f"\nGemini:\n{reply}\n")

        # ---- append to history (persisted) ----
        history += f"""

User:
{user_input}

Assistant:
{reply}
"""
        history_path.write_text(history, encoding="utf-8")

    except KeyboardInterrupt:
        print("\nExiting.")
        break

if len(sys.argv) != 2:
    print("Usage: gemini_chat.py <initial_prompt.txt>")
    sys.exit(1)

# ---- read initial context from file ----
with open(sys.argv[1], "r", encoding="utf-8") as f:
    initial_context = f.read()

client = genai.Client()

# conversation buffer (ephemeral, in-memory only)
history = initial_context.strip()

print("Loaded initial context.")
print("Enter messages. Ctrl+C to exit.\n")

while True:
    try:
        user_input = input("You: ").strip()
        if not user_input:
            continue

        prompt = f"{history}\n\nUser:\n{user_input}\n\nAssistant:"
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        reply = response.text.strip()
        print(f"\nGemini:\n{reply}\n")

        # append to in-memory history only
        history = f"{prompt}\n{reply}"

    except KeyboardInterrupt:
        print("\nExiting.")
        break
