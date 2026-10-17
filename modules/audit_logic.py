from google import genai
from google.genai.errors import ServerError, APIError
import time

def run_gemini_audit(major_name, bulletin_text, transcript_text, api_key=None):
    client = genai.Client(api_key=api_key) if api_key else genai.Client()
    prompt = f"""
    You are an expert academic advisor at Penn State University. 
    Review the following Student Transcript for {major_name} against the Official Bulletin Source Text below.
    
    OFFICIAL BULLETIN SOURCE TEXT:
    {bulletin_text}
    
    STUDENT TRANSCRIPT:
    {transcript_text}
    
    STRICT REPORT STRUCTURE INSURUCTIONS (DO NOT NUMBER THE HEADINGS):
    1. **Student Rank Determination**:
       - Assign student a rank based on performance relative to academic standing:
         - **Z**: Flawless ~4.0 GPA, ahead of schedule.
         - **S**: 3.8 - 3.99 GPA, elite and on track.
         - **A**: 3.5 - 3.79 GPA, strong progress.
         - **B**: 3.2 - 3.49 GPA, comfortable standing.
         - **C**: 2.8 - 3.19 GPA, meeting basic requirements.
         - **D**: 2.3 - 2.79 GPA, near threshold.
         - **E**: 2.0 - 2.29 GPA, critical risk.
         - **F**: <2.0 GPA, academic warning.
       - Include this exact format line at the very top: **Student Rank: [Z/S/A/B/C/D/E/F]**

    2. **Required Headings and Sections (Strictly unnumbered)**:

       ### Quick Student Metrics
       - **Student Year**: (e.g. Sophomore)
       - **Cumulative GPA**: (e.g. 3.84)
       - **Credits Completed**: (e.g. 31.0)

       ---

       ### ETM Requirements
       - Detail the official Entrance to Major (ETM) courses, grade minimums, and GPA cutoffs for all students in this program.

       ---

       ### Completion Standards
       - Compare student status against ETM and college rules: list criteria Met, In-Progress, or Late/Dropped (LD).

       ---

       ### Course Trajectory & Missing Courses
       - **Classes Taken and Ongoing**: (Itemize completed and current active semester coursework)
       - **Missing Core Courses**: (Itemize required core courses yet to be completed)

       ---

       ### Overall Report & Next Semester Schedule
       - Comprehensive summary and recommended schedule for the upcoming semester with total target credit count.
    """

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return response.text
        except ServerError:
            time.sleep(2 ** attempt)
        except APIError as e:
            if "429" in str(e):
                time.sleep(3 ** attempt)
            else:
                return "⚠️ API Error: Rate limit or request restrictions encountered."
        except Exception as e:
            raise e
            
    return "Error: The model is currently experiencing high server demand. Please try again in a few seconds."