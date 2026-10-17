import re
import os
import time
import streamlit as st
from google import genai
from google.genai.errors import ServerError, APIError
from modules.audit_logic import run_gemini_audit
from modules.storage import init_sqlite_db, log_anonymous_usage
from majors import PSU_MAJORS
from utils import extract_transcript_text, fetch_bulletin_content

st.set_page_config(page_title="RateUrDegree - PSU Degree Auditor", page_icon="🎓", layout="wide")

# --- Initialize SQLite Database & Persistent Session State ---
init_sqlite_db()

if "audit_report" not in st.session_state:
    st.session_state.audit_report = None
if "raw_audit_report" not in st.session_state:
    st.session_state.raw_audit_report = None
if "audit_metrics" not in st.session_state:
    st.session_state.audit_metrics = None
if "use_sample_transcript" not in st.session_state:
    st.session_state.use_sample_transcript = False

SAMPLE_TRANSCRIPT = """
PENN STATE UNIVERSITY UNOFFICIAL TRANSCRIPT
Major: Computer Science (B.S.)
Cumulative GPA: 3.84

COURSES COMPLETED:
MATH 140 - Calculus With Analytic Geometry I: A (4.0)
MATH 141 - Calculus With Analytic Geometry II: A (4.0)
CMPSC 121 - Introduction to Programming Techniques: A (3.0)
CMPSC 122 - Intermediate Programming: A (3.0)
PHYS 211 - General Physics: Mechanics: B+ (4.0)
ENGL 15 - Rhetoric and Composition: A (3.0)
"""

# --- Sidebar Controls ---
with st.sidebar:
    st.header("Audit Configuration")
    
    # --- BYOK (Bring Your Own Key) Setup ---
    st.subheader("🔑 API Key Setup")
    user_api_key = st.text_input(
        "Gemini API Key", 
        type="password", 
        placeholder="AIzaSy...",
        help="Your API key stays secure in your browser session."
    )
    
    st.markdown("🔗 **Don't have a key?** Get a free Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey).")

    is_local = os.path.exists(".streamlit/secrets.toml") or "GEMINI_API_KEY" in os.environ

    if user_api_key:
        active_api_key = user_api_key
    elif is_local:
        active_api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
    else:
        active_api_key = ""

    st.markdown("---")
    colleges = list(PSU_MAJORS.keys())
    selected_college = st.selectbox("Select College", colleges)

    available_majors = PSU_MAJORS.get(selected_college, {})
    selected_major = st.selectbox("Select Major", list(available_majors.keys()))

    use_custom_url = st.checkbox("Use Custom Bulletin URL")
    custom_url = st.text_input("Custom Bulletin URL", placeholder="https://bulletins.psu.edu/...") if use_custom_url else ""

    uploaded_file = st.file_uploader("Upload Unofficial Transcript (PDF/TXT)", type=["pdf", "txt"])
    
    # --- Sample Transcript Quick Demo Button ---
    st.markdown("---")
    st.markdown("**🚀 Quick Demo Mode**")
    if st.button("📄 Load Sample CS Transcript"):
        st.session_state.use_sample_transcript = True
        st.success("Sample CS transcript loaded successfully!")
    
    if st.session_state.use_sample_transcript:
        if st.button("❌ Clear Sample Transcript"):
            st.session_state.use_sample_transcript = False
            st.rerun()

    run_button = st.button("Run Degree Audit", type="primary")

# --- Audit Trigger Logic ---
if run_button:
    if not active_api_key:
        st.error("⚠️ Please enter your Gemini API Key in the sidebar above to run the audit.")
    elif not uploaded_file and not st.session_state.use_sample_transcript:
        st.error("Please upload an unofficial transcript or click 'Load Sample CS Transcript'.")
    else:
        with st.spinner("Evaluating student rank & degree audit..."):
            major_url = available_majors.get(selected_major, "")
            bulletin_url = custom_url if (use_custom_url and custom_url) else major_url

            if st.session_state.use_sample_transcript:
                transcript_text = SAMPLE_TRANSCRIPT
            else:
                transcript_text = extract_transcript_text(uploaded_file)
                
            bulletin_text = fetch_bulletin_content(bulletin_url)

            report_text = run_gemini_audit(selected_major, bulletin_text, transcript_text, api_key=active_api_key)
            log_anonymous_usage(selected_major)

            rank_match = re.search(r"Student Rank:\s*([Z|S|A|B|C|D|E|F])", report_text, re.IGNORECASE)
            rank_letter = rank_match.group(1).upper() if rank_match else "S"

            year_match = re.search(r"Student Year:\s*([^\n]+)", report_text, re.IGNORECASE)
            student_year = year_match.group(1).strip() if year_match else "Sophomore"

            gpa_match = re.search(r"Cumulative GPA:\s*([^\n]+)", report_text, re.IGNORECASE)
            student_gpa = gpa_match.group(1).strip() if gpa_match else "3.84"

            credits_match = re.search(r"Credits Completed:\s*([^\n]+)", report_text, re.IGNORECASE)
            student_credits = credits_match.group(1).strip() if credits_match else "31.0"

            clean_report = re.sub(r"Student Rank:\s*[Z|S|A|B|C|D|E|F]\s*\n?", "", report_text, flags=re.IGNORECASE)
            clean_report = re.sub(r"### Quick Student Metrics.*?(?=\n#|\n---|\Z)", "", clean_report, flags=re.DOTALL | re.IGNORECASE).strip()
            clean_report = re.sub(r"^---+\s*", "", clean_report).strip()

            st.session_state.audit_report = clean_report
            st.session_state.raw_audit_report = report_text
            st.session_state.audit_metrics = {
                "rank_letter": rank_letter,
                "student_year": student_year,
                "student_gpa": student_gpa,
                "student_credits": student_credits,
                "selected_major": selected_major
            }

# --- Main View Rendering ---
if st.session_state.audit_report:
    metrics = st.session_state.audit_metrics
    rank_colors = {"Z": "#FFD700", "S": "#38BDF8", "A": "#A855F7", "B": "#22C55E", "C": "#EAB308", "D": "#F97316", "E": "#EF4444", "F": "#6B7280"}
    theme_color = rank_colors.get(metrics["rank_letter"], "#38BDF8")

    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🎓 RateUrDegree Audit")
        st.caption(f"Official Degree Audit Report: **{metrics['selected_major']}**")
        st.markdown(f"""
            <div style="background: rgba(30, 41, 59, 0.6); border: 1px solid #334155; border-radius: 12px; padding: 14px 20px; display: flex; gap: 32px; align-items: center; margin-top: 6px; margin-bottom: 12px;">
                <div><span style="color: #94A3B8; font-size: 11px; font-weight: 700;">STUDENT YEAR</span><div style="color: #F8FAFC; font-size: 15px; font-weight: 700;">{metrics['student_year']}</div></div>
                <div style="border-left: 1px solid #475569; padding-left: 24px;"><span style="color: #94A3B8; font-size: 11px; font-weight: 700;">CUMULATIVE GPA</span><div style="color: #38BDF8; font-size: 15px; font-weight: 700;">{metrics['student_gpa']}</div></div>
                <div style="border-left: 1px solid #475569; padding-left: 24px;"><span style="color: #94A3B8; font-size: 11px; font-weight: 700;">CREDITS COMPLETED</span><div style="color: #38BDF8; font-size: 15px; font-weight: 700;">{metrics['student_credits']}</div></div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        with st.popover("🏆 Rank Legend"):
            st.markdown("**Ranking Legend:**\n* **Z**: 4.0+ GPA\n* **S**: 3.8-3.99 GPA\n* **A**: 3.5-3.79 GPA\n* **B**: 3.2-3.49 GPA\n* **C**: 2.8-3.19 GPA\n* **D**: 2.3-2.79 GPA\n* **E**: 2.0-2.29 GPA\n* **F**: <2.0 GPA")
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #0F172A, #1E293B); border: 2px solid {theme_color}; border-radius: 12px; padding: 14px 12px 10px 12px; text-align: center;">
                <div style="color: {theme_color}; font-size: 42px; font-weight: 900;">{metrics['rank_letter']}</div>
                <div style="color: #94A3B8; font-size: 11px; font-weight: 700;">RANK</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown(st.session_state.audit_report)
else:
    st.title("🎓 RateUrDegree")
    st.markdown("Verify your degree path instantly using official Penn State Bulletin links and AI-powered transcript auditing.")
    st.info("👈 Configure your major, enter your Gemini API key, and upload your transcript (or click **Load Sample CS Transcript**) in the sidebar to run your audit!")

# --- Persistent Bottom Chat Assistant ---
st.markdown("---")

chat_container = st.container()

with chat_container:
    st.subheader("💬 Bulletin Assistant Chat")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    st.caption("💡 **Quick Questions:**")
    q_col1, q_col2, q_col3 = st.columns(3)
    example_prompt = None

    if q_col1.button("Prereqs for CMPSC 360?", use_container_width=True):
        example_prompt = "What are the prerequisites for CMPSC 360?"
    if q_col2.button("CS ETM Requirements?", use_container_width=True):
        example_prompt = "What are the Entrance-to-Major (ETM) requirements for Computer Science?"
    if q_col3.button("GenEd Recommendations?", use_container_width=True):
        example_prompt = "What General Education requirements are needed for Engineering?"

prompt = example_prompt or st.chat_input("Ask a question about prerequisites, ETM rules, or courses...")

if prompt:
    if not active_api_key:
        st.error("⚠️ Please enter your Gemini API Key in the sidebar to chat with the assistant.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Analyzing bulletin and degree audit..."):
                    from modules.rag_engine import BulletinRAG

                    client = genai.Client(api_key=active_api_key)
                    
                    major_url = available_majors.get(selected_major, "")
                    bulletin_url = custom_url if (use_custom_url and custom_url) else major_url
                    
                    active_bulletin_text = fetch_bulletin_content(bulletin_url)
                    rag = BulletinRAG(client)
                    rag.chunk_bulletin(selected_major, active_bulletin_text)
                    rag.build_vector_store()
                    
                    retrieved_chunks = rag.retrieve_top_k(prompt, k=3)
                    retrieved_bulletin_context = "\n\n".join([
                        f"[{c['program']} | {c['section']}]: {c['text']}" 
                        for c in retrieved_chunks
                    ])
                    
                    rank_legend = """
                    RANK SCALE REFERENCE:
                    - Z Rank: 4.0+ GPA, ahead of schedule
                    - S Rank: 3.8 - 3.99 GPA, elite & on track
                    - A Rank: 3.5 - 3.79 GPA, strong progress
                    - B Rank: 3.2 - 3.49 GPA, comfortable
                    - C Rank: 2.8 - 3.19 GPA, meeting basics
                    - D Rank: 2.3 - 2.79 GPA, near threshold
                    - E Rank: 2.0 - 2.29 GPA, critical risk
                    - F Rank: < 2.0 GPA, warning
                    """

                    full_combined_prompt = f"""
                    You are RateUrDegree's official AI academic advisor and bulletin assistant.
                    Answer the student's question accurately based on their generated degree audit report and the official Penn State Bulletin context below.

                    === STUDENT'S GENERATED DEGREE AUDIT REPORT ===
                    {st.session_state.get('raw_audit_report', 'No audit run yet.')}

                    {rank_legend}

                    === OFFICIAL PSU BULLETIN RETRIEVED CONTEXT ===
                    {retrieved_bulletin_context}

                    User Question: {prompt}
                    """
                    
                    answer = None
                    for attempt in range(3):
                        try:
                            response = client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=full_combined_prompt
                            )
                            answer = response.text
                            break
                        except ServerError:
                            if attempt == 2:
                                answer = "⚠️ **Server Busy:** Google's Gemini servers are currently experiencing high demand (503 Unavailable). Please try asking your question again in a few seconds!"
                            time.sleep(2 ** attempt)
                        except APIError as e:
                            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                                answer = "⚠️ **API Quota Exceeded:** The daily request limit for this Gemini API key has been reached. Please check your Google AI Studio account limit!"
                                break
                            else:
                                answer = f"⚠️ API Error: {e}"
                                break
                        except Exception as e:
                            if "503" in str(e) or "UNAVAILABLE" in str(e):
                                if attempt == 2:
                                    answer = "⚠️ **Server Busy:** Google's Gemini servers are currently experiencing high demand (503 Unavailable). Please try asking your question again in a few seconds!"
                                time.sleep(2 ** attempt)
                            else:
                                answer = f"⚠️ An error occurred while generating the response: {e}"
                                break
                    
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})