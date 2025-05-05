import streamlit as st
import os
import tempfile
import openai
import datetime
from docx import Document
import zipfile
import io
import re
from io import BytesIO

openai.api_key = st.secrets["OPENAI_API_KEY"]

st.set_page_config(layout="wide")
st.title("📘 AI Training Content App")

uploaded_files = st.file_uploader("Upload one or more documents (PDF or DOCX)", type=["pdf", "docx"], accept_multiple_files=True)

selected_sections = []
all_text_blocks = []

#Helper: Extract text from uploaded files

def extract_text_from_file(uploaded_file): ext = os.path.splitext(uploaded_file.name)[1].lower() text = "" if ext == ".docx": doc = Document(uploaded_file) for para in doc.paragraphs: if para.text.strip(): text += para.text.strip() + "\n" elif ext == ".pdf": from PyPDF2 import PdfReader reader = PdfReader(uploaded_file) for page in reader.pages: page_text = page.extract_text() if page_text: text += page_text + "\n" return text

if uploaded_files: all_text = "" for file in uploaded_files: all_text += extract_text_from_file(file) + "\n"

prompt = st.text_input("Enter a prompt to extract relevant content from uploaded documents (e.g., 'show all content about narratives'):")
if prompt:
    with st.spinner("Analyzing content..."):
        response = openai.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts relevant content."},
                {"role": "user", "content": f"Extract all relevant content from this text based on the prompt '{prompt}'. Present the results in sections with markdown headings prefixed by ###.\n\n{all_text}"}
            ]
        )
        search_result = response.choices[0].message.content
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_path = os.path.join(tempfile.gettempdir(), f"search_result_{timestamp}.docx")
        doc = Document()
        for line in search_result.splitlines():
            if line.startswith("### "):
                doc.add_heading(line[4:].strip(), level=3)
            else:
                doc.add_paragraph(line.strip())
        doc.save(temp_path)
        st.success("Search results extracted.")

        with open(temp_path, "rb") as f:
            st.download_button("Download Extracted Content (DOCX)", data=f, file_name=os.path.basename(temp_path))

        st.divider()
        st.subheader("Step 2: Generate Class Content")
        doc = Document(temp_path)
        text_blocks = [p.text.strip() for p in doc.paragraphs if p.text.strip() != ""]
        extracted = []
        current_heading = None
        current_content = []

        for line in text_blocks:
            if line.startswith("### "):
                if current_heading and current_content:
                    extracted.append((current_heading, "\n".join(current_content).strip()))
                current_heading = line.replace("### ", "").strip()
                current_content = []
            elif current_heading:
                current_content.append(line)
        if current_heading and current_content:
            extracted.append((current_heading, "\n".join(current_content).strip()))

        all_sections = [f"{i+1}. {title}" for i, (title, _) in enumerate(extracted)]
        selected_sections = st.multiselect("Choose section(s) to create class from", all_sections)

        run_type = st.session_state.get("run_type", "")
        col1, col2 = st.columns(2)
        if col1.button("Create QuickByte"):
            st.session_state.run_type = "QuickByte"
        if col2.button("Create FastTrack", disabled=len(selected_sections) < 1):
            st.session_state.run_type = "FastTrack"

        if "run_type" in st.session_state and st.session_state.run_type:
            selected_indices = [int(s.split(".")[0]) - 1 for s in selected_sections]
            selected_content = "\n\n".join(extracted[i][1] for i in selected_indices)

            with st.spinner("Generating design document..."):
                response = openai.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert instructional designer creating a class design document in markdown format."},
                        {"role": "user", "content": f"Create a class design document using markdown syntax. The format should include a title, duration, audience, learning objectives, required materials, preparation, instructor notes, and detailed step-by-step teaching plan. Base the content on:

\n\n{selected_content}"} ] ) md_output = response.choices[0].message.content st.divider() st.subheader("Step 3: Class Design Document") st.download_button("Download Design Document (Markdown)", data=md_output, file_name=f"class_design_{timestamp}.md") st.code(md_output, language="markdown")

