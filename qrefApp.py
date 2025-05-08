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
st.title("AI Training Content App QREF")

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
    for uploaded_file in uploaded_files:
        suffix = ".pdf" if uploaded_file.name.endswith(".pdf") else ".docx"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = tmp_file.name

        if suffix == ".pdf":
            extracted_text = extract_text_from_pdf(tmp_path)
        else:
            extracted_text = extract_text_from_docx(tmp_path)

        document_chunks.append((uploaded_file.name, extracted_text))

    st.success("Files uploaded and content extracted.")

    query = st.text_input("What content are you looking for?")
    if query and document_chunks and "search_topics" not in st.session_state:
        with st.spinner("Finding relevant topics..."):
            combined_text = "  ".join([text for _, text in document_chunks])
            user_prompt = f"""From this content:

{combined_text}

What topics are relevant to this query: {query}
"""
            response = openai.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You are a document analyst. Extract a list of specific, self-contained topics based on the query. Format as a numbered or bullet list."},
                    {"role": "user", "content": user_prompt}
                ]
            )
            topics = response.choices[0].message.content
            topic_lines = [line.strip("â€¢-1234567890. ") for line in topics.strip().splitlines() if line.strip()]
            st.session_state.search_topics = topic_lines
            st.session_state.full_text = combined_text

if "search_topics" in st.session_state:
    st.markdown("### Step 2: Choose Topics for Your Class")
    selected = st.multiselect("Pick the topics you'd like to include:", st.session_state.search_topics)
    if selected:
        with st.spinner("Extracting selected content..."):
            selection_prompt = f"""Extract detailed content for these selected topics:

{selected}

From the following documents:

{st.session_state.full_text}
"""
            content_response = openai.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You extract training content from documents."},
                    {"role": "user", "content": selection_prompt}
                ]
            )
            st.session_state.selected_text = content_response.choices[0].message.content
            st.success("Content extracted.")
# === Generate QREF Markdown ===
        selected_topic = ", ".join(selected)
        matched_text = st.session_state.selected_text
        today = datetime.date.today().strftime("%B %d, %Y")

        qref_md = f"""### QREF: {selected_topic}

**Application:** [App Name]  
**Function:** [Function or Module]  
**Audience:** [User Type]  
**Document Version:** {today}

---

#### OVERVIEW  
{matched_text[:300]}...

---

#### STEPS

1. **First Action**  
   [Insert first clear instruction here.]

2. **Next Action**  
   [Insert second instruction.]

---

#### TIPS & NOTES

- [Add any helpful tips or reminders.]

---

#### RELATED FEATURES

- [Mention other relevant QREFs or tools.]
"""

        st.markdown("### QREF Preview")
        st.code(qref_md, language="markdown")

        st.download_button(
            label="Download QREF Markdown",
            data=qref_md,
            file_name=f"QREF_{selected_topic}.md",
            mime="text/markdown"
        )