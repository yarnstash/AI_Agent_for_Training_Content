import streamlit as st
import os
import tempfile
import datetime
from docx import Document
from PyPDF2 import PdfReader
import openai
import re
import zipfile
import io
from io import BytesIO

openai.api_key = st.secrets["OPENAI_API_KEY"]

st.set_page_config(layout="wide")
st.title("AI Document Analyzer and Training Content Generator")

tabs = st.tabs(["1. Search Documents", "2. Generate Training Content"])

# --- Shared state ---
st.session_state.setdefault("search_docx_path", None)

# --- Tab 1: Semantic Search ---
with tabs[0]:
    st.header("Step 1: Upload and Search Documents")
    uploaded_files = st.file_uploader("Upload PDF or DOCX files", type=["pdf", "docx"], accept_multiple_files=True)
    documents = []

    def extract_text_from_pdf(file):
        reader = PdfReader(file)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    def extract_text_from_docx(file):
        doc = Document(file)
        return "\n".join(p.text for p in doc.paragraphs)

    if uploaded_files:
        for file in uploaded_files:
            if file.name.endswith(".pdf"):
                text = extract_text_from_pdf(file)
            elif file.name.endswith(".docx"):
                text = extract_text_from_docx(file)
            else:
                continue
            documents.append(text)
        st.success(f"Loaded {len(documents)} documents.")

    search_prompt = st.text_input("Enter your query to extract relevant content:")

    if st.button("Run Search") and search_prompt and documents:
        all_text = "\n\n".join(documents)
        query = (
            "Extract content from the following documents in response to the prompt."
            " Format the result with section headings using Markdown-style '### Heading':\n"
            f"Prompt: {search_prompt}\n\nDocuments:\n{all_text}"
        )

        with st.spinner("Searching and extracting content..."):
            response = openai.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You extract relevant content from documents and structure it with Markdown headings."},
                    {"role": "user", "content": query}
                ]
            )
            result = response.choices[0].message.content

            st.markdown("### Search Result Preview")
            st.markdown(result)

            doc = Document()
            for line in result.split("\n"):
                doc.add_paragraph(line)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            doc_path = os.path.join(tempfile.gettempdir(), f"search_output_{timestamp}.docx")
            doc.save(doc_path)
            st.session_state.search_docx_path = doc_path

            with open(doc_path, "rb") as f:
                st.download_button("Download Extracted Content as DOCX", f, file_name="search_result.docx")

# --- Tab 2: Training Content ---
with tabs[1]:
    st.header("Step 2: Generate Training Content")
    parsed_sections = []

    def extract_sections(doc_path):
        doc = Document(doc_path)
        text_blocks = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
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

    if st.session_state.search_docx_path:
        parsed_sections = extract_sections(st.session_state.search_docx_path)
        section_titles = [f"{i+1}. {title}" for i, (title, _) in enumerate(parsed_sections)]
        selected = st.multiselect("Select sections to include", section_titles)

        if selected:
            selected_indices = [int(s.split(".")[0]) - 1 for s in selected]
            content_input = "\n\n".join(parsed_sections[i][1] for i in selected_indices)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

            if st.button("Generate Training Content"):
                with st.spinner("Generating outline, script, and tips..."):
                    outline = openai.chat.completions.create(
                        model="gpt-4.1-mini",
                        messages=[
                            {"role": "system", "content": "Create a class outline with learning objectives."},
                            {"role": "user", "content": f"Write an outline for a 15-minute class based on this:\n{content_input}"}
                        ]
                    ).choices[0].message.content

                    script = openai.chat.completions.create(
                        model="gpt-4.1-mini",
                        messages=[
                            {"role": "system", "content": "Create a narration script."},
                            {"role": "user", "content": f"Write a narration script for the selected training content:\n{content_input}"}
                        ]
                    ).choices[0].message.content

                    tips_prompt = (
                        "Generate 5 email tips from the following content."
                        " Each should include a title, benefit, and 3 steps. Use this format:\n"
                        "Tip X: [Title]\nBenefit: ...\nSteps:\n1. ...\n2. ...\n3. ..."
                    )
                    tips = openai.chat.completions.create(
                        model="gpt-4.1-mini",
                        messages=[
                            {"role": "system", "content": "Instructional content expert"},
                            {"role": "user", "content": f"{tips_prompt}\n\nCONTENT:\n{content_input}"}
                        ]
                    ).choices[0].message.content

                def create_doc(text, name):
                    doc = Document()
                    for line in text.split("\n"):
                        doc.add_paragraph(line.strip())
                    path = os.path.join(tempfile.gettempdir(), name)
                    doc.save(path)
                    return path

                outline_path = create_doc(outline, f"outline_{timestamp}.docx")
                script_path = create_doc(script, f"script_{timestamp}.docx")
                tips_path = create_doc(tips, f"email_tips_{timestamp}.docx")

                with open(outline_path, "rb") as f:
                    st.download_button("Download Outline", f, file_name=os.path.basename(outline_path))
                with open(script_path, "rb") as f:
                    st.download_button("Download Script", f, file_name=os.path.basename(script_path))
                with open(tips_path, "rb") as f:
                    st.download_button("Download Email Tips", f, file_name=os.path.basename(tips_path))
