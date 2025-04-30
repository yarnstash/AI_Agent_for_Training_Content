import streamlit as st
import openai
import os
import tempfile

openai.api_key = st.secrets["OPENAI_API_KEY"]

st.set_page_config(page_title="Simple TTS Test", layout="centered")
st.title("TTS Test")

if st.button("Say Hello"):
    speech_file_path = os.path.join(tempfile.gettempdir(), "hello_julian.mp3")

    try:
        response = openai.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input="Hello, Julian"
        )

        with open(speech_file_path, "wb") as f:
            f.write(response.content)

        with open(speech_file_path, "rb") as f:
            st.success("Audio generated!")
            st.download_button("Download Audio", f, file_name="hello_julian.mp3")
            st.audio(f.read(), format="audio/mp3")

    except Exception as e:
        st.error(f"TTS failed: {e}")