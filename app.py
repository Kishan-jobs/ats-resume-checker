# ================== ATS RESUME CHECKER (STABLE + INTERACTIVE) ==================

import streamlit as st
import fitz  # PyMuPDF
import json
import re
import time
import google.generativeai as genai


# ------------------ PAGE CONFIG ------------------
st.set_page_config(page_title="ATS Resume Checker", layout="centered")


# ------------------ GLOBAL UI + ANIMATIONS ------------------
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

.stFileUploader label div span {
    color: #000000 !important;
    font-size: 16px;
    font-weight: 600;
}

.stFileUploader small {
    color: #7dd3fc !important;
    font-size: 13px;
}

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

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")  # stable model


# ------------------ FILE UPLOAD ------------------
uploaded_file = st.file_uploader(
    "📄 Drop your resume here or click Browse  (PDF only)",
    type=["pdf"]
)

# ------------------ TABS ------------------
tabs = st.tabs(["📊 ATS Score", "🛠 Improvements", "📄 Resume Preview"])


# ================== CORE LOGIC ==================
if uploaded_file:

    # ---------- Step 1: Read PDF ----------
    with st.spinner("📖 Reading resume..."):
        try:
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            full_text = " ".join(
                re.sub(r"\s+", " ", page.get_text()).strip()
                for page in doc
            )
        except Exception as e:
            st.error(f"❌ Failed to read PDF: {e}")
            st.stop()

    if not full_text.strip():
        st.error("❌ Could not extract text from this PDF. It may be scanned or image-based.")
        st.stop()

    # ---------- Step 2: Call Gemini ----------
    prompt = f"""
Act strictly as a Resume Parsing Engine.

Resume Text:
{full_text}

Extract ATS-relevant metrics objectively.
Do NOT calculate any score.
Do NOT estimate quality or tone.

Return ONLY valid JSON with no extra text, no markdown, no code fences:
{{
  "keyword_matches": ["Python", "SQL"],
  "missing_keywords": ["Docker", "AWS"],
  "experience_years": 2,
  "strong_action_verbs": 5,
  "weak_phrases_count": 2,
  "formatting_issues_count": 1,
  "red_marker_data": [
    {{"original_text": "EXACT_STRING", "reason": "why", "correction": "FIXED_STRING"}}
  ],
  "yellow_marker_data": [
    {{"original_text": "EXACT_STRING", "reason": "why", "suggestion": "BETTER_STRING", "add_keywords": ["kw1"]}}
  ]
}}
"""

    data = None
    with st.spinner("🤖 Analyzing resume with Gemini..."):
        for attempt in range(3):
            try:
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0,
                        top_p=1,
                    )
                )
                raw = response.text.strip()

                # Strip markdown code fences if Gemini adds them
                raw = re.sub(r"^```(?:json)?", "", raw).strip()
                raw = re.sub(r"```$", "", raw).strip()

                data = json.loads(raw)
                break

            except json.JSONDecodeError as e:
                if attempt == 2:
                    st.error(f"❌ Gemini returned invalid JSON: {e}")
                    st.stop()
                time.sleep(3)

            except Exception as e:
                if attempt == 2:
                    st.error(f"❌ Gemini API error: {e}")
                    st.stop()
                time.sleep(min(2 ** attempt * 3, 30))

    if not data:
        st.error("❌ Failed to get a valid response from Gemini. Please try again.")
        st.stop()

    # ---------- Step 3: ATS Score ----------
    def calculate_ats_score(d):
        score = 0
        score += min(len(d.get("keyword_matches", [])) * 4, 40)

        exp = d.get("experience_years", 0)
        score += 25 if exp >= 5 else 18 if exp >= 3 else 10 if exp >= 1 else 0

        score += min(d.get("strong_action_verbs", 0) * 2, 20)
        score += max(10 - d.get("formatting_issues_count", 0) * 2, 0)
        score += max(5 - d.get("weak_phrases_count", 0), 0)

        return min(score, 100)

    final_score = calculate_ats_score(data)

    # ---------- Tab 1: Score ----------
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

        st.markdown("<div class='ats-card'>", unsafe_allow_html=True)
        st.markdown("**✅ Matched Keywords:**")
        st.write(", ".join(data.get("keyword_matches", [])) or "None found")
        st.markdown("**❌ Missing Keywords:**")
        st.write(", ".join(data.get("missing_keywords", [])) or "None")
        st.markdown("</div>", unsafe_allow_html=True)

    # ---------- Tab 2: Improvements ----------
    with tabs[1]:
        yellow = data.get("yellow_marker_data", [])
        red = data.get("red_marker_data", [])

        if not yellow and not red:
            st.info("✅ No major issues found!")

        for item in yellow:
            st.markdown(
                f"<div class='ats-card'>🟡 <b>{item.get('original_text','')}</b><br>"
                f"💡 {item.get('suggestion','')}<br>"
                f"🧠 Keywords: {', '.join(item.get('add_keywords', []))}</div>",
                unsafe_allow_html=True
            )

        for item in red:
            st.markdown(
                f"<div class='ats-card'>🔴 <b>{item.get('original_text','')}</b><br>"
                f"✅ Fix: {item.get('correction','')}</div>",
                unsafe_allow_html=True
            )

    # ---------- Tab 3: PDF Preview + Download ----------
    with tabs[2]:
        try:
            for page in doc:
                for item in data.get("red_marker_data", []):
                    txt = item.get("original_text", "")
                    if txt:
                        for inst in page.search_for(txt):
                            hl = page.add_highlight_annot(inst)
                            hl.set_colors(stroke=(1, 0, 0))
                            hl.update()

                for item in data.get("yellow_marker_data", []):
                    txt = item.get("original_text", "")
                    if txt:
                        for inst in page.search_for(txt):
                            hl = page.add_highlight_annot(inst)
                            hl.set_colors(stroke=(1, 0.9, 0.4))
                            hl.update()

            output = "/tmp/Reviewed_Resume.pdf"
            doc.save(output)

            with open(output, "rb") as f:
                st.download_button("⬇ Download Reviewed Resume", f, file_name="Reviewed_Resume.pdf")

        except Exception as e:
            st.error(f"❌ Error generating PDF: {e}")

    st.success("🎉 Analysis complete!")
