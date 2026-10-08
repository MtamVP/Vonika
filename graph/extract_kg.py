import os
import sys
import json
import time
import requests
import pdfplumber
import urllib.parse
from datetime import datetime
from google import genai
from dotenv import load_dotenv

# Setup env
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "rag_server", ".env")
load_dotenv(env_path)

SUPABASE_URL = "https://jqzlmzbvaesczarqptye.supabase.co"
SUPABASE_KEY = "sb_publishable_wXUovp36dvd_VwdX-U8ecg_P-OrGwEb"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def get_unparsed_daily_report():
    """Tìm báo cáo ngày mới nhất chưa được parse (is_graph_parsed=FALSE)"""
    query_url = f"{SUPABASE_URL}/rest/v1/uploaded_files?category=eq.market_reports&is_graph_parsed=eq.false&select=id,file_name,file_url"
    resp = requests.get(query_url, headers=HEADERS)
    
    if not resp.ok:
        print("Lỗi lấy danh sách file từ Supabase:", resp.text)
        return None
        
    data = resp.json()
    # Chỉ lấy các báo cáo ngày
    daily_reports = [item for item in data if item['file_name'].startswith('Báo cáo thị trường ngày') and item['file_name'].endswith('.pdf')]
    
    if not daily_reports:
        print("Không tìm thấy báo cáo ngày nào chưa được parse.")
        return None
        
    # Lấy file mới nhất
    daily_reports.sort(key=lambda x: x['file_name'], reverse=True)
    return daily_reports[0]

def download_file(file_url, file_name):
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_name)
    r = requests.get(file_url, headers=HEADERS)
    if r.ok:
        with open(local_path, 'wb') as f:
            f.write(r.content)
        return local_path
    return None

def extract_text(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t: text += t + "\n"
    return text

def fetch_existing_nodes():
    """Lấy danh sách các node hiện có từ Supabase kg_nodes"""
    query_url = f"{SUPABASE_URL}/rest/v1/kg_nodes?select=id,name,aliases,node_type"
    resp = requests.get(query_url, headers=HEADERS)
    if not resp.ok:
        print("Lỗi lấy danh sách nodes từ Supabase:", resp.text)
        return []
    return resp.json()

def extract_kg_from_report(text, existing_nodes):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Không có GEMINI_API_KEY")
        return None
        
    client = genai.Client(api_key=api_key)
    
    nodes_str = json.dumps(existing_nodes, ensure_ascii=False)
    
    prompt = f"""Bạn là Kỹ sư Dữ liệu Đồ thị tài chính. 
Nhiệm vụ: Trích xuất Thực thể và Quan hệ thành JSON.

THỰC THỂ ĐÃ CÓ TRONG HỆ THỐNG (EXISTING ENTITIES) (id là UUID):
{nodes_str}

QUY TẮC THỰC THỂ:
1. Trùng "name" hoặc "aliases" ➡️ Dùng UUID có sẵn trong trường "id". KHÔNG tạo Node mới.
2. Chưa có ➡️ Tạo Node mới với "temp_id" (NEW_1, NEW_2).
3. "node_type" bắt buộc: TICKER, MACRO, EVENT, COMPANY. Tên phải chuẩn hóa (VD: Lạm phát Mỹ).

QUY TẮC CẠNH (EDGES):
1. "source" và "target": Dùng UUID (nếu node đã có) hoặc temp_id (nếu node mới).
2. "label" CHỈ CHỌN 1 trong các nhãn:
   - Tích cực: Tác động tích cực, Hưởng lợi, Thúc đẩy
   - Tiêu cực: Tác động tiêu cực, Gây áp lực
   - Cấu trúc: Bao gồm, Công ty mẹ
3. "relation": Rất ngắn gọn, tối đa 8 từ (VD: "Tăng chi phí vay", "Thu hẹp biên lợi nhuận").
4. "evidence": SAO CHÉP NGUYÊN VĂN 1-2 câu từ báo cáo. KHÔNG TỰ VIẾT LẠI. Nếu không có câu phù hợp, BỎ QUA cạnh này.
5. Chỉ trích cạnh TRỰC TIẾP (A tác động B).

ĐỊNH DẠNG JSON BẮT BUỘC (Trả về nguyên chuỗi JSON có thể parse được, không bọc trong markdown tick):
{{
  "new_nodes": [
    {{"temp_id": "NEW_1", "name": "Lãi suất Fed", "node_type": "MACRO", "aliases": ["Fed Rate"]}}
  ],
  "edges": [
    {{"source": "uuid-cua-node-cu", "target": "NEW_1", "label": "Gây áp lực", "relation": "Buộc duy trì mặt bằng lãi suất", "evidence": "Lạm phát cao khiến Fed tiếp tục duy trì mặt bằng lãi suất..."}}
  ]
}}

BÁO CÁO:
{text[:50000]}
"""

    models = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.5-flash", "gemini-2.5-flash"]
    max_retries = 3
    result_text = None
    
    for model_name in models:
        success = False
        for attempt in range(max_retries):
            try:
                print(f"Đang gọi Gemini model {model_name} (Thử lần {attempt+1}/{max_retries})...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                result_text = response.text
                success = True
                break
            except Exception as e:
                err_str = str(e)
                print(f"Lỗi khi gọi {model_name}: {err_str}")
                if "503" in err_str or "429" in err_str or "UNAVAILABLE" in err_str:
                    time.sleep(2 ** attempt)  # Exponential backoff 1s, 2s, 4s
                else:
                    break # Lỗi khác không phải do nghẽn, skip model này luôn
        if success:
            break
            
    if not result_text:
        raise Exception("Tất cả các model đều thất bại hoặc quá tải.")
    if "```json" in result_text:
        result_text = result_text.split("```json")[1].split("```")[0].strip()
    elif "```" in result_text:
        result_text = result_text.split("```")[1].split("```")[0].strip()
        
    try:
        return json.loads(result_text)
    except Exception as e:
        print("Lỗi parse JSON trả về:", e)
        print("Raw response:", result_text)
        return None

def save_to_supabase(data, file_name):
    # 1. Insert new nodes
    temp_id_to_uuid = {}
    if "new_nodes" in data and data["new_nodes"]:
        for node in data["new_nodes"]:
            payload = {
                "name": node["name"],
                "node_type": node["node_type"],
                "aliases": node.get("aliases", [])
            }
            headers_with_prefer = {**HEADERS, "Prefer": "return=representation"}
            res = requests.post(f"{SUPABASE_URL}/rest/v1/kg_nodes", headers=headers_with_prefer, json=payload)
            
            if res.ok:
                inserted = res.json()
                if len(inserted) > 0:
                    temp_id_to_uuid[node["temp_id"]] = inserted[0]["id"]
            else:
                print(f"Lỗi insert node {node['name']}:", res.text)
                
    # 2. Insert edges
    if "edges" in data and data["edges"]:
        edges_payload = []
        for edge in data["edges"]:
            source_id = temp_id_to_uuid.get(edge["source"], edge["source"])
            target_id = temp_id_to_uuid.get(edge["target"], edge["target"])
            
            edges_payload.append({
                "source_node_id": source_id,
                "target_node_id": target_id,
                "label": edge.get("label", ""), 
                "relation": edge.get("relation", ""),
                "evidence": edge.get("evidence", ""),
                "source_files": [file_name]
            })
            
        if edges_payload:
            res = requests.post(f"{SUPABASE_URL}/rest/v1/kg_edges", headers=HEADERS, json=edges_payload)
            if not res.ok:
                print("Lỗi insert edges:", res.text)
            else:
                print(f"Đã lưu thành công {len(edges_payload)} edges.")

def mark_file_as_parsed(file_id):
    res = requests.patch(
        f"{SUPABASE_URL}/rest/v1/uploaded_files?id=eq.{file_id}",
        headers=HEADERS,
        json={"is_graph_parsed": True}
    )
    if not res.ok:
        print("Lỗi update is_graph_parsed:", res.text)
    else:
        print("Đã đánh dấu file là is_graph_parsed = TRUE.")

def main():
    report_info = get_unparsed_daily_report()
    if not report_info:
        return
        
    pdf_path = download_file(report_info['file_url'], report_info['file_name'])
    if not pdf_path:
        return
        
    print("Trích xuất text từ PDF...")
    text = extract_text(pdf_path)
    
    print("Lấy existing nodes từ DB...")
    nodes = fetch_existing_nodes()
    
    print("Gọi Gemini để parse KG JSON...")
    kg_data = extract_kg_from_report(text, nodes)
    
    if kg_data:
        print("Lưu vào Supabase kg_nodes & kg_edges...")
        save_to_supabase(kg_data, report_info['file_name'])
        mark_file_as_parsed(report_info['id'])
    
    if os.path.exists(pdf_path):
        os.remove(pdf_path)

if __name__ == "__main__":
    main()
