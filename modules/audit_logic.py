import re
import math
from google import genai
from google.genai.errors import ServerError, APIError
import time

class AuditParsingError(Exception):
    """Raised when transcript parsing or OCR fails."""
    pass

def parse_transcript(transcript_text: str) -> list:
    """
    Parses transcript text into a list of course dicts:
    [{"code": "MATH 140", "credits": 4.0, "grade": "A"}, ...]
    Applies grade forgiveness: if a course is repeated, only the latest grade counts.
    """
    if not transcript_text or not transcript_text.strip():
        raise AuditParsingError("Transcript text is empty or invalid.")
    
    lines = transcript_text.strip().split("\n")
    courses_dict = {}
    
    pattern = re.compile(r"([A-Z]+\s*\d+[A-Z]*)\s*[-:]\s*(.*?)\s*[-:]\s*([\d\.]+)\s*[-:]\s*([A-Za-z][+\-]?)")
    
    for line in lines:
        match = pattern.search(line)
        if match:
            code = match.group(1).strip()
            title = match.group(2).strip()
            credits = float(match.group(3))
            grade = match.group(4).upper()
            courses_dict[code] = {"code": code, "title": title, "credits": credits, "grade": grade}
            
    if not courses_dict:
        simple_pattern = re.compile(r"([A-Z]+\s*\d+[A-Z]*)\s+([A-Za-z][+\-]?)\s+([\d\.]+)")
        for line in lines:
            smatch = simple_pattern.search(line)
            if smatch:
                code = smatch.group(1).strip()
                grade = smatch.group(2).upper()
                credits = float(smatch.group(3))
                courses_dict[code] = {"code": code, "title": "", "credits": credits, "grade": grade}
                
    if not courses_dict:
        raise AuditParsingError("No valid course entries found in transcript.")
        
    return list(courses_dict.values())

def compute_gpa(courses: list) -> float:
    """Computes cumulative GPA, excluding TR, W, P, S grades."""
    grade_points = {
        'A': 4.0, 'A-': 3.7,
        'B+': 3.3, 'B': 3.0, 'B-': 2.7,
        'C+': 2.3, 'C': 2.0,
        'D': 1.0, 'F': 0.0
    }
    
    total_points = 0.0
    total_gpa_credits = 0.0
    
    for c in courses:
        grade = c.get("grade", "").upper()
        credits = c.get("credits", 0.0)
        
        if grade in ['TR', 'W', 'P', 'S'] or grade not in grade_points:
            continue
            
        total_points += grade_points[grade] * credits
        total_gpa_credits += credits
        
    if total_gpa_credits == 0.0:
        return 0.00
        
    return round(total_points / total_gpa_credits, 2)

def rank_from_gpa(gpa: float) -> str:
    """Determines student rank category based on official app thresholds."""
    if gpa >= 4.00:
        return "Z"
    elif gpa >= 3.80:
        return "S"
    elif gpa >= 3.50:
        return "A"
    elif gpa >= 3.20:
        return "B"
    elif gpa >= 2.80:
        return "C"
    elif gpa >= 2.30:
        return "D"
    elif gpa >= 2.00:
        return "E"
    else:
        return "F"

def build_prompt(major_name: str, bulletin_text: str, transcript_text: str) -> str:
    """Constructs the prompt containing major name, bulletin text, and transcript text."""
    return f"""
    Review student transcript for {major_name} against bulletin below.
    Bulletin: {bulletin_text}
    Transcript: {transcript_text}
    """

def extract_rank(response_text: str) -> str:
    """Extracts rank from LLM response text, handling missing formats gracefully."""
    match = re.search(r"\*\*Student Rank:\s*\[([ZSABCDEFZ])\]\*\*", response_text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return "UNKNOWN"

def run_gemini_audit(major_name: str, bulletin_text: str, transcript_text: str, api_key: str = None) -> str:
    """Executes audit with Gemini client, incorporating local GPA/credit calculation and retry logic."""
    if not api_key:
        raise ValueError("Missing API key: Client cannot be constructed.")
        
    client = genai.Client(api_key=api_key)
    prompt = build_prompt(major_name, bulletin_text, transcript_text)

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return response.text
        except ServerError as e:
            if attempt == 2:
                raise e
            time.sleep(2 ** attempt)
        except APIError as e:
            if e.code == 429:
                return "API Error: Rate limit encountered."
            raise e
        except Exception as e:
            raise e
            
    return "Error: The model is currently experiencing high server demand. Please try again in a few seconds."