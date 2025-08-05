import streamlit as st
import fitz  # PyMuPDF
import docx
import openai
from openai import OpenAI
import re

st.set_page_config(page_title="AI Legal Contract Explainer", layout="centered")

st.title("📄 AI Legal Contract Explainer")
st.markdown("Upload a legal contract and get a clear summary of key terms, deadlines, and risks.")

# --- Setup OpenAI Client ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Session State for Usage Limit ---
if "contracts_used" not in st.session_state:
    st.session_state["contracts_used"] = 0

if st.session_state["contracts_used"] >= 3:
    st.warning("🚫 You’ve reached your free contract limit. Upgrade to continue.")
    st.stop()

# --- File Upload ---
uploaded_file = st.file_uploader("Upload your contract (PDF or DOCX)", type=["pdf", "docx"])

def extract_text_from_pdf(file):
    text = ""
    with fitz.open(stream=file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text

def extract_text_from_docx(file):
    text = ""
    doc = docx.Document(file)
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

def analyze_contract_with_gpt(text):
    system_prompt = """You are a legal assistant AI. Your job is to analyze a contract and extract:
    1. Key obligations for each party
    2. Deadlines or time-sensitive clauses
    3. Termination or payment clauses
    4. Any vague, risky, or one-sided language
    
    Return the output in structured markdown like this:
    
    ## 📄 Summary
    ...
    
    ## 📌 Obligations
    - Party A must ...
    - Party B agrees to ...
    
    ## ⏱️ Deadlines
    - Deliverables must be completed by ...
    
    ## ⚠️ Red Flags
    - Clause X is vague because...
    """

    max_chars = 16000
    trimmed_text = text[:max_chars]

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": trimmed_text}
        ],
        temperature=0.3
    )

    return response.choices[0].message.content

def split_sections(text):
    sections = re.split(r'##\s+', text)
    return {s.splitlines()[0]: "\n".join(s.splitlines()[1:]) for s in sections if s.strip()}

if uploaded_file:
    file_ext = uploaded_file.name.split(".")[-1].lower()

    if file_ext == "pdf":
        extracted_text = extract_text_from_pdf(uploaded_file)
    elif file_ext == "docx":
        extracted_text = extract_text_from_docx(uploaded_file)
    else:
        st.error("Unsupported file type.")
        extracted_text = None

    if extracted_text:
        st.success("✅ Text extracted successfully.")
        with st.expander("🔍 View contract text"):
            st.text_area("Contract Text", extracted_text, height=300)

        if st.button("🔍 Explain My Contract with AI"):
            with st.spinner("Analyzing contract with GPT..."):
                explanation = analyze_contract_with_gpt(extracted_text)
                st.session_state["contracts_used"] += 1
                st.success("✅ Analysis complete!")

                # UI Tabs
                sections = split_sections(explanation)
                tab_titles = list(sections.keys())
                tabs = st.tabs(tab_titles)

                for tab, title in zip(tabs, tab_titles):
                    with tab:
                        content = sections[title]
                        if "Red Flag" in title or "⚠️" in title:
                            st.markdown(f":red[{content}]")
                        else:
                            st.markdown(content)
