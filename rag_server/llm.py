import os
from google import genai
from fastapi import HTTPException
def generate_answer(query: str, context_chunks: list[dict], chat_history: list[dict], model_name:str = "gemini-2.5-flash") -> str:
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
            f"---Snippet {i+1} ---\n{chunk['content']}"
            for i, chunk in enumerate(context_chunks)
        ])
        
    history_text = ""
    if chat_history:
        history_text = "--- Chat History ---\n"
        for msg in chat_history:
            role_name = "User" if msg.get('role') == 'user' else "AI"
            history_text += f"{role_name}: {msg.get('content')}\n\n"
    
    prompt = f"""You are a highly intelligent financial and data analysis AI assistant. 
        Answer the user's question based strictly on the provided context below.
        
        CRITICAL RULES FOR READING CONTEXT:
        1. TABLE RECOGNITION: The context contains structured tables formatted as "[Dòng X] Cột A: Giá trị | Cột B: Giá trị". 
           - Treat all items within the same "[Dòng X]" as belonging to a single row.
           - Use these Key-Value pairs to accurately compare data, trace financial metrics, or answer questions about specific entities (e.g., matching a ticker symbol with its corresponding P/E ratio).
        2. OCR TYPO AUTO-CORRECTION: The text was extracted from PDFs and may contain missing spaces (kerning errors) such as "THỊTRƯỜNG", "mứckhiêm", "hệthống". Mentally separate these words into proper Vietnamese before analyzing the meaning.
        3. If the user asks for a table or comparison, synthesize the Key-Value data back into a clean Markdown table in your response.
        
        If the answer cannot be found in the context, clearly state that you do not have enough information. Do not hallucinate or use outside knowledge.
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
    
    import time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            error_str = str(e)
            if attempt < max_retries - 1 and ("503" in error_str or "429" in error_str or "UNAVAILABLE" in error_str):
                time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s
                continue
            raise HTTPException(status_code=502, detail=f"Lỗi từ Google AI (Model '{model_name}'): {error_str}")
        