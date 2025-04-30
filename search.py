import streamlit as st
import os
import tempfile
from docx import Document
from PyPDF2 import PdfReader
import openai
from io import BytesIO

openai.api_key = st.secrets["OPENAI_API_KEY"]

st.set_page_config(layout="wide")
st.title("Semantic Document Search & Export")

Upload multiple files

uploaded_files = st.file_uploader("Upload PDF or Word documents", type=["pdf", "docx"], accept_multiple_files=True)

Store document content

documents = []

def extract_text_from_pdf(file): reader = PdfReader(file) text = "\n".join(page.extract_text() or "" for page in reader.pages) return text

def extract_text_from_docx(file): doc = Document(file) text = "\n".join(para.text for para in doc.paragraphs) return text

if uploaded_files: for file in uploaded_files: file_type = file.name.lower() if file_type.endswith(".pdf"): text = extract_text_from_pdf(file) elif file_type.endswith(".docx"): text = extract_text_from_docx(file) else: text = "" documents.append({"filename": file.name, "content": text})

st.success(f"Loaded {len(documents)} document(s)")

user_query = st.text_input("Enter a question or instruction about the content")

if user_query:
    all_content = "\n\n".join(doc["content"] for doc in documents)

    with st.spinner("Searching and generating content..."):
        response = openai.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts and organizes relevant information from uploaded documents."},
                {"role": "user", "content": f"The following is content from multiple documents:\n\n{all_content}\n\nNow respond to this prompt:\n{user_query}"}
            ]
        )
        answer = response.choices[0].message.content
        st.markdown("### Generated Content")
        st.markdown(answer)

        # Export to Word
        doc = Document()
        for line in answer.split("\n"):
            doc.add_paragraph(line)
        output_path = os.path.join(tempfile.gettempdir(), "extracted_response.docx")
        doc.save(output_path)

        with open(output_path, "rb") as f:
            st.download_button("Download as Word Document", f, file_name="search_result.docx")

