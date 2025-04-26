import streamlit as st
import os
import tempfile
import openai
import datetime
from typing import List
from PyPDF2 import PdfReader
from docx import Document
from dotenv import load_dotenv
import re

# Load environment variables from .env file
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

st.set_page_config(layout="wide")
st.title("📘 AI Agent for IT Training Content")

uploaded_file = st.file_uploader("Upload a vendor PDF or Quick Reference Word doc", type=["pdf", "docx"])

selected_sections = []
all_sections = []

def create_word_doc(text, filename):
    doc = Document()
    doc.add_paragraph(text)
    temp_path = os.path.join(tempfile.gettempdir(), filename)
    doc.save(temp_path)
    return temp_path

def create_text_file(text, filename):
    temp_path = os.path.join(tempfile.gettempdir(), filename)
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(text)
    return temp_path

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_path = tmp_file.name

    def extract_text_by_headings(pdf_path):
        reader = PdfReader(pdf_path)
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() + "\n"

        headings = re.findall(r"(?m)^[A-Z][A-Z \-\d]{3,}$", full_text)
        sections = re.split(r"(?m)^[A-Z][A-Z \-\d]{3,}$", full_text)[1:]

        return list(zip(headings, sections))

    extracted = extract_text_by_headings(tmp_path)

    if extracted:
        all_sections = [f"{i+1}. {title.strip()}" for i, (title, _) in enumerate(extracted)]
        selected_sections = st.multiselect("Choose section(s) to create class from", all_sections)

        single_btn_col, multi_btn_col = st.columns([1, 1])

        run_type = st.session_state.get("run_type", "")
        if st.button("Create QuickByte"):
            st.session_state.run_type = "QuickByte"
        if st.button("Create FastTrack", disabled=len(selected_sections) < 1):
            st.session_state.run_type = "FastTrack"

        if "run_type" in st.session_state and st.session_state.run_type:
            selected_indices = [int(s.split(".")[0]) - 1 for s in selected_sections]
            selected_content = "\n\n".join(extracted[i][1] for i in selected_indices)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

            with st.spinner("Generating content..."):
                outline_response = openai.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert instructional designer."},
                        {"role": "user", "content": f"Create an outline with learning objectives for a {'15-minute QuickByte' if st.session_state.run_type == 'QuickByte' else '30-minute FastTrack'} instructor-led class based on this:\n{selected_content}"},
                    ]
                )

                script_response = openai.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        {"role": "system", "content": "You are a professional e-learning narrator."},
                        {"role": "user", "content": f"Write a friendly but professional narration script for a video based on this content:\n{selected_content}"},
                    ]
                )

                tips_response = openai.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        {"role": "system", "content": "You are an instructional content expert."},
                        {"role": "user", "content": f"Generate exactly 5 email tips based on the following training content. Each tip must include the following format:\n\nTip #: <Title>\nFeature:\nBenefit:\nSteps:\n\nOutput each tip as a separate piece, clearly numbered and formatted."},
                    ]
                )

                outline_text = outline_response.choices[0].message.content
                script_text = script_response.choices[0].message.content
                tips_text = tips_response.choices[0].message.content

                # Parse the tips
                tips = []
                tip_pattern = r"(Tip \d+: .+?)(?=\nTip \d+:|\Z)"
                matches = re.findall(tip_pattern, tips_text, re.DOTALL)

                # If fewer than 5 tips are generated, retry the generation
                while len(matches) < 5:
                    st.warning("Insufficient tips generated. Regenerating...")
                    tips_response = openai.chat.completions.create(
                        model="gpt-4.1-mini",
                        messages=[
                            {"role": "system", "content": "You are an instructional content expert."},
                            {"role": "user", "content": f"Generate exactly 5 email tips based on the following training content. Each tip must include the following format:\n\nTip #: <Title>\nFeature:\nBenefit:\nSteps:\n\nOutput each tip as a separate piece, clearly numbered and formatted."},
                        ]
                    )
                    tips_text = tips_response.choices[0].message.content
                    matches = re.findall(tip_pattern, tips_text, re.DOTALL)

                tip_files = []
                for i, tip in enumerate(matches[:5]):
                    tip_filename = f"email_tip_{i+1}_{timestamp}.docx"
                    tip_path = create_word_doc(tip.strip(), tip_filename)
                    tip_files.append((f"Email Tip {i+1}", tip.strip(), tip_path))

                outline_file = create_word_doc(outline_text, f"class_outline_{timestamp}.docx")
                script_file = create_text_file(script_text, f"narration_script_{timestamp}.txt")

                st.session_state.generated = True
                st.session_state.tabs = {
                    "Outline": (outline_text, outline_file),
                    "Narration": (script_text, script_file),
                    "Email Tips": (tip_files, None),
                }

        if st.session_state.get("generated"):
            # Use actual visual tabs
            tab_selection = st.selectbox("Select Output to View/Download", options=["Outline", "Narration", "Email Tips"])

            if tab_selection == "Outline":
                tab_content, tab_file = st.session_state.tabs["Outline"]
                st.write(tab_content)
                with open(tab_file, "rb") as f:
                    st.download_button(label="Download Class Outline", data=f, file_name=os.path.basename(tab_file))
            elif tab_selection == "Narration":
                tab_content, tab_file = st.session_state.tabs["Narration"]
                st.write(tab_content)
                with open(tab_file, "rb") as f:
                    st.download_button(label="Download Narration Script", data=f, file_name=os.path.basename(tab_file))
            elif tab_selection == "Email Tips":
                tab_content, _ = st.session_state.tabs["Email Tips"]
                for tip_title, tip_text, tip_path in tab_content:
                    with st.expander(tip_title):
                        st.write(tip_text)
                        with open(tip_path, "rb") as f:
                            st.download_button(label=f"Download {tip_title}", data=f, file_name=os.path.basename(tip_path))
