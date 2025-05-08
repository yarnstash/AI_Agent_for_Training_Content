import streamlit as st
import os
import tempfile
import datetime
from docx import Document
from PyPDF2 import PdfReader
import re

st.set_page_config(layout="wide")
st.title("ðŸ“„ QREF Markdown Generator (Stage 1)")

# === File upload ===
uploaded_files = st.file_uploader("Upload PDF or DOCX files", accept_multiple_files=True, type=["pdf", "docx"])

# === Extract text from uploaded files ===
def extract_text_from_pdf(file):
    reader = PdfReader(file)
    return "\n".join(page.extract_text() or "" for page in reader.pages)

def extract_text_from_docx(file):
    doc = Document(file)
    return "\n".join(p.text for p in doc.paragraphs)

document_texts = {}
if uploaded_files:
    for file in uploaded_files:
        if file.name.endswith(".pdf"):
            text = extract_text_from_pdf(file)
        elif file.name.endswith(".docx"):
            text = extract_text_from_docx(file)
        else:
            continue
        document_texts[file.name] = text

# === Keyword or topic search ===
search_query = st.text_input("Enter a keyword or topic to search for:")
matched_sections = {}

if search_query and document_texts:
    for filename, text in document_texts.items():
        matches = re.findall(rf"(.{{0,200}}{re.escape(search_query)}.{{0,200}})", text, flags=re.IGNORECASE)
        if matches:
            matched_sections[filename] = "\n---\n".join(matches)

# === Topic selection ===
if matched_sections:
    selected_topic = st.selectbox("Select a matching document to build your QREF:", list(matched_sections.keys()))

    def generate_qref_markdown(topic_title, matched_text):
        today = datetime.date.today().strftime("%B %d, %Y")
        qref_md = f"""### QREF: {topic_title}

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
        return qref_md

    if selected_topic:
        matched_text = matched_sections[selected_topic]
        qref_md = generate_qref_markdown(selected_topic, matched_text)

        st.markdown("### QREF Preview")
        st.code(qref_md, language="markdown")

        st.download_button(
            label="Download QREF Markdown",
            data=qref_md,
            file_name=f"QREF_{selected_topic}.md",
            mime="text/markdown"
        )