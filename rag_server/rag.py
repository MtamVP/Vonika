import os
import json
import io
import re
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from functools import lru_cache
from pydantic import BaseModel
from typing import Optional, List
from google import genai
import docx
from pypdf import PdfReader
import csv
from dotenv import load_dotenv
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    from underthesea import word_tokenize
    HAVE_UNDERTHESEA = True
except ImportError:
    HAVE_UNDERTHESEA = False
import supabase_client

load_dotenv(override=True)
app = FastAPI(title="Lightweight RAG Backend", description="Classic BM25 + TF-IDF (CPU Friendly) + Cache Optimized")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

print("[*] Starting Lightweight RAG Server (CPU Only) - Optimized Version...")
class ProcessFileRequest(BaseModel):
    file_id: int

class ChatRequest(BaseModel):
    query: str
    file_ids: List[int]
    chatId: Optional[int] = None
    model: Optional[str] = "gemini-2.5-flash"
    top_k_chunks: Optional[int] = 50
def extract_text(file_bytes: bytes, fileName: str) -> str:
    ext = fileName.lower().split('.')[-1]
    text = ""
    try:
        if ext == 'pdf':
            reader = PdfReader(io.BytesIO(file_bytes))
            text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        elif ext in ['doc', 'docx']:
            doc = docx.Document(io.BytesIO(file_bytes))
            text = "\n".join([para.text for para in doc.paragraphs])
        elif ext == 'csv':
            content = file_bytes.decode("utf-8", errors='ignore')
            reader = csv.reader(io.StringIO(content))
            text = "\n".join([', '.join(row) for row in reader])
        elif ext == 'json':
            content = file_bytes.decode("utf-8", errors='ignore')
            try:
                text = json.dumps(json.loads(content), indent=2, ensure_ascii=False)
            except:
                text = content
        else:
            text = file_bytes.decode('utf-8', errors='ignore')
            
        if not text.strip():
            raise ValueError("No readable text found in file.")
    except Exception as e:
        print(f"Error extracting {fileName}: {e}")
        raise HTTPException(status_code=422, detail=f"Không thể đọc nội dung file {fileName}: {str(e)}")
        
    return text

def chunk_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
    )
    return splitter.split_text(text)
def remove_vietnamese_accents(text: str) -> str:
    s = text.lower()
    s = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', s)
    s = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', s)
    s = re.sub(r'[ìíịỉĩ]', 'i', s)
    s = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', s)
    s = re.sub(r'[ùúụủũưừứựửữ]', 'u', s)
    s = re.sub(r'[ỳýỵỷỹ]', 'y', s)
    s = re.sub(r'đ', 'd', s)
    return s

def tokenize_vietnamese(text: str) -> List[str]:
    clean_text = re.sub(r'[^\w\s]', " ", text).lower()
    if HAVE_UNDERTHESEA:
        try:
            tokens = word_tokenize(clean_text, format="text").split()
            return tokens
        except Exception:
            pass
    return clean_text.split()

@lru_cache(maxsize=5000)
def get_cached_tokens(text: str) -> List[str]:
    tokens = tokenize_vietnamese(text)
    return [remove_vietnamese_accents(t) for t in tokens]

def retrieve_top_chunks(query: str, chunks_data: list[dict], top_k: int = 5) -> list[dict]:
    if not chunks_data:
        return []

    corpus = [chunk['content'] for chunk in chunks_data]
    q_tokens = get_cached_tokens(query)
    corpus_tokens = [get_cached_tokens(doc) for doc in corpus]
    bm25 = BM25Okapi(corpus_tokens)
    bm25_scores = bm25.get_scores(q_tokens)
    bm25_ranks = {
        idx: rank + 1
        for rank, idx in enumerate(np.argsort(bm25_scores)[::-1])
    }
    corpus_joined = [" ".join(tokens) for tokens in corpus_tokens]
    query_joined = " ".join(q_tokens)
    
    try:
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=30000, token_pattern=r"(?u)\b\w+\b")
        tfidf_matrix = vectorizer.fit_transform(corpus_joined)
        q_vec = vectorizer.transform([query_joined])
        cos_sim = cosine_similarity(q_vec, tfidf_matrix)[0]
    except ValueError:
        cos_sim = np.zeros(len(corpus))
        
    tfidf_ranks = {
        idx: rank + 1
        for rank, idx in enumerate(np.argsort(cos_sim)[::-1])
    }
    fused_score = {}
    for idx in range(len(corpus)):
        bm25_r = bm25_ranks.get(idx, 999)
        tfidf_r = tfidf_ranks.get(idx, 999)
        score = (1.0 / (60.0 + bm25_r)) + (1.0 / (60.0 + tfidf_r))
        fused_score[idx] = score
    ranked_indices = [
        idx for idx, _ in sorted(fused_score.items(), key=lambda x: x[1], reverse=True)[:top_k]
    ]
    
    return [chunks_data[i] for i in ranked_indices]
def generate_answer(query: str, context_chunks: list[dict], chat_history: list[dict], model_name: str = "gemini-2.5-flash") -> str:
    if model_name == "no-ai":
        if not context_chunks:
            return "Bạn đang chọn chế độ Không dùng AI. Không tìm thấy tài liệu nào phù hợp."
        return "Chế độ Không dùng AI. Tài liệu thô tìm được:\n\n" + "\n\n".join([f"[{i+1}] {c['content']}" for i, c in enumerate(context_chunks)])

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is missing.")
        
    client = genai.Client(api_key=api_key)
    
    if not context_chunks:
        context_text = "No context documents provided."
    else:
        context_text = "\n\n".join([
            f"--- Snippet {i+1} ---\n{chunk['content']}"
            for i, chunk in enumerate(context_chunks)
        ])
        
    history_text = ""
    if chat_history:
        history_text = "--- Chat History ---\n"
        for msg in chat_history:
            role_name = "User" if msg.get('role') == 'user' else "AI"
            history_text += f"{role_name}: {msg.get('content')}\n\n"
    
    prompt = f"""You are a helpful and highly intelligent AI assistant. 
Answer the user's question based strictly on the provided context below.
If the answer cannot be found in the context, clearly state that you do not have enough information. Do not hallucinate.
Reply in the same language as the user's question (likely Vietnamese).

After providing your answer, you MUST suggest exactly 3 short follow-up questions that the user might want to ask next based on the context. 
Format the suggestions EXACTLY like this at the very end of your response:
---SUGGESTIONS---
1. [Question 1]
2. [Question 2]
3. [Question 3]

{history_text}
Context Documents:
{context_text}

User Question: {query}
Answer:"""

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        return response.text
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Lỗi từ Google AI (Model '{model_name}'): {str(e)}")
@app.post("/api/process-file")
def process_file(req: ProcessFileRequest):
    file_info = supabase_client.get_file_info(req.file_id)
    if not file_info: raise HTTPException(status_code=404, detail="File not found")
        
    file_name = file_info.get("file_name", "")
    file_url = file_info.get("file_url", "")
    storage_path = file_url.split("/")[-1] if file_url else ""
        
    supabase_client.delete_chunks_by_file_id(req.file_id)
    file_bytes = supabase_client.download_file("chat-files", storage_path)
    text = extract_text(file_bytes, file_name)
    text = text.replace('\x00', '').replace('\u0000', '')
    
    chunks = chunk_text(text)
    
    if chunks:
        batch_size = 10
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            rows = [
                {"file_id": req.file_id, "chunk_index": i + j, "content": chunk}
                for j, chunk in enumerate(batch)
            ]
            supabase_client.supabase.table("documents").insert(rows).execute()
        for chunk in chunks:
            get_cached_tokens(chunk)
            
    return {"status": "ok", "chunks": len(chunks)}

@app.post("/api/chat")
def chat(req: ChatRequest):
    chat_history = []
    if req.chatId:
        chat_history = supabase_client.get_chat_history(req.chatId)
        
    all_chunks = supabase_client.get_chunks_by_file_ids(req.file_ids)
    if not all_chunks:
        answer = generate_answer(req.query, [], chat_history, req.model)
        return {"answer": answer, "sources": []}
        
    top_chunks = retrieve_top_chunks(req.query, all_chunks, top_k=req.top_k_chunks)
    answer = generate_answer(req.query, top_chunks, chat_history, req.model)
    
    source_file_ids = list(set([c["file_id"] for c in top_chunks]))
    source_files_info = supabase_client.get_all_files_info(source_file_ids)
    sources = [f["file_name"] for f in source_files_info]
    
    return {"answer": answer, "sources": sources}

