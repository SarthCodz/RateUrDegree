# Inside Audit Trigger Logic in app.py:
from modules.audit_logic import parse_transcript, compute_gpa, rank_from_gpa

if run_button:
    if not active_api_key and not st.session_state.use_sample_transcript:
        st.error("⚠️ Please enter your Gemini API Key in the sidebar above to run the audit.")
    elif not uploaded_file and not st.session_state.use_sample_transcript:
        st.error("Please upload an unofficial transcript or click 'Load Sample CS Transcript'.")
    else:
        with st.spinner("Evaluating student rank & degree audit..."):
            try:
                if st.session_state.use_sample_transcript and not active_api_key:
                    report_text = SAMPLE_PRECOMPUTED_REPORT
                    time.sleep(0.5)
                else:
                    major_url = available_majors.get(selected_major, "")
                    bulletin_url = custom_url if (use_custom_url and custom_url) else major_url

                    transcript_text = SAMPLE_TRANSCRIPT if st.session_state.use_sample_transcript else extract_transcript_text(uploaded_file)
                    
                    # Live integration of pure business logic functions:
                    parsed_courses = parse_transcript(transcript_text)
                    computed_gpa_val = compute_gpa(parsed_courses)
                    computed_rank = rank_from_gpa(computed_gpa_val)

                    bulletin_text = fetch_bulletin_content(bulletin_url)
                    report_text = run_gemini_audit(selected_major, bulletin_text, transcript_text, api_key=active_api_key)
            except ServerError as e:
                st.error("⚠️ **Server Busy:** Google's Gemini servers are currently experiencing high demand (5xx Server Error). Please try again in a few seconds!")
                report_text = None
            except APIError as e:
                if e.code == 429 or "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    st.error("⚠️ **API Quota Exceeded:** Rate limit encountered (429 Too Many Requests). Please check your API usage limits.")
                else:
                    st.error(f"⚠️ **API Error:** {e}")
                report_text = None
            except Exception as e:
                st.error(f"⚠️ **Error during audit execution:** {e}")
                report_text = None

            if report_text:
                log_anonymous_usage(selected_major)
                # ... metric extraction and session state updating ...