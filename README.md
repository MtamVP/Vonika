# Vonika — AI Chat Assistant with Document RAG

**Vonika** is a full-stack chat application that lets users upload their own documents (PDF, Word, Excel, CSV, JSON, Markdown...) and ask questions grounded in that content. It combines a hand-built hybrid retrieval engine (BM25 + TF-IDF with Reciprocal Rank Fusion) tuned for Vietnamese text with a FastAPI backend and a vanilla JS/Supabase frontend.

I built this to understand retrieval-augmented generation from the ground up — not just call an embeddings API, but implement and tune the ranking logic myself, and see where a lightweight hybrid-search approach holds up (and where it doesn't) compared to pure vector search.

**[Live Demo](https://vonika.pages.dev/)** ·
**[Screenshots below](#screenshots)** ·
**Built by [Vo Phuc Minh Tam (MTamVP)]**

---

## Screenshots
**Giao diện chat**
![Giao diện Chat](assets/chat_layout.png)

**Giao diện tải file**
![Giao diện Upload file](assets/upload_files.png)

**Giao diện Settings**
![Giao diện Settings](assets/settings.png)

**Giao diện chọn file thông minh**
![Giao diện chọn file thông minh](assets/attach_files.png)
---

## Why hybrid search instead of pure embeddings?

Most RAG tutorials reach straight for a vector database. I chose BM25 (exact keyword/term matching) fused with TF-IDF cosine similarity instead, for two reasons:

- **Vietnamese retrieval is sensitive to exact terms** — legal/technical phrasing, names, and numbers often matter more than semantic similarity, and BM25 handles that better out of the box.
- **Cost and hosting constraints** — running on a free-tier host with no GPU ruled out hosting my own embedding model, and I wanted to avoid paying for an embeddings API for this project.

Scores from both algorithms are combined using Reciprocal Rank Fusion (`1 / (60 + rank)`), which is more robust than simple score averaging when the two methods score on different scales.

---

## How it works

1. **Upload** — user uploads a document (or pastes text). Files are parsed based on type (`pandas`/`tabulate` for spreadsheets, `pypdf` for PDFs, `python-docx` for Word, etc.) and converted to plain text.
2. **Chunk** — text is split into ~800-character chunks with `RecursiveCharacterTextSplitter` and stored in Supabase.
3. **Retrieve** — on a query, Vietnamese text is tokenized with `underthesea` and normalized, then scored by BM25 and TF-IDF in parallel; the top results are fused via RRF.
4. **Generate** — the top ~5 chunks are injected into a prompt with conversation history and sent to Gemini, which is instructed to answer strictly from context and suggest follow-up questions.

```
Upload → Parse → Chunk → Store (Supabase)
                              ↓
Query → Tokenize → BM25 ┐
                 → TF-IDF ┴→ RRF fusion → Top-k chunks → Gemini → Answer
```

---

## Key Features and Practical Applications

### Intelligent Document Question Answering
- **Multi-Format Support**: Process various document formats including PDF, DOCX, TXT, JSON, XLSX, CSV, TSV, and MD.
- **Context-Grounded Responses**: Query the system and retrieve answers strictly based on the provided document context, which significantly reduces generative hallucinations.
- **Targeted File Attachment**: Isolate search context by attaching specific documents to individual queries.

### Optimized Retrieval Engine
- **Vietnamese NLP Integration**: Utilize `underthesea` for custom tokenization tailored to Vietnamese text, coupled with a hybrid retrieval pipeline (BM25 and TF-IDF).
- **Reciprocal Rank Fusion (RRF)**: Combine keyword-based exact matching with term frequency scoring to accurately identify and retrieve the most relevant text segments.

### System Extensibility and Automation
- **AI Skills Management**: Dynamically configure the system's reasoning framework by uploading and toggling custom `SKILL.md` instruction sets without altering the underlying codebase.
- **Advanced Model Selection**: Seamlessly switch between multiple language models (e.g., Gemini 3.5 Flash, Gemini 2.5 Flash, Flash-Lite) to optimize for computational efficiency or reasoning depth.
- **Automated Market Reporting**: Utilize scheduled automation workflows (via GitHub Actions) to aggregate data, synthesize periodic reports, and automatically distribute findings to external channels like Discord while synchronizing with the database.

### User Interface and Interaction
- **Persistent Chat History**: Store conversation threads securely with automatically generated and user-editable titles.
- **Responsive Design**: Adapt to different screen sizes with a flexible layout, including theme selection and collapsible navigation sidebars.

---

## Tech Stack

| Layer | Tools |
|---|---|
| Frontend | HTML5, CSS3, vanilla JavaScript (ES6+) |
| Backend | Python, FastAPI, Uvicorn |
| Retrieval | Rank-BM25, scikit-learn (TF-IDF), underthesea (Vietnamese NLP) |
| Generation | Google Gemini API |
| Parsing | pandas, openpyxl, tabulate, pypdf, python-docx |
| Data | Supabase (PostgreSQL + Storage) |
| Hosting | Render (free tier) |

---

## How to Build and Run Locally

### Prerequisites
- Python 3.9+ installed.
- A free [Supabase](https://supabase.com/) account.
- A free [Google Gemini API Key](https://aistudio.google.com/).

### 1. Database Setup (Supabase)
1. Create a new Supabase project.
2. Go to the **SQL Editor** and run the following script to initialize the schema:
   ```sql
   -- Create tables
   CREATE TABLE chat_messages (id SERIAL PRIMARY KEY, role TEXT, content TEXT, chat_title TEXT, created_at TIMESTAMP DEFAULT NOW());
   CREATE TABLE uploaded_files (id SERIAL PRIMARY KEY, file_name TEXT, file_url TEXT, created_at TIMESTAMP DEFAULT NOW());
   CREATE TABLE document (id SERIAL PRIMARY KEY, file_id INTEGER, chunk_index INTEGER, content TEXT);
   ```
3. Go to **Storage** and create a new public bucket named `chat-files`.

### 2. Backend Setup
```bash
# Navigate to the backend directory
cd rag_server

# Create and activate a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY, SUPABASE_URL, and SUPABASE_KEY

# Start the FastAPI server
uvicorn main:app --reload
```
*The API will be available at `http://localhost:8000`.*

### 3. Frontend Setup
Since the frontend uses Vanilla JS, no build step is required!
1. Open `index.html` directly in your browser, or use an extension like **Live Server** in VS Code.
2. Ensure the API endpoint in your JS code points to `http://localhost:8000`.

---

## Database Schema

- `chat_messages` — chat history (`id`, `role`, `content`, `chat_title`, `created_at`)
- `uploaded_files` — file metadata (`id`, `file_name`, `file_url`, `created_at`)
- `document` — chunked text per file (`id`, `file_id`, `chunk_index`, `content`)
- `chat-files` (Storage bucket) — raw uploaded files

---

## Limitations & Next Steps

- No retrieval evaluation yet — next step is a small labeled test set to measure precision/recall of the fused ranking, and compare against a pure-embedding baseline.
- BM25/TF-IDF is fast but won't catch pure semantic matches (paraphrased questions with no shared keywords); worth testing a lightweight embedding model as a third signal.
- Free-tier hosting caps concurrent usage and memory — noted as a constraint, not yet load-tested.

---
