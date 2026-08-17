import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Lấy thông tin từ file .env
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# table uploaded_files

def get_file_info(file_id: int):
    response = supabase.table("uploaded_files").select("*").eq("id", file_id).execute()
    return response.data[0] if response.data else None

def get_all_files_info(file_ids: list[int]):
    response = supabase.table("uploaded_files").select("*").in_("id", file_ids).execute()
    return response.data if response.data else []   

# table documents

def insert_chunks(file_id: int, chunks: list[str]):
    rows = [
        {"file_id": file_id, "chunk_index":i, "content":chunk}
        for i, chunk in enumerate(chunks)
    ]
    response = supabase.table("documents").insert(rows).execute()
    return response.data

def get_chunks_by_file_ids(file_ids: list[int]):
    response = (
        supabase.table("documents")
        .select("*")
        .in_("file_id", file_ids)
        .order("file_id")
        .order("chunk_index")
        .execute()
    )
    return response.data if response.data else []

def delete_chunks_by_file_id(file_id: int):
    response = (
        supabase.table("documents")
        .delete()
        .eq("file_id", file_id)
        .execute()
    )
    return response.data

# storage

def download_file(bucket: str, storage_path:str):
    return supabase.storage.from_(bucket).download(storage_path)

# chat_messages

def get_chat_history(chat_id: int, limit: int = 10):

    response = (
        supabase.table("chat_messages")
        .select("*")
        .lt("id", chat_id)
        .order("id", desc=True)
        .limit(limit)
        .execute()
    )
    return list(reversed(response.data)) if response.data else []
