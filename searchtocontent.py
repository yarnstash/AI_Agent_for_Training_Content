
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
st.title("ðŸ“˜ Semantic Search to Training Content")

# Step 1: Upload and Search
uploaded_files = st.file_uploader("Upload PDF or Word documents", type=["pdf", "docx"], accept_multiple_files=True)
search_query = st.text_input("What content are you looking for? (e.g., all the information about narratives)")

selected_sections = []
all_sections = []
all_text_blocks = []

def extract_text_from_pdf(pdf_file):
    import fitz
    text_blocks = []
    with fitz.open(pdf_file) as doc:
        for page in doc:
            text = page.get_text("text")
            for line in text.splitlines():
                if line.strip():
                    text_blocks.append(line.strip())
    return text_blocks

def extract_text_from_docx(docx_file):
    doc = Document(docx_file)
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]

if uploaded_files and search_query:
    all_text_blocks.clear()
    for file in uploaded_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp:
            tmp.write(file.read())
            tmp_path = tmp.name
        if file.name.lower().endswith(".pdf"):
            all_text_blocks.extend(extract_text_from_pdf(tmp_path))
        elif file.name.lower().endswith(".docx"):
            all_text_blocks.extend(extract_text_from_docx(tmp_path))

    with st.spinner("Searching documents..."):
        chunk_size = 20
        chunks = ["
".join(all_text_blocks[i:i+chunk_size]) for i in range(0, len(all_text_blocks), chunk_size)]
        relevant_sections = []
        for chunk in chunks:
            try:
                response = openai.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        {"role": "system", "content": "You extract and rewrite user-relevant content from technical files."},
                        {"role": "user", "content": f"Extract any content relevant to the topic: {search_query}

CONTENT:
{chunk}"}
                    ]
                )
                answer = response.choices[0].message.content.strip()
                if answer:
                    relevant_sections.append(answer)
            except Exception as e:
                relevant_sections.append(f"(Error in extraction: {str(e)})")

        full_result = "

".join(relevant_sections)
        st.session_state.search_results = full_result

# Step 2: Convert Search Result to Class Content
if "search_results" in st.session_state and st.session_state.search_results:
    st.markdown("### Step 2: Create Training Content from Search Result")

    run_type = st.session_state.get("run_type", "")
    col1, col2 = st.columns(2)
    if col1.button("Create QuickByte"):
        st.session_state.run_type = "QuickByte"
    if col2.button("Create FastTrack"):
        st.session_state.run_type = "FastTrack"

    if "run_type" in st.session_state and st.session_state.run_type:
        selected_content = st.session_state.search_results
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        with st.spinner("Generating training materials..."):
            outline_response = openai.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You are an expert instructional designer."},
                    {"role": "user", "content": f"Create an outline with learning objectives for a {'15-minute QuickByte' if st.session_state.run_type == 'QuickByte' else '30-minute FastTrack'} class based on this:
{selected_content}"},
                ]
            )

            script_response = openai.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You are a professional e-learning narrator."},
                    {"role": "user", "content": f"Write a narration script for a video based on this content:
{selected_content}"},
                ]
            )

            tips_prompt = (
                "Generate exactly 5 email tips based on the following training content."
                " Each tip should be in this format:
"
                "Tip X: [Title]
Benefit: [Why it's useful]
Steps:
1. ...
2. ...
3. ..."
            )

            tips_response = openai.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You are an instructional content expert."},
                    {"role": "user", "content": f"{tips_prompt}

CONTENT:
{selected_content}"}
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

# Step 3: Display Output
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