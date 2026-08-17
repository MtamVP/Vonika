# Vonika - AI Chat Assistant Web Interface

## Overview
This project is a web-based chat application designed to interface with an AI assistant. It provides a robust, responsive, and modern user interface for seamless human-AI interaction. The application is built entirely using vanilla web technologies and integrates with Supabase for backend services, including data persistence and file storage. The focus of this project is on delivering a high-quality user experience, maintaining a modular codebase architecture, and providing comprehensive file management capabilities.

## Core Features

### 1. Advanced File Management System
- **Multi-format Support**: Allows uploading various document types including .pdf, .txt, .docx, .json, .xlsx, .csv, .tsv, and .md.
- **Upload Methods**: Supports standard file selection, folder upload, drag-and-drop interactions, and pasting raw text directly into a modal.
- **Attachment Selection**: Users can seamlessly select or deselect specific files to attach as context for the AI prompt. The system accurately tracks selected files using optimized data structures.
- **Batch Operations**: Includes features to select all files and perform batch deletions from both the database and cloud storage.

### 2. Intelligent Chat Interface
- **Message Persistence**: Real-time saving and loading of chat history from the database.
- **Auto-resizing Input**: The chat input area dynamically adjusts its height based on user content for optimal readability.
- **Dynamic Chat Titles**: The application automatically generates chat titles based on the content of the user's initial message. Users can also manually rename the chat title via the interface.

### 3. Modern and Responsive UI/UX
- **Responsive Layout**: Includes collapsible left and right sidebars with drag-to-resize functionality, ensuring usability across different screen sizes.
- **Theming**: Built-in toggle for Light and Dark modes using CSS variables.
- **Accessibility & Polish**: Custom scrollbars, modal overlays, smooth transitions, and careful layout planning to prevent UI overlap.

## AI Backend & RAG System (Vonika Model)
The application leverages a Retrieval-Augmented Generation (RAG) backend built with Python (FastAPI) to process files and answer user queries accurately based on the context of the uploaded documents.

### 1. Document Parsing & Preprocessing
The model supports reading multiple document formats and converting them into plain text for the AI:
- **`xlsx`**: Extracted using `pandas` and converted to highly readable Markdown tables (`tabulate`).
- **`csv` / `tsv`**: Parsed into plain text table-like structures.
- **`pdf`**: Text extraction via `pypdf`.
- **`doc` / `docx`**: Paragraph extraction via `python-docx`.
- **`json`**: Formatted and indented for structured text reading.
- **Plain Text / MD**: Decoded as standard UTF-8.

### 2. Chunking & Storage
Once documents are parsed into massive plain text strings, they are dynamically divided into smaller, contextual chunks (~800 characters) using `RecursiveCharacterTextSplitter`. These text chunks are synchronized and stored in the Supabase `document` table.

### 3. Vietnamese NLP & Hybrid Search (Retrieval)
When a user asks a question, the system queries the database to find the top ~5 most relevant text chunks:
- **Tokenization**: Employs `underthesea` (word_tokenize) combined with custom regex to normalize and clean Vietnamese text (accents stripping).
- **Hybrid Search**: Combines two powerful ranking algorithms:
  - **BM25 (Rank-BM25)**: For exact keyword and term frequency matching.
  - **TF-IDF & Cosine Similarity (Scikit-Learn)**: For n-gram (1-2) vector similarity scoring.
- **Reciprocal Rank Fusion**: Scores from BM25 and TF-IDF are mathematically fused using the reciprocal rank formula `1 / (60 + rank)` to yield the final `fused_score` for the best retrieval performance.

### 4. Generation (LLM)
The retrieved plain text snippets are injected directly into a prompt containing the user's conversation history. The prompt is then passed to Google's **Gemini** (e.g., Gemini 1.5 Flash/Pro), explicitly instructed to formulate an accurate answer strictly based on the context and to suggest follow-up questions.

## Technical Stack
- **Frontend**: HTML5, CSS3 (Vanilla), JavaScript (ES6+)
- **Backend**: Python (FastAPI, Uvicorn)
- **AI / NLP**: Google GenAI SDK, Scikit-Learn, Rank-BM25, Underthesea, Langchain Text Splitters
- **Data Parsing**: Pandas, OpenPyXL, Tabulate, PyPDF, Python-Docx
- **Database & Storage**: Supabase (PostgreSQL Database, Supabase Storage)

## Technical Highlights
- **State Management**: Utilized JavaScript `Map` and `Set` to handle complex state synchronization between the DOM and file selection logic efficiently and without duplication errors.
- **Asynchronous Operations**: Handled database queries, file uploads, and DOM updates using `async/await` to prevent UI blocking and ensure smooth data flow.
- **Event Handling**: Implemented robust event listeners for drag-and-drop file areas, custom keyboard shortcuts (e.g., Enter to save, Shift+Enter for new line), and dynamic element interactions.
- **CSS Architecture**: Structured CSS with global variables for a consistent design system, utilizing Flexbox for complex layout management and media queries for responsiveness.

## Database Schema (Supabase)
The application relies on the following backend structure:
- `chat_messages`: Stores chat history (`id`, `role`, `content`, `chat_title`, `created_at`).
- `uploaded_files`: Stores metadata of uploaded files (`id`, `file_name`, `file_url`, `created_at`).
- `document`: Stores the actual chunked text derived from uploaded files (`id`, `file_id`, `chunk_index`, `content`).
- `chat-files` (Storage Bucket): Securely stores the physical files uploaded by users.
