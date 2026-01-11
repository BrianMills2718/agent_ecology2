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

# ---- read specs file ----
specs_path = Path("/home/azureuser/brian_misc/agent_ecology/agent_ecology_v2_specs.txt")
specs_content = specs_path.read_text(encoding="utf-8")

# ---- build prompt ----
# The specs already start with context, so we prepend a clear instruction
prompt = f"""You are reviewing a design specification document. Please provide a thorough critique and help figure out the minimal V1 version that can be implemented with approximately 5 LLM agents, proceeding in thin slices.

The LLM that generated these specs made many assumptions that are not necessarily true - everything is on the table, including any "hard rules" mentioned in the document. Be critical and practical.

Here is the specification document:

{specs_content}

---
Now please provide:
1. Key critique points - what's overcomplicated, unclear, or unnecessary
2. A proposed minimal V1 scope with ~5 LLM agents
3. Suggested thin slices (incremental implementation steps)
4. What to defer vs what's essential for V1"""

# ---- init Gemini client and send ----
client = genai.Client(api_key=API_KEY)

print("Sending specs to Gemini for critique...")
print(f"Specs size: {len(specs_content)} characters\n")

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
)

print("=" * 60)
print("GEMINI CRITIQUE:")
print("=" * 60)
print(response.text)

# ---- save response ----
output_path = Path("/home/azureuser/brian_misc/agent_ecology/specs_critique.txt")
output_path.write_text(response.text, encoding="utf-8")
print(f"\n[Critique saved to {output_path}]")
