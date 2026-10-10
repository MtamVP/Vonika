import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
import supabase_client
from dotenv import load_dotenv
import models
import parser
import retrieval
import llm
load_dotenv(override=True)

app = FastAPI(title="RAG Backend", description="Classical ways")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

REPORT_BUCKET = "graph_context"
MAX_REPORT_CHARS = 60000
_report_cache = {}


def load_report_text(source_file_name):
    md_name = re.sub(r"\.pdf$", ".md", source_file_name, flags=re.IGNORECASE)
    if md_name in _report_cache:
        return _report_cache[md_name]
    try:
        data = supabase_client.download_file(REPORT_BUCKET, md_name)
    except Exception as e:
        print(f"Không tải được {REPORT_BUCKET}/{md_name}: {e}")
        return None
    if not data:
        return None
    text = data.decode("utf-8", errors="ignore") if isinstance(data, (bytes, bytearray)) else str(data)
    text = text[:MAX_REPORT_CHARS]
    _report_cache[md_name] = text
    return text


def build_report_context(source_files):
    parts = []
    for name in dict.fromkeys(source_files or []):
        text = load_report_text(name)
        if text:
            parts.append(f"=== {name} ===\n{text}")
    return "\n\n".join(parts)


@app.post("/api/process-file")
def process_file(req: models.ProcessFileRequest):
    file_info = supabase_client.get_file_info(req.file_id)
    if not file_info: raise HTTPException(status_code=404, detail="File not found")
    
    file_name = file_info.get("file_name", "")
    file_url = file_info.get("file_url", "")
    if file_url and "chat-files/" in file_url:
        storage_path = file_url.split("chat-files/")[-1]
    else:
        storage_path = file_url.split("/")[-1] if file_url else ""
    
    supabase_client.delete_chunks_by_file_id(req.file_id)
    file_bytes = supabase_client.download_file("chat-files", storage_path)
    
    text = parser.extract_text(file_bytes, file_name)
    
    text = text.replace('\x00','').replace('\u0000','')
    
    chunks = parser.chunk_text(text)
    
    if chunks:
        batch_size = 10
        for i in range(0,len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            rows = [
                {"file_id": req.file_id, "chunk_index": i + j, "content": chunk}
                for j, chunk in enumerate(batch)
            ]
            supabase_client.supabase.table("documents").insert(rows).execute()
    
    return {"status": "ok", "chunks": len(chunks)}

@app.post("/api/chat")
def chat(req: models.ChatRequest):
    chat_history = []
    if req.chatId:
        chat_history = supabase_client.get_chat_history(req.chatId)
    all_chunks = supabase_client.get_chunks_by_file_ids(req.file_ids)
    if not all_chunks:
        answer, tokens = llm.generate_answer(req.query, [], chat_history, req.model)
        return {"answer": answer, "sources": [], "tokens": tokens}
    
    MAX_SMART_CHUNKS = 150
    if len(all_chunks) <= MAX_SMART_CHUNKS:
        top_chunks = sorted(all_chunks, key=lambda x: (x.get('file_id', 0), x.get('chunk_index', 0)))
    else:
        top_chunks = retrieval.retrieve_top_chunks(req.query, all_chunks, top=MAX_SMART_CHUNKS)
        top_chunks = sorted(top_chunks, key=lambda x: (x.get('file_id', 0), x.get('chunk_index', 0)))
        
    answer, tokens = llm.generate_answer(req.query, top_chunks, chat_history, req.model)
    
    source_file_ids = list(set([c["file_id"] for c in top_chunks]))
    source_files_info = supabase_client.get_all_files_info(source_file_ids)
    sources = [f["file_name"] for f in source_files_info]
    
    return {"answer": answer, "sources": sources, "tokens": tokens}

@app.post("/api/graph-chat")
def graph_chat(req: models.GraphChatRequest):
    chat_history = []
    if req.chatId:
        chat_history = supabase_client.get_chat_history(req.chatId, source='graph')
        
    prompt = f"Bạn là Vonika, một trợ lý AI phân tích Đồ thị Tri thức. Người dùng hỏi: {req.query}\n"
    if req.context:
        prompt += f"\nNgữ cảnh Đính kèm từ Graph:\n{req.context}\n"

    report_context = build_report_context(req.source_files)
    if report_context:
        prompt += (
            "\nNội dung đầy đủ của báo cáo gốc (ưu tiên dùng để trả lời, "
            "chỉ nêu thông tin có trong báo cáo hoặc ngữ cảnh ở trên):\n"
            f"{report_context}\n"
        )
    
    answer, tokens = llm.generate_answer(prompt, [], chat_history, req.model)
    return {"answer": answer, "tokens": tokens}

import requests
import os
from fastapi import APIRouter

@app.get("/api/search")
def web_search(q: str):
    api_key = os.getenv("SERPER_API_KEY")
    url = f"https://google.serper.dev/search?q={q}"
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    response = requests.get(url, headers=headers)
    return response.json()

from fastapi import Response

@app.get("/api/jina")
def jina_search(q: str):
    api_key = os.getenv("JINA_API_KEY")
    url = f"https://r.jina.ai/{q}"
    headers = {
        'Authorization': f'Bearer {api_key}'
    }
    response = requests.get(url, headers=headers)
    return Response(content=response.text, media_type="text/plain")

@app.post("/api/trigger-github-action")
def trigger_github_action():
    github_pat = os.getenv("GITHUB_PAT")
    if not github_pat:
        raise HTTPException(status_code=500, detail="GITHUB_PAT not configured on server")
    
    url = "https://api.github.com/repos/MtamVP/Vonika/actions/workflows/market_report.yml/dispatches"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {github_pat}",
        "Content-Type": "application/json"
    }
    payload = {"ref": "main"}
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code in (200, 204):
            return {"status": "success", "message": "Action triggered successfully"}
        else:
            raise HTTPException(status_code=response.status_code, detail=f"GitHub API Error: {response.text}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))