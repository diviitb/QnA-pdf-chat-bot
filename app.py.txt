import streamlit as st
import fitz
import base64
from io import BytesIO
import random
import google.generativeai as genai

st.set_page_config(page_title="Gemini PDF QA Chatbot", layout="wide")
st.title("🤖 Gemini PDF QA Chatbot")

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("models/gemini-1.5-flash")

if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = []
if "pdf_images" not in st.session_state:
    st.session_state.pdf_images = {}
if "suggested_questions" not in st.session_state:
    st.session_state.suggested_questions = []

with st.sidebar:
    uploaded_pdf = st.file_uploader("📄 Upload your PDF", type="pdf")
    if uploaded_pdf:
        doc = fitz.open(stream=uploaded_pdf.read(), filetype="pdf")
        texts = []
        images = {}

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            texts.append({"page": page_num + 1, "text": text})

            img_list = page.get_images(full=True)
            if img_list:
                xref = img_list[0][0]
                pix = fitz.Pixmap(doc, xref)
                img_bytes = pix.tobytes("png")
                img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                images[page_num + 1] = img_b64

        st.session_state.pdf_text = texts
        st.session_state.pdf_images = images

        st.markdown("### 📑 PDF Preview:")
        st.text(texts[0]["text"][:400] + "..." if texts else "No text extracted.")
        st.success(f"PDF Uploaded: {len(doc)} pages")

query = st.text_input("🔎 Ask a question from the PDF")
if query and st.session_state.pdf_text:
    full_text = "\n\n".join([f"Page {p['page']}: {p['text']}" for p in st.session_state.pdf_text])
    with st.spinner("Thinking with Gemini..."):
        prompt = f"""
        You are a helpful assistant. Use the following PDF content to answer user questions.
        Give relevant answer with the page number if possible. If related image exists, say "Image available".

        PDF Content:
        {full_text}

        Question: {query}
        """
        response = model.generate_content(prompt)
        final_answer = response.text.strip()
        st.markdown("### ✅ Answer:")
        st.write(final_answer)

        # 🔍 Show related image if page is mentioned
        image_shown = False
        for page_num, img_data in st.session_state.pdf_images.items():
            if f"page {page_num}" in final_answer.lower():
                st.image(BytesIO(base64.b64decode(img_data)), caption=f"🖼️ Related image from Page {page_num}")
                image_shown = True
                break
        if not image_shown and len(st.session_state.pdf_images) == 1:
            only_page = list(st.session_state.pdf_images.keys())[0]
            st.image(BytesIO(base64.b64decode(st.session_state.pdf_images[only_page])), caption="🖼️ Image from available page")

        st.markdown("### 🧐 People also ask:")
        suggestions = [
            f"What else is discussed on page {page_num}?",
            "Can you explain this in simpler words?",
            "Is there an example for this?",
            "Any disadvantages?",
        ]
        st.session_state.suggested_questions = random.sample(suggestions, 3)
        for sq in st.session_state.suggested_questions:
            if st.button(sq):
                st.query_params.update(q=sq)
                st.rerun()
