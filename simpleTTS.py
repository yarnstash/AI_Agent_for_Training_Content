import streamlit as st
import openai
import os
import tempfile

openai.api_key = st.secrets["OPENAI_API_KEY"]

st.set_page_config(page_title="Simple TTS Test", layout="centered")
st.title("TTS Test: Hello, Julian")

if st.button("Say Hello"):
    speech_file_path = os.path.join(tempfile.gettempdir(), "hello_julian.mp3")

    try:
        with openai.audio.speech.with_streaming_response.create(
            model="tts-1",
            voice="alloy",
            input="Hello, Julian"
        ) as response:
            response.stream_to_file(speech_file_path)

        if os.path.exists(speech_file_path) and os.path.getsize(speech_file_path) > 0:
            with open(speech_file_path, "rb") as f:
                st.success("Audio generated!")
                st.download_button("Download Audio", f, file_name="hello_julian.mp3")
                st.audio(f.read(), format="audio/mp3")
        else:
            st.error("Audio file was not generated or is empty.")

    except Exception as e:
        st.error(f"TTS failed: {e}")