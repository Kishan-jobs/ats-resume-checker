# ================== ATS RESUME CHECKER (STABLE + SAFE | STREAMLIT) ==================

import streamlit as st
import fitz  # PyMuPDF
import json
import re
import time
from google import genai
from google.genai import types
from google.genai.errors import ServerError, ClientError

# ------------------ STREAMLIT CONFIG ------------------
st.set_page_config(page_title="ATS Resume Checker", layout="centered")
st.title("📄 ATS Resume Checker")
st.caption("Deterministic • Stable • Resume-friendly")

# ------------------ LOAD API KEY ------------------
# Add this in Streamlit Cloud → Secrets
API_KEY = st.secrets.get("GOOGLE_API_KEY")

if not API_KEY:
    st.error("API key not found. Please add GOOGLE_API_KEY in Streamlit Secrets.")
    st.stop()

client = genai.Client(api_key=API_KEY)

# ------------------ FILE UPLOAD ------------------
uploaded_file = st.file_uploader("Upload your resume (PDF only)", type=["pdf"])

if uploaded_file:

    with st.spinner("📖 Reading resume..."):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")

        # Normalize text (stability improvement)
        full_text = " ".join(
            re.sub(r'\s+', ' ', page.get_text()).strip()
            for page in doc
        )

    # ------------------ GEMINI PROMPT (NO SCORING) ------------------
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
      "experience_years": 2,
      "strong_action_verbs": 5,
      "weak_phrases_count": 3,
      "formatting_issues_count": 1,

      "red_marker_data": [
        {{"original_text": "EXACT_STRING", "reason": "why", "correction": "FIXED_STRING"}}
      ],
      "yellow_marker_data": [
        {{"original_text": "EXACT_STRING", "reason": "why", "suggestion": "BETTER_STRING", "add_keywords": ["kw1"]}}
      ]
    }}
    """

    # ------------------ CALL GEMINI WITH SAFE RETRIES ------------------
    response = None
    max_retries = 5

    with st.spinner("🤖 Analyzing with ATS engine..."):
        for attempt in range(max_retries):
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
                break

            except (ServerError, ClientError):
                wait_time = min(2 ** attempt * 5, 60)
                time.sleep(wait_time)

    if response is None:
        st.error("❌ Gemini is overloaded. Please try again later.")
        st.stop()

    data = json.loads(response.text)

    # ------------------ DETERMINISTIC ATS SCORING ------------------
    def calculate_ats_score(d):
        score = 0
        score += min(len(d["keyword_matches"]) * 4, 40)

        exp = d["experience_years"]
        if exp >= 5:
            score += 25
        elif exp >= 3:
            score += 18
        elif exp >= 1:
            score += 10

        score += min(d["strong_action_verbs"] * 2, 20)
        score += max(10 - d["formatting_issues_count"] * 2, 0)
        score += max(5 - d["weak_phrases_count"], 0)

        return min(score, 100)

    final_score = calculate_ats_score(data)

    # ------------------ DISPLAY RESULTS ------------------
    st.success(f"✅ ATS Score: {final_score}/100")

    col1, col2 = st.columns(2)
    col1.metric("Matched Keywords", len(data["keyword_matches"]))
    col2.metric("Missing Keywords", len(data["missing_keywords"]))

    # ------------------ APPLY PDF HIGHLIGHTING ------------------
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

    # ------------------ DOWNLOAD REVIEWED RESUME ------------------
    output_name = "Reviewed_Resume.pdf"
    doc.save(output_name)

    with open(output_name, "rb") as f:
        st.download_button(
            label="⬇ Download Highlighted Resume",
            data=f,
            file_name=output_name,
            mime="application/pdf"
        )

    # ------------------ SHOW SUGGESTIONS ------------------
    st.subheader("🟡 Recommended Improvements")
    for item in data.get("yellow_marker_data", []):
        st.markdown(
            f"**{item['original_text']}**  \n"
            f"Suggestion: {item['suggestion']}  \n"
            f"Keywords to add: {', '.join(item['add_keywords'])}"
        )

    st.success("✅ Analysis complete")
