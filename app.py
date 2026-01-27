# ================== ATS RESUME CHECKER (STABLE + INTERACTIVE) ==================

import streamlit as st
import fitz  # PyMuPDF
import json
import re
import time
from google import genai
from google.genai import types



# ------------------ PAGE CONFIG ------------------
st.set_page_config(page_title="ATS Resume Checker", layout="centered")


# ------------------ GLOBAL UI + ANIMATIONS (UNCHANGED) ------------------
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #0f172a, #020617);
    color: #e5e7eb;
}

h1, h2, h3, h4, h5, p, span {
    color: #f8fafc !important;
}

/* ================= FILE UPLOADER ================= */
.stFileUploader {
    background: linear-gradient(135deg, #020617, #020617);
    padding: 20px;
    border-radius: 15px;
    border: 2px dashed #22d3ee;
}

/* Drag & drop main text */
.stFileUploader label div span {
    color: #000000 !important;
    font-size: 16px;
    font-weight: 600;
}

/* Subtext */
.stFileUploader small {
    color: #7dd3fc !important;
    font-size: 13px;
}

/* Browse button */
.stFileUploader button {
    background: linear-gradient(135deg, #22d3ee, #0ea5e9) !important;
    color: #020617 !important;
    font-weight: 700;
    border-radius: 10px;
    border: none;
}

.stFileUploader button:hover {
    background: linear-gradient(135deg, #0ea5e9, #0284c7) !important;
    color: #ffffff !important;
}

/* ================= TABS ================= */
[data-testid="stTabs"] button {
    font-size: 18px;
    color: #cbd5f5 !important;
    font-weight: 600;
}

[data-testid="stTabs"] button[aria-selected="true"] {
    color: #ffffff !important;
    border-bottom: 3px solid #22d3ee;
}

/* ================= CARDS ================= */
.ats-card {
    background: linear-gradient(135deg, #1e293b, #020617);
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 0 30px rgba(0,0,0,0.45);
    animation: fadeUp 0.6s ease-in-out;
}

@keyframes fadeUp {
    from {opacity:0; transform: translateY(15px);}
    to {opacity:1; transform: translateY(0);}
}

/* ================= PROGRESS BAR ================= */
.progress-container {
    background: #020617;
    border-radius: 20px;
    height: 26px;
    width: 100%;
    overflow: hidden;
}

.progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #22c55e, #16a34a);
    width: 0%;
    animation: loadBar 1.4s ease forwards;
}

@keyframes loadBar {
    from {width: 0%;}
    to {width: var(--value);}
}

/* ================= BUTTONS ================= */
.stDownloadButton button,
.stButton button {
    background: linear-gradient(135deg, #2563eb, #1d4ed8);
    color: #ffffff !important;
    font-weight: 600;
    border-radius: 10px;
    padding: 0.6em 1.4em;
    border: none;
}

.stDownloadButton button:hover,
.stButton button:hover {
    background: linear-gradient(135deg, #1d4ed8, #1e40af);
    transform: scale(1.03);
}


</style>
""", unsafe_allow_html=True)

# ------------------ HEADER ------------------
st.title("📄 ATS Resume Checker")
st.caption("Deterministic • Stable • Resume-Friendly")


# ------------------ GEMINI CLIENT ------------------
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("❌ GOOGLE_API_KEY missing in Streamlit secrets")
    st.stop()

client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])


# ------------------ FILE UPLOAD ------------------
uploaded_file = st.file_uploader(
    "📄 Drop your resume here or click Browse  (PDF only)",
    type=["pdf"]
)



# ------------------ TABS ------------------
tabs = st.tabs(["📊 ATS Score", "🛠 Improvements", "📄 Resume Preview"])


# ================== CORE LOGIC ==================
if uploaded_file:

    with st.spinner("📖 Reading resume..."):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")

        full_text = " ".join(
            re.sub(r"\s+", " ", page.get_text()).strip()
            for page in doc
        )

    # ------------------ GEMINI PROMPT (STABLE) ------------------
    prompt = f"""
Act strictly as a Resume Parsing Engine.

Resume Text:
{full_text}

Extract ATS-relevant metrics objectively.
Do NOT calculate any score.
Do NOT estimate quality or tone.

Return ONLY valid JSON:
{{
  "keyword_matches": ["Python", "SQL"],
  "missing_keywords": ["Docker", "AWS"],
  "experience_years": number,
  "strong_action_verbs": number,
  "weak_phrases_count": number,
  "formatting_issues_count": number,
  "red_marker_data": [
    {{"original_text": "EXACT_STRING", "reason": "why", "correction": "FIXED_STRING"}}
  ],
  "yellow_marker_data": [
    {{"original_text": "EXACT_STRING", "reason": "why", "suggestion": "BETTER_STRING", "add_keywords": ["kw1"]}}
  ]
}}
"""

    response = None
    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0,
                    top_k=1,
                    top_p=1,
                    response_mime_type="application/json"
                )
            )
            data = json.loads(response.text)
            break
        except (ServerError, ClientError, json.JSONDecodeError):
            time.sleep(min(2 ** attempt * 5, 60))

    if not response:
        st.error("❌ Gemini failed. Try again later.")
        st.stop()


    # ------------------ ATS SCORE (DETERMINISTIC) ------------------
    def calculate_ats_score(d):
        score = 0
        score += min(len(d["keyword_matches"]) * 4, 40)

        exp = d["experience_years"]
        score += 25 if exp >= 5 else 18 if exp >= 3 else 10 if exp >= 1 else 0

        score += min(d["strong_action_verbs"] * 2, 20)
        score += max(10 - d["formatting_issues_count"] * 2, 0)
        score += max(5 - d["weak_phrases_count"], 0)

        return min(score, 100)

    final_score = calculate_ats_score(data)


    # ------------------ TAB 1: SCORE ------------------
    with tabs[0]:
        st.markdown(f"""
        <div class="ats-card">
            <h3>📊 ATS Compatibility Score</h3>
            <div class="progress-container">
                <div class="progress-bar" style="--value:{final_score}%"></div>
            </div>
            <p style="margin-top:10px;font-size:20px;"><b>{final_score}/100</b></p>
        </div>
        """, unsafe_allow_html=True)


    # ------------------ TAB 2: IMPROVEMENTS ------------------
    with tabs[1]:
        for item in data.get("yellow_marker_data", []):
            st.markdown(
                f"<div class='ats-card'>🟡 <b>{item['original_text']}</b><br>"
                f"💡 {item['suggestion']}<br>"
                f"🧠 Keywords: {', '.join(item['add_keywords'])}</div>",
                unsafe_allow_html=True
            )

        for item in data.get("red_marker_data", []):
            st.markdown(
                f"<div class='ats-card'>🔴 <b>{item['original_text']}</b><br>"
                f"✅ Fix: {item['correction']}</div>",
                unsafe_allow_html=True
            )


    # ------------------ TAB 3: PDF PREVIEW + DOWNLOAD ------------------
    with tabs[2]:
        for page in doc:
            for item in data.get("red_marker_data", []):
                for inst in page.search_for(item["original_text"]):
                    hl = page.add_highlight_annot(inst)
                    hl.set_colors(stroke=(1, 0, 0))
                    hl.update()

            for item in data.get("yellow_marker_data", []):
                for inst in page.search_for(item["original_text"]):
                    hl = page.add_highlight_annot(inst)
                    hl.set_colors(stroke=(1, 0.9, 0.4))
                    hl.update()

        output = "Reviewed_Resume.pdf"
        doc.save(output)

        with open(output, "rb") as f:
            st.download_button("⬇ Download Reviewed Resume", f, file_name=output)

    st.success("🎉 Analysis complete")
