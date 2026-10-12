# 🎓 RateUrDegree

An automated full-stack academic auditing and transcript parsing platform built for Penn State students to evaluate curriculum progress, Entrance to Major (ETM) compliance, and long-term degree trajectory.

## 🚀 Key Features
* **Multi-Route Web Scraping:** Uses `BeautifulSoup` to parse official university curriculum bulletins, extracting complex ETM rules, prerequisite trees, and course matrices.
* **Transcript Parsing Pipeline:** Leverages `Gemini 2.5 Flash` via the Google GenAI SDK to ingest unstructured PDF/TXT unofficial transcripts and map course histories into structured records.
* **Performance-Based Academic Ranking:** Implements a custom academic evaluation engine that categorizes student standing relative to credit progression and cumulative GPA.
* **Interactive Streamlit Dashboard:** A production-ready UI featuring real-time credit tracking, GPA metrics, automated prerequisite gap analysis, and semester course trajectory planning.

## 🛠️ Tech Stack
* **Frontend/UI:** Streamlit
* **Scraping & Parsing:** BeautifulSoup, Python Regular Expressions
* **AI Integration:** Google GenAI SDK (Gemini 2.5 Flash)