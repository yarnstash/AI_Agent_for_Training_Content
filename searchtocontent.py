
import streamlit as st
import os
import tempfile
import openai
import datetime
from docx import Document
from PyPDF2 import PdfReader
import zipfile
import io
import re

openai.api_key = st.secrets["OPENAI_API_KEY"]

st.set_page_config(layout="wide")
st.title("ðŸ“˜ AI Training Content App with Search Integration")

uploaded_files = st.file_uploader("Upload one or more source documents (PDF or DOCX)", type=["pdf", "docx"], accept_multiple_files=True)

selected_sections = []
all_sections = []
document_chunks = []

def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def extract_text_from_docx(file_path):
    doc = Document(file_path)
    return " ".join(p.text for p in doc.paragraphs if p.text.strip())

if uploaded_files:
    st.session_state.uploaded_chunks = []
    for uploaded_file in uploaded_files:
        suffix = ".pdf" if uploaded_file.name.endswith(".pdf") else ".docx"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = tmp_file.name

        if suffix == ".pdf":
            extracted_text = extract_text_from_pdf(tmp_path)
        else:
            extracted_text = extract_text_from_docx(tmp_path)

        st.session_state.uploaded_chunks.append((uploaded_file.name, extracted_text))

    st.success("Files uploaded and content extracted.")

    # Build index of headings to choose from
    headings = []
    for filename, content in st.session_state.uploaded_chunks:
        lines = content.splitlines()
        for line in lines:
            if len(line.strip()) > 20 and line.strip() == line.strip().upper():
                headings.append(line.strip())

    unique_headings = sorted(set(headings))
    selected_topics = st.multiselect("Select topics to include in your class", unique_headings)

    if selected_topics:
        relevant_text = []
        for filename, content in st.session_state.uploaded_chunks:
            for topic in selected_topics:
                if topic in content:
                    relevant_text.append(f"{topic}
" + content.split(topic, 1)[-1].split("
", 1)[-1])
        selected_text = "

".join(relevant_text)

        if "run_type" not in st.session_state:
            col1, col2 = st.columns(2)
            if col1.button("Create QuickByte"):
                st.session_state.run_type = "QuickByte"
            if col2.button("Create FastTrack"):
                if len(selected_text.split()) > 2000:
                    st.warning("FastTrack class should be no more than 30 minutes. Please reduce the content.")
                else:
                    st.session_state.run_type = "FastTrack"

        if "run_type" in st.session_state:
            if not all(k in st.session_state for k in ["outline_text", "script_text", "tips_text"]):
                with st.spinner("Generating training content..."):
                    response_outline = openai.chat.completions.create(
                        model="gpt-4.1-mini",
                        messages=[
                            {"role": "system", "content": "You are an expert instructional designer."},
                            {"role": "user", "content": f"Create a detailed outline for a {st.session_state.run_type} class based on this: {selected_text}"}
                        ]
                    )
                    response_script = openai.chat.completions.create(
                        model="gpt-4.1-mini",
                        messages=[
                            {"role": "system", "content": "You are a professional training narrator."},
                            {"role": "user", "content": f"Write a narration script for a video class based on this: {selected_text}"}
                        ]
                    )
                    response_tips = openai.chat.completions.create(
                        model="gpt-4.1-mini",
                        messages=[
                            {"role": "system", "content": "You are an expert trainer."},
                            {"role": "user", "content": f"Generate 5 email tips based on this content. Each tip should be clearly separated by 'Tip X:' and include a benefit and step-by-step instructions: {selected_text}"}
                        ]
                    )
                    st.session_state.outline_text = response_outline.choices[0].message.content
                    st.session_state.script_text = response_script.choices[0].message.content
                    st.session_state.tips_text = response_tips.choices[0].message.content

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

            def save_docx(text, filename):
                path = os.path.join(tempfile.gettempdir(), filename)
                doc = Document()
                doc.add_paragraph(text)
                doc.save(path)
                return path

            def save_txt(text, filename):
                path = os.path.join(tempfile.gettempdir(), filename)
                with open(path, "w") as f:
                    f.write(text)
                return path

            outline_file = save_docx(st.session_state.outline_text, f"outline_{timestamp}.docx")
            script_file = save_txt(st.session_state.script_text, f"script_{timestamp}.txt")

            tip_blocks = re.findall(r"Tip\s+\d+:(.*?)(?=Tip\s+\d+:|\Z)", st.session_state.tips_text, re.DOTALL)
            tips = [f"Tip {i+1}: {block.strip()}" for i, block in enumerate(tip_blocks)][:5]

            tip_paths = []
            for i, tip in enumerate(tips):
                tip_paths.append(save_docx(tip, f"email_tip_{i+1}_{timestamp}.docx"))

            st.session_state.tabs = {
                "Outline": (st.session_state.outline_text, outline_file),
                "Narration": (st.session_state.script_text, script_file),
                "Email Tips": (tips, tip_paths)
            }

if "tabs" in st.session_state:
    tabs = st.tabs(["Outline", "Narration", "Email Tips"])

    with tabs[0]:
        content, path = st.session_state.tabs["Outline"]
        with open(path, "rb") as f:
            st.download_button("Download Outline", f, os.path.basename(path))
        st.markdown(content)

    with tabs[1]:
        content, path = st.session_state.tabs["Narration"]
        with open(path, "rb") as f:
            st.download_button("Download Narration Script", f, os.path.basename(path))
        st.markdown(content)

    with tabs[2]:
        tips, paths = st.session_state.tabs["Email Tips"]
        for i, (tip, path) in enumerate(zip(tips, paths)):
            st.markdown(f"**Tip {i+1}:** {tip}")
            with open(path, "rb") as f:
                st.download_button(f"Download Tip {i+1}", f, os.path.basename(path))