import streamlit as st
import os
import tempfile
import openai
import datetime from docx
import Document
import zipfile 
import io
import re from io
import BytesIO

openai.api_key = st.secrets["OPENAI_API_KEY"]

st.set_page_config(layout="wide") st.title("📘 AI Training Content App")

uploaded_file = st.file_uploader("Upload a Markdown-style DOCX from the search app", type=["docx"])

selected_sections = [] all_sections = []

Extract sections from Markdown-style headings in .docx (### style)

def extract_sections_markdown_headings(doc_path): doc = Document(doc_path) text_blocks = [p.text.strip() for p in doc.paragraphs if p.text.strip() != ""] sections = [] current_heading = None current_content = []

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

if uploaded_file: with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file: tmp_file.write(uploaded_file.read()) tmp_path = tmp_file.name

extracted = extract_sections_markdown_headings(tmp_path)

if extracted:
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
                    {"role": "user", "content": f"Generate exactly 5 email tips based on the following training content. Each tip should describe one useful feature, explain its benefit, and provide short step-by-step instructions. Output each as a separate tip, clearly numbered or titled:\n{selected_content}"},
                ]
            )

            outline_text = outline_response.choices[0].message.content
            script_text = script_response.choices[0].message.content
            tips_text = tips_response.choices[0].message.content

            # Create downloadable files
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

            outline_file = create_word_doc(outline_text, f"class_outline_{timestamp}.docx")
            script_file = create_text_file(script_text, f"narration_script_{timestamp}.txt")

            tips = re.split(r"(?m)^\s*(?:\d+\.\s+|Tip\s+\d+:)", tips_text)
            tips = [tip.strip() for tip in tips if tip.strip()][:5]

            tip_files = []
            for i, tip in enumerate(tips):
                tip_filename = f"email_tip_{i+1}_{timestamp}.docx"
                tip_path = create_word_doc(tip, tip_filename)
                tip_files.append((f"Email Tip {i+1}", tip, tip_path))

            tip_zip = io.BytesIO()
            with zipfile.ZipFile(tip_zip, "w") as zipf:
                for _, _, path in tip_files:
                    zipf.write(path, os.path.basename(path))
            tip_zip.seek(0)

            st.session_state.generated = True
            st.session_state.timestamp = timestamp
            st.session_state.tabs = {
                "Outline": (outline_text, outline_file),
                "Narration": (script_text, script_file),
                "Email Tips": (tips, tip_zip)
            }

if st.session_state.get("generated"): tabs = st.tabs(["Outline", "Narration", "Email Tips"])

with tabs[0]:
    tab_content, tab_file = st.session_state.tabs["Outline"]
    with open(tab_file, "rb") as f:
        st.download_button(label="Download Class Outline", data=f, file_name=os.path.basename(tab_file))
    st.markdown(tab_content)

with tabs[1]:
    tab_content, tab_file = st.session_state.tabs["Narration"]
    with open(tab_file, "rb") as f:
        st.download_button(label="Download Narration Script", data=f, file_name=os.path.basename(tab_file))
    st.markdown(tab_content)

with tabs[2]:
    tip_texts, tip_zip = st.session_state.tabs["Email Tips"]
    st.download_button("Download All Email Tips", data=tip_zip, file_name=f"email_tips_{st.session_state.timestamp}.zip")
    for i, tip in enumerate(tip_texts):
        st.markdown(f"**Tip {i+1}:** {tip}")

