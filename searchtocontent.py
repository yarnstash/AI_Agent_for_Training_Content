
import streamlit as st
import os
import tempfile
import openai
import datetime
from docx import Document
import zipfile
import io
import re

openai.api_key = st.secrets["OPENAI_API_KEY"]
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
st.title("ðŸ“˜ AI Training Content App")

uploaded_file = st.file_uploader("Upload a Markdown-style DOCX from the search app", type=["docx"])

selected_sections = []
all_sections = []

# Extract sections from Markdown-style headings in .docx (### style)
def extract_sections_markdown_headings(doc_path):
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

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_path = tmp_file.name

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

                tips_prompt = (
                    "Generate exactly 5 email tips based on the following training content."
                    " Each tip should include the following structure:\n"
                    "Tip X: [Title]\nBenefit: [Why it's useful]\nSteps:\n1. ...\n2. ...\n3. ..."
                    " Clearly separate each tip using 'Tip X:' and keep the structure consistent."
                )

                tips_response = openai.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        {"role": "system", "content": "You are an instructional content expert."},
                        {"role": "user", "content": f"{tips_prompt}\n\nCONTENT:\n{selected_content}"}
                    ]
                )

                outline_text = outline_response.choices[0].message.content
                script_text = script_response.choices[0].message.content
                tips_text = tips_response.choices[0].message.content

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

                tip_pattern = r"Tip\s+(\d+):\s*(.*?)\s*(?=Tip\s+\d+:|\Z)"
                tip_blocks = re.findall(tip_pattern, tips_text, re.DOTALL)
                tips = [f"Tip {num}:\n{body.strip()}" for num, body in tip_blocks if body.strip()][:5]

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

if st.session_state.get("generated"):
    tabs = st.tabs(["Outline", "Narration", "Email Tips"])

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
st.set_page_config(layout="wide")
st.title(" AI Training Content App (Search + Content + Design Steps)")

# Step 1: Upload and Analyze
st.header("Step 1: Upload and Analyze")
uploaded_files = st.file_uploader("Upload one or more PDF or DOCX files", type=["pdf", "docx"], accept_multiple_files=True)

text_blocks = []

if uploaded_files:
    for file in uploaded_files:
        suffix = os.path.splitext(file.name)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file.read())
            tmp_path = tmp.name

        if suffix == ".docx":
            doc = Document(tmp_path)
            for para in doc.paragraphs:
                if para.text.strip():
                    text_blocks.append(para.text.strip())
        elif suffix == ".pdf":
            from PyPDF2 import PdfReader
            reader = PdfReader(tmp_path)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    lines = text.split("\n")
                    text_blocks.extend([line.strip() for line in lines if line.strip()])

# Step 2: Prompt + Content Creation
st.header("Step 2: Select Content and Generate")

selected_prompt = st.text_input("Ask a question or describe the topic you want to generate content for")
run_type = st.radio("Class Type", ["QuickByte (15 mins)", "FastTrack (30 mins)"])

if selected_prompt and text_blocks:
    with st.spinner("Finding relevant content..."):
        # Split into chunks
        chunks = []
        chunk_size = 800
        chunk = []
        for block in text_blocks:
            chunk.append(block)
            if len("\n".join(chunk)) >= chunk_size:
                chunks.append("\n".join(chunk))
                chunk = []
        if chunk:
            chunks.append("\n".join(chunk))

        relevant_text = []
        for chunk in chunks:
            resp = openai.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You help extract relevant content from training documents."},
                    {"role": "user", "content": f"Find any content related to: {selected_prompt}\n\n{chunk}"}
                ]
            )
            relevant_text.append(resp.choices[0].message.content.strip())

        combined_content = "\n\n".join(relevant_text)

        # Generate outputs
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        class_type = "15-minute QuickByte" if "QuickByte" in run_type else "30-minute FastTrack"

        outline_resp = openai.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are an expert instructional designer."},
                {"role": "user", "content": f"Create a class outline with learning objectives for a {class_type} class based on this content:\n{combined_content}"}
            ]
        )
        outline = outline_resp.choices[0].message.content.strip()

        narration_resp = openai.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are a professional e-learning narrator."},
                {"role": "user", "content": f"Write a professional narration script based on this:\n{combined_content}"}
            ]
        )
        narration = narration_resp.choices[0].message.content.strip()

        tips_resp = openai.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are an instructional content expert."},
                {"role": "user", "content": f"Generate exactly 5 email tips from this training content. Use this format:\nTip X: [Title]\nBenefit: [Why it's useful]\nSteps:\n1. ...\n2. ..."}
            ]
        )
        tips_text = tips_resp.choices[0].message.content.strip()
        tip_pattern = r"Tip\s+(\d+):\s*(.*?)\s*(?=Tip\s+\d+:|\Z)"
        tip_blocks = re.findall(tip_pattern, tips_text, re.DOTALL)
        tips = [f"Tip {num}:\n{body.strip()}" for num, body in tip_blocks if body.strip()][:5]

        # Step 3: Generate Class Design Markdown
        st.header("Step 3: Generate Design Document")
        design_md = f"# Class Design Document\n\n## Title\n{selected_prompt}\n\n## Class Type\n{class_type}\n\n## Outline\n{outline}\n\n## Narration Script\n{narration}\n\n## Email Tips\n"
        for i, tip in enumerate(tips, 1):
            design_md += f"\n### Tip {i}\n{tip}"

        # File outputs
        def save_temp_file(text, filename):
            path = os.path.join(tempfile.gettempdir(), filename)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            return path

        outline_path = save_temp_file(outline, f"outline_{timestamp}.txt")
        narration_path = save_temp_file(narration, f"narration_{timestamp}.txt")
        tips_path = save_temp_file("\n\n".join(tips), f"email_tips_{timestamp}.txt")
        design_path = save_temp_file(design_md, f"class_design_{timestamp}.md")

        tabs = st.tabs(["Outline", "Narration", "Email Tips", "Design Document"])
        with tabs[0]:
            st.download_button("Download Outline", open(outline_path, "rb"), file_name=os.path.basename(outline_path))
            st.markdown(outline)
        with tabs[1]:
            st.download_button("Download Narration Script", open(narration_path, "rb"), file_name=os.path.basename(narration_path))
            st.markdown(narration)
        with tabs[2]:
            st.download_button("Download Email Tips", open(tips_path, "rb"), file_name=os.path.basename(tips_path))
            for i, tip in enumerate(tips):
                st.markdown(f"**Tip {i+1}:**\n{tip}")
        with tabs[3]:
            st.download_button("Download Class Design Markdown", open(design_path, "rb"), file_name=os.path.basename(design_path))
            st.code(design_md, language="markdown")