# generate_tts.py
import openai
import sys
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

text = sys.stdin.read()
output_path = sys.argv[1]

response = openai.audio.speech.create(
    model="tts-1",
    voice="alloy",
    input=text
)

with open(output_path, "wb") as f:
    f.write(response.content)
