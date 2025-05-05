
import streamlit as st
import os
import tempfile
import openai
import datetime
from docx import Document
import zipfile
import io
import re
from PyPDF2 import PdfReader

openai.api_key = st.secrets["OPENAI_API_KEY"]

st.set_page_config(layout="wide")
st.title("ðŸ“˜ AI Training Content App")

uploaded_file = st.file_uploader("Upload a Markdown-style DOCX or PDF from the search app", type=["docx", "pdf"])

selected_sections = []
all_sections = []

def extract_sections_from_docx(doc_path):
    doc = Document(doc_path)
    text_blocks = [p.text.strip() for p in doc.paragraphs if p.text.strip() != ""]
    sections = []
    current_heading = None
    current_content = []

    for line in text_blocks:
        if line.startswith("### "):
            if current_heading and current_content:
                sections.append((current_heading, "\n".join(current_content).strip()))
            current_heading = line.replace("### ", "").strip()
            current_content = []
        elif current_heading:
            current_content.append(line)

    if current_heading and current_content:
        sections.append((current_heading, "\n".join(current_content).strip()))

    return sections

def extract_sections_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text_blocks = []
    for page in reader.pages:
        text_blocks.extend(page.extract_text().split("\n"))
    sections = []
    current_heading = None
    current_content = []

    for line in text_blocks:
        line = line.strip()
        if line.startswith("### "):
            if current_heading and current_content:
                sections.append((current_heading, "\n".join(current_content).strip()))
            current_heading = line.replace("### ", "").strip()
            current_content = []
        elif current_heading:
            current_content.append(line)

    if current_heading and current_content:
        sections.append((current_heading, "\n".join(current_content).strip()))

    return sections

if uploaded_file:
    filename = uploaded_file.name
    st.success(f"Uploaded file: {filename}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_path = tmp_file.name

    if filename.endswith(".docx"):
        extracted = extract_sections_from_docx(tmp_path)
    elif filename.endswith(".pdf"):
        extracted = extract_sections_from_pdf(tmp_path)
    else:
        st.error("Unsupported file type.")
        extracted = []

    if extracted:
        all_sections = [f"{i+1}. {title}" for i, (title, _) in enumerate(extracted)]
        selected_sections = st.multiselect("Choose section(s) to create class from", all_sections)