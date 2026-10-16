# 🎓 RateUrDegree - PSU Degree Auditor & Bulletin Assistant

RateUrDegree is a production-ready, interactive degree auditing web application built for Penn State University students. It bridges official university curriculum data (via a vector-based RAG engine) with student transcript analysis to provide automated degree audits, custom semester planning, and interactive AI academic advising.

---

## 🚀 Key Features

* **Automated Transcript Auditing:** Ingests unofficial student transcripts (PDF/TXT) to evaluate course completions, cumulative GPA, and Entrance to Major (ETM) milestones.
* **Smart Rank Classification System:** Assigns a dynamic student rank (Z through F scale based on GPA and credit pacing) with an interactive legend popover.
* **Official PSU Bulletin RAG Engine:** Scrapes and caches official program requirements from the Penn State Bulletin using SQLite, embedding text via `gemini-embedding-001` for precise cosine similarity retrieval and inline source citations[cite: 12].
* **Persistent UI & Chat State:** Built with Streamlit session state architecture (`st.session_state`) to ensure the generated audit report and metric cards remain fully visible during interactive chat reruns[cite: 12].
* **Context-Aware AI Advisor:** Combines direct raw audit report ingestion with retrieved bulletin chunks to accurately answer questions regarding course prerequisites, graduation timelines, and rank-up requirements[cite: 12].
* **Graceful API Rate-Limit Handling:** Robust `try/except` management for Gemini API quotas (`429` / `RESOURCE_EXHAUSTED`) to maintain a smooth user experience.

---

## 🛠️ Tech Stack

* **Frontend & UI:** Streamlit (with custom responsive CSS/HTML components)
* **LLM & Embeddings:** Google GenAI SDK (`gemini-2.5-flash`, `gemini-embedding-001`)
* **Data Processing & Parsing:** BeautifulSoup, PyPDF2 / custom transcript extractors
* **Database & Caching:** SQLite, SQLAlchemy
* **Language:** Python[cite: 12]

---

## 📁 Project Structure

```text
RateUrDegree/
│
├── modules/
│   ├── audit_logic.py      # Gemini-powered audit & transcript evaluation engine
│   ├── rag_engine.py       # Bulletin RAG vector store, chunking, and citation mapping
│   └── storage.py          # SQLite bulletin caching layer
│
├── majors.py               # PSU college and major URL mappings
├── utils.py                # Transcript text extraction and web scraper utilities
├── app.py                  # Main Streamlit application entry point & persistent UI
├── requirements.txt        # Project dependencies
└── README.md               # Project documentation