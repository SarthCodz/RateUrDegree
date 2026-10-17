import pypdf
import requests
from bs4 import BeautifulSoup
from modules.storage import get_cached_bulletin, set_cached_bulletin

def fetch_bulletin_content(base_url):
    clean_url = base_url.split("#")[0].rstrip("/")
    
    # --- Check SQLite Cache first to save time and network requests ---
    cached_content = get_cached_bulletin(clean_url)
    if cached_content:
        return cached_content

    # Penn State Bulletin sub-routes containing actual course lists and ETM rules
    target_routes = [
        f"{clean_url}/howtogetin/",
        f"{clean_url}/programrequirements/",
        clean_url
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    extracted_blocks = []
    
    for url in target_routes:
        try:
            res = requests.get(url, headers=headers, timeout=8)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                
                # Decompose non-content elements
                for elem in soup(["script", "style", "nav", "footer", "header"]):
                    elem.decompose()
                
                # Extract text preserving structured elements (headings, paragraphs, list items, tables)
                for elem in soup.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'li', 'table']):
                    if elem.name == 'table':
                        for tr in elem.find_all('tr'):
                            cols = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                            if cols:
                                extracted_blocks.append(" | ".join(cols))
                    else:
                        t = elem.get_text(separator=" ", strip=True)
                        if len(t) > 3:
                            extracted_blocks.append(t)
        except Exception:
            continue

    # Deduplicate extracted lines while keeping order
    seen = set()
    unique_lines = []
    for line in extracted_blocks:
        if line not in seen:
            seen.add(line)
            unique_lines.append(line)
            
    full_content = "\n".join(unique_lines)
    
    if len(full_content.strip()) < 200:
        return "Error: Scraped content insufficient."
        
    final_content = full_content[:35000]
    
    # --- Save to SQLite Cache ---
    set_cached_bulletin(clean_url, final_content)
    
    return final_content

def extract_transcript_text(uploaded_file):
    if uploaded_file.name.endswith(".pdf"):
        reader = pypdf.PdfReader(uploaded_file)
        return "\n".join([page.extract_text() or "" for page in reader.pages])
    else:
        return uploaded_file.read().decode("utf-8", errors="ignore")