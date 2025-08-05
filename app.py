import streamlit as st
import fitz  # PyMuPDF
import base64
from io import BytesIO
import os
from PIL import Image
import requests
from groq import Groq

# Set App Title and Config
st.set_page_config(page_title="DivAI - PDF Chatbot", layout="wide")
st.title("💬 Hello, I’m DivAI — your PDF Assistant 🤖")
st.markdown("Glad to see you! Upload a PDF and ask me anything about it.")

# Load GROQ API Key
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=GROQ_API_KEY)

# Upload PDF
uploaded_file = st.file_uploader("📄 Upload your PDF", type="pdf")

# Preview first page
if uploaded_file:
    with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
        first_page = doc[0]
        image = first_page.get_pixmap()
        img_bytes = image.tobytes("png")
        st.image(img_bytes, caption="Preview of Page 1", use_column_width=True)

    # Reset file for reading again later
    uploaded_file.seek(0)

    # Ask Question
    user_question = st.text_input("❓ Ask a question from this PDF")

    if user_question:
        with st.spinner("Generating answer..."):
            # Convert entire PDF to text
            pdf_text = ""
            images = []
            page_mapping = []

            with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
                for i, page in enumerate(doc):
                    text = page.get_text()
                    pdf_text += f"\n\n--- Page {i+1} ---\n{text}"

                    for img_index, img in enumerate(page.get_images(full=True)):
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        images.append((i+1, image_bytes))

            # Call Mixtral model via Groq
            prompt = f"""
You are a helpful assistant answering questions based on the given PDF content.

PDF Content:
{pdf_text[:12000]}  # Limit to fit context

User Question: {user_question}

Give:
1. A clear, factual answer.
2. Mention the page number if relevant.
3. Suggest 3 related questions like 'People also ask'.
"""

            response = client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[{"role": "user", "content": prompt}],
            )

            answer = response.choices[0].message.content

            # Display answer
            st.markdown("### 🧠 Answer:")
            st.markdown(answer)

            # Search for related image if any
            related_img = None
            for pg_num, img_bytes in images:
                if str(pg_num) in answer:
                    related_img = (pg_num, img_bytes)
                    break

            if related_img:
                pg, img = related_img
                st.markdown(f"📸 Found related image on **page {pg}**")
                st.image(img, caption=f"Image from page {pg}", use_column_width=True)
            else:
                st.info("No related image found in PDF.")

            # Feedback buttons
            col1, col2 = st.columns(2)
            with col1:
                st.button("👍 Helpful", use_container_width=True)
            with col2:
                st.button("👎 Not useful", use_container_width=True)
