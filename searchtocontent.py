
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