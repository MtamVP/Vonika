# Kế hoạch triển khai True Streaming (Server-Sent Events) cho Vonika RAG

Tài liệu này ghi chú chi tiết cách nâng cấp hệ thống RAG hiện tại từ giao tiếp Synchronous (chờ toàn bộ AI trả lời xong mới gửi 1 cục JSON) sang giao tiếp Real-time Streaming bằng giao thức Server-Sent Events (SSE). Tính năng này sẽ triệt tiêu thời gian chờ (latency) và cho phép render các thẻ `<think>` (chuỗi suy luận của AI thế hệ mới) lên giao diện theo thời gian thực.

---

## 1. Thay đổi Backend (FastAPI - Python)

### A. File `rag_server/llm.py`
Hiện tại hàm `generate_answer` đang gọi API và đợi kết quả (Blocking). Cần tạo một hàm generator mới để yield từng phần tử (chunk) khi AI nhả chữ.

```python
# rag_server/llm.py
import json

def generate_answer_stream(query: str, context_chunks: list[dict], chat_history: list[dict], model_name: str = "gemini-2.5-flash"):
    api_keys = [v for k, v in os.environ.items() if k.startswith("GEMINI_API_KEY")]
    # Logic setup prompt và tính token giữ nguyên...
    
    # Khởi tạo client
    client = genai.Client(api_key=api_keys[0]) 
    # Lưu ý: Streaming khó làm cơ chế fallback luân phiên hơn, nên chọn key tĩnh hoặc random ngay từ đầu.
    
    response_stream = client.models.generate_content_stream(
        model=model_name,
        contents=prompt
    )
    
    for chunk in response_stream:
        # Chuẩn bị dữ liệu để gửi xuống client qua chuẩn SSE
        data = {
            "text": chunk.text
        }
        # Cú pháp của SSE luôn phải bắt đầu bằng 'data: ' và kết thúc bằng 2 dấu xuống dòng
        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
        
    # Gửi một chunk cuối cùng chứa Sources & Tokens để UI hoàn thiện tin nhắn
    final_data = {
        "text": "",
        "sources": ["File A.pdf", "File B.pdf"],
        "tokens": total_tokens,
        "done": True
    }
    yield f"data: {json.dumps(final_data, ensure_ascii=False)}\n\n"
```

### B. File `rag_server/main.py`
Sửa endpoint `/api/chat` để trả về `StreamingResponse` thay vì Dict thông thường.

```python
# rag_server/main.py
from fastapi.responses import StreamingResponse

@app.post("/api/chat")
def chat(req: models.ChatRequest):
    # Setup context, retrieve top chunks...
    
    # Thay vì gọi hàm cũ, ta lấy generator
    generator = llm.generate_answer_stream(req.query, top_chunks, chat_history, req.model)
    
    # Trả về StreamingResponse với MediaType chuẩn của SSE
    return StreamingResponse(generator, media_type="text/event-stream")
```

---

## 2. Thay đổi Frontend (Vanilla JS)

### A. File `app.js` (Hàm `fetchAIResponse` và `sendMessages`)
Việc dùng `await res.json()` sẽ không hoạt động với luồng SSE. Cần dùng `res.body.getReader()` để đọc luồng byte liên tục.

```javascript
// Thay vì fetchAIResponse trả về JSON, ta đọc stream trực tiếp trong sendMessages

async function sendMessages(text) {
    // 1. In tin nhắn user ra màn hình (giữ nguyên)
    // 2. Lưu vào DB (giữ nguyên)
    // 3. Tạo khung tin nhắn AI trống để chuẩn bị hứng dữ liệu
    
    const aiEl = document.createElement("div");
    aiEl.className = "message-ai";
    aiEl.innerHTML = `<div class="content"><div class="markdown-body"></div></div>`;
    chatArea.appendChild(aiEl);
    
    const mdBody = aiEl.querySelector('.markdown-body');
    let fullAnswer = "";

    try {
        const res = await fetch(`${backend_url}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: text, file_ids: fileIds, chatId: currentChatId, model: model })
        });
        
        const reader = res.body.getReader();
        const decoder = new TextDecoder("utf-8");
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            // Decode mảng byte thành chuỗi
            const chunkText = decoder.decode(value, { stream: true });
            
            // Phân tách các event data: {...}
            const lines = chunkText.split('\n');
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const jsonStr = line.substring(6); // bỏ chữ 'data: '
                    try {
                        const data = JSON.parse(jsonStr);
                        
                        if (data.text) {
                            fullAnswer += data.text;
                            // Cập nhật DOM ngay lập tức
                            mdBody.innerHTML = window.marked ? marked.parse(fullAnswer) : fullAnswer;
                            scrollToBottom(false, 0); // Trượt xuống lập tức không độ trễ
                        }
                        
                        if (data.done) {
                            // Xử lý chunk cuối cùng (Vẽ thanh công cụ, đính sources, lưu db)
                            finalizeAIMessage(aiEl, fullAnswer, data.sources, data.tokens);
                            // Cập nhật supabase chat_messages
                        }
                    } catch (e) {
                        console.error("Lỗi parse SSE chunk:", e);
                    }
                }
            }
        }
    } catch (error) {
        console.error("Stream bị đứt ngang", error);
    }
}
```

### B. Hàm `finalizeAIMessage`
Cần tách logic vẽ nút (Copy, Download, Nguồn) ra một hàm riêng để gọi sau khi nhận cờ `done: True` từ Stream.

---

## 3. Quản lý Thẻ `<think>` (Chain of Thought)
Vì dữ liệu được đẩy xuống real-time theo từng ký tự, nếu dùng các mô hình DeepSeek hoặc Gemini 2.0 (tương lai) trả về thẻ `<think>`, văn bản thô sẽ có dạng:
```markdown
<think>
Đang đọc bảng báo cáo tài chính...
Quý 1 lợi nhuận 50 tỷ.
</think>
Dạ, lợi nhuận của Vingroup trong quý 1 là 50 tỷ đồng ạ.
```

**Cách xử lý trên Frontend:**
Trong lúc `fullAnswer` đang được stream về, ta dùng Regex hoặc DOM logic để bóc đoạn text nằm giữa `<think>` và `</think>`, bọc nó vào một thẻ `<div class="think-box">` có màu nền xám, chữ nhỏ đi, nhấp nháy, hoặc cho phép người dùng click để Mở rộng/Thu gọn.

**Ví dụ CSS để UX tốt hơn:**
```css
.think-box {
    background-color: #f1f5f9;
    border-left: 3px solid #cbd5e1;
    color: #64748b;
    padding: 10px;
    font-size: 0.9em;
    font-style: italic;
    border-radius: 4px;
    margin-bottom: 15px;
    /* Có thể làm max-height và scroll để k chiếm diện tích */
}
```

## Tổng kết Lợi Ích Của SSE
1. **Perceived Latency (Thời gian chờ cảm nhận) bằng 0:** Khách hàng thấy AI phản hồi tức thì sau cú click chuột.
2. **Loại bỏ vòng lặp `setInterval` giả lập đánh phím:** Trình duyệt đỡ vất vả hơn, không còn hiện tượng giật lag CPU.
3. **Mở đường cho AI Agent:** Trong tương lai, Agent có thể đẩy status "Đang gọi Google...", "Đang duyệt PDF...", "Đang tính toán..." real-time xuống màn hình y hệt ChatGPT.
