from pydantic import BaseModel
from typing import List, Optional

class ProcessFileRequest(BaseModel):
    file_id: int
    
class ChatRequest(BaseModel):
    query: str
    file_ids: List[int]
    chatId: Optional[int] = None
    model: Optional[str] = "gemini-2.5-flash"
    top_k_chunks: Optional[int] = 50


    
