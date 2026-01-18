# ATS Resume Checker

A Streamlit-based ATS resume analysis tool that evaluates resumes using
deterministic logic combined with Gemini AI parsing.

## 🚀 Features
- Upload resume PDF and get ATS score
- Deterministic scoring (no AI score fluctuation)
- Keyword match & missing keyword detection
- Resume formatting and wording analysis
- Highlighted PDF download
- Graceful handling of Gemini API overload

## 🧠 How It Works
1. Resume text is extracted using PyMuPDF
2. Gemini API parses ATS-relevant metrics (no scoring by AI)
3. ATS score is calculated locally using fixed rules
4. Issues and improvements are highlighted directly in the PDF

## 🛠 Tech Stack
- Python
- Streamlit
- Google Gemini API
- PyMuPDF

## 🌐 Deployment
Deployed using **Streamlit Cloud** with secure API key handling via secrets.

## 📌 Future Improvements
- Job description matching
- Resume rewrite suggestions
- Keyword heatmap visualization
