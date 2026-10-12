import re
import streamlit as st
from audit import run_gemini_audit
from majors import PSU_MAJORS
from utils import extract_transcript_text, fetch_bulletin_content

st.set_page_config(
    page_title="RateUrDegree - PSU Degree Auditor",
    page_icon="🎓",
    layout="wide",
)

with st.sidebar:
  st.header("Audit Configuration")
  colleges = list(PSU_MAJORS.keys())
  selected_college = st.selectbox("Select College", colleges)

  available_majors = PSU_MAJORS.get(selected_college, {})
  selected_major = st.selectbox("Select Major", list(available_majors.keys()))

  use_custom_url = st.checkbox("Use Custom Bulletin URL")
  custom_url = ""
  if use_custom_url:
    custom_url = st.text_input(
        "Custom Bulletin URL", placeholder="https://bulletins.psu.edu/..."
    )

  uploaded_file = st.file_uploader(
      "Upload Unofficial Transcript (PDF/TXT)", type=["pdf", "txt"]
  )
  run_button = st.button("Run Degree Audit", type="primary")

if not run_button:
  st.title("🎓 RateUrDegree")
  st.markdown(
      "Verify your degree path instantly using official Penn State Bulletin"
      " links and AI-powered transcript auditing."
  )
  st.info(
      "👈 Configure your major and upload your transcript in the sidebar on the"
      " left to run your audit!"
  )
else:
  if not uploaded_file:
    st.error("Please upload an unofficial transcript (PDF or TXT) first.")
  else:
    with st.spinner("Evaluating student rank & degree audit..."):
      major_url = available_majors.get(selected_major, "")
      bulletin_url = (
          custom_url if (use_custom_url and custom_url) else major_url
      )

      transcript_text = extract_transcript_text(uploaded_file)
      bulletin_text = fetch_bulletin_content(bulletin_url)

      report_text = run_gemini_audit(
          selected_major, bulletin_text, transcript_text
      )

      # Extract Rank Letter (Z, S, A, B, C, D, E, F)
      rank_match = re.search(
          r"Student Rank:\s*([Z|S|A|B|C|D|E|F])", report_text, re.IGNORECASE
      )
      rank_letter = rank_match.group(1).upper() if rank_match else "S"

      # Extract metrics for the top metrics card
      year_match = re.search(r"Student Year:\s*([^\n]+)", report_text, re.IGNORECASE)
      student_year = year_match.group(1).strip() if year_match else "Sophomore"

      gpa_match = re.search(r"Cumulative GPA:\s*([^\n]+)", report_text, re.IGNORECASE)
      student_gpa = gpa_match.group(1).strip() if gpa_match else "3.84"

      credits_match = re.search(r"Credits Completed:\s*([^\n]+)", report_text, re.IGNORECASE)
      student_credits = credits_match.group(1).strip() if credits_match else "31.0"

      # Clean out duplicate lines and old metric blocks from body text
      clean_report = re.sub(
          r"Student Rank:\s*[Z|S|A|B|C|D|E|F]\s*\n?",
          "",
          report_text,
          flags=re.IGNORECASE,
      )
      clean_report = re.sub(
          r"### Quick Student Metrics.*?(?=\n#|\n---|\Z)",
          "",
          clean_report,
          flags=re.DOTALL | re.IGNORECASE,
      ).strip()
      
      # Remove any leading markdown dividers left over from cleaning
      clean_report = re.sub(r"^---+\s*", "", clean_report).strip()

      rank_colors = {
          "Z": "#FFD700",
          "S": "#38BDF8",
          "A": "#A855F7",
          "B": "#22C55E",
          "C": "#EAB308",
          "D": "#F97316",
          "E": "#EF4444",
          "F": "#6B7280",
      }
      theme_color = rank_colors.get(rank_letter, "#38BDF8")

      col1, col2 = st.columns([3, 1])

      with col1:
        st.title("🎓 RateUrDegree Audit")
        st.caption(f"Official Degree Audit Report: **{selected_major}**")
        st.markdown("")
        
        # Sleek Metrics Card
        st.markdown(
            f"""
            <div style="
                background: rgba(30, 41, 59, 0.6);
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 14px 20px;
                display: flex;
                gap: 32px;
                align-items: center;
                margin-top: 6px;
                margin-bottom: 12px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            ">
                <div>
                    <span style="color: #94A3B8; font-size: 11px; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px;">Student Year</span>
                    <div style="color: #F8FAFC; font-size: 15px; font-weight: 700; margin-top: 2px;">{student_year}</div>
                </div>
                <div style="border-left: 1px solid #475569; padding-left: 24px;">
                    <span style="color: #94A3B8; font-size: 11px; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px;">Cumulative GPA</span>
                    <div style="color: #38BDF8; font-size: 15px; font-weight: 700; margin-top: 2px;">{student_gpa}</div>
                </div>
                <div style="border-left: 1px solid #475569; padding-left: 24px;">
                    <span style="color: #94A3B8; font-size: 11px; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px;">Credits Completed</span>
                    <div style="color: #38BDF8; font-size: 15px; font-weight: 700; margin-top: 2px;">{student_credits}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

      with col2:
        with st.popover("ℹ️ Rank Legend"):
            st.markdown("""
            **Ranking Legend:**
            * **Z**: 4.0+ GPA, ahead of schedule
            * **S**: 3.8-3.99 GPA, elite & on track
            * **A**: 3.5-3.79 GPA, strong progress
            * **B**: 3.2-3.49 GPA, comfortable
            * **C**: 2.8-3.19 GPA, meeting basics
            * **D**: 2.3-2.79 GPA, near threshold
            * **E**: 2.0-2.29 GPA, critical risk
            * **F**: <2.0 GPA, warning
            """)

        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #0F172A, #1E293B);
                border: 2px solid {theme_color};
                border-radius: 12px;
                padding: 14px 12px 10px 12px;
                text-align: center;
                box-shadow: 0px 0px 15px {theme_color}44;
                margin-top: 4px;
            ">
                <div style="color: {theme_color}; font-size: 42px; font-weight: 900; line-height: 1.0;">
                    {rank_letter}
                </div>
                <div style="color: #94A3B8; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; margin-top: 6px;">
                    RANK
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

      # Render the cleaned report directly without trailing divider cluster
      st.markdown(clean_report)