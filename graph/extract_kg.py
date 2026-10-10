import os
import re
import json
import time
import requests
import pdfplumber
import urllib.parse
from google import genai
from dotenv import load_dotenv
import unicodedata

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "rag_server", ".env")
load_dotenv(env_path)

SUPABASE_URL = "https://jqzlmzbvaesczarqptye.supabase.co"
SUPABASE_KEY = "sb_publishable_wXUovp36dvd_VwdX-U8ecg_P-OrGwEb"
REPORT_BUCKET = "graph_context"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

ALLOWED_LABELS = {
    "Bao gồm", "Sở hữu", "Hành động",
    "Thúc đẩy", "Hưởng lợi", "Tác động tích cực", "Gây áp lực",
    "Tác động tiêu cực", "Làm giảm", "Làm tăng"
}
IMPACT_LABELS = {"Tác động tích cực", "Tác động tiêu cực"}
COMPANY_TYPES = {"TICKER", "COMPANY"}


def get_unparsed_daily_report():
    query_url = f"{SUPABASE_URL}/rest/v1/uploaded_files?category=eq.market_reports&is_graph_parsed=eq.false&select=id,file_name,file_url"
    resp = requests.get(query_url, headers=HEADERS)

    if not resp.ok:
        print("Lỗi lấy danh sách file từ Supabase:", resp.text)
        return None

    data = resp.json()
    daily_reports = [item for item in data if item['file_name'].startswith('Báo cáo thị trường ngày') and item['file_name'].endswith('.pdf')]

    if not daily_reports:
        print("Không tìm thấy báo cáo ngày nào chưa được parse.")
        return None

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
            if t:
                text += t + "\n"
    return text


def report_md_key(file_name):
    m = re.search(r"(\d{2})-(\d{2})-(\d{4})", file_name)
    if m:
        d, mo, y = m.groups()
        return f"BaoCao_{y}-{mo}-{d}.md"
    base = re.sub(r"\.(pdf|md)$", "", file_name, flags=re.IGNORECASE)
    base = base.replace("đ", "d").replace("Đ", "D")
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^A-Za-z0-9]+", "_", base).strip("_")
    return f"{base or 'report'}.md"


def upload_report_to_storage(file_name, text):
    md_key = report_md_key(file_name)
    md_content = f"# {file_name}\n\n{text}"
    md_bytes = md_content.encode("utf-8")

    upload_url = f"{SUPABASE_URL}/storage/v1/object/{REPORT_BUCKET}/{md_key}"
    upload_headers = {
        **HEADERS,
        "Content-Type": "text/markdown; charset=utf-8",
        "x-upsert": "true"
    }
    resp = requests.post(upload_url, headers=upload_headers, data=md_bytes)
    if resp.ok:
        print(f"Đã upload báo cáo lên Storage: {REPORT_BUCKET}/{md_key}")
        return True
    print(f"Lỗi upload Storage: {resp.status_code} {resp.text}")
    return False


def fetch_existing_nodes():
    query_url = f"{SUPABASE_URL}/rest/v1/kg_nodes?select=id,name,aliases,node_type"
    resp = requests.get(query_url, headers=HEADERS)
    if not resp.ok:
        print("Lỗi lấy danh sách nodes từ Supabase:", resp.text)
        return []
    return resp.json()


def normalize_text(s):
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def validate_edges(edges, nodes_by_ref, report_text):
    report_norm = normalize_text(report_text)
    valid, rejected = [], []
    for e in edges:
        errors = []
        if e.get("label") not in ALLOWED_LABELS:
            errors.append(f"label_invalid: {e.get('label')}")

        evidence = re.sub(r"^\[[^\]]+\]\s*", "", e.get("evidence", ""))
        if normalize_text(evidence) not in report_norm:
            errors.append("evidence_not_verbatim")

        target = nodes_by_ref.get(e.get("target"))
        if e.get("label") in IMPACT_LABELS and target and target.get("node_type") not in COMPANY_TYPES:
            errors.append("impact_label_on_non_company")

        if len(e.get("relation", "").split()) > 10:
            errors.append("relation_too_long")

        if errors:
            rejected.append({**e, "errors": errors})
        else:
            valid.append(e)
    return valid, rejected


def extract_kg_from_report(text, existing_nodes):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Không có GEMINI_API_KEY")
        return None

    client = genai.Client(api_key=api_key)

    short_to_uuid = {}
    short_nodes = []
    for idx, node in enumerate(existing_nodes):
        short_id = f"E{idx+1}"
        short_to_uuid[short_id] = node["id"]
        short_nodes.append({
            "id": short_id,
            "name": node["name"],
            "aliases": node.get("aliases", []),
            "node_type": node["node_type"]
        })

    nodes_str = json.dumps(short_nodes, ensure_ascii=False)

    prompt = f"""Bạn là Kỹ sư Dữ liệu Đồ thị tài chính. Nhiệm vụ: Trích xuất Thực thể và Quan hệ thành JSON.

THỰC THỂ ĐÃ CÓ (Dùng id ngắn dạng E1, E2):
{nodes_str}

QUY TẮC THỰC THỂ:
1. Trùng "name"/"aliases" ➡️ Dùng id ngắn có sẵn (vd: E1).
2. Chưa có ➡️ Tạo Node mới với "temp_id" (vd: NEW_1).
3. "node_type" bắt buộc:
   - TICKER: Mã chứng khoán/công ty niêm yết (VD: GMD).
   - COMPANY: Doanh nghiệp chưa niêm yết.
   - MACRO: Yếu tố vĩ mô, giá cả (VD: Giá dầu, Ngành hàng AI). KHÔNG gộp xu hướng vào tên Node (Chỉ ghi "Giá dầu", không ghi "Giá dầu giảm").
   - EVENT: Sự kiện, dự án, hành động (VD: Phạt thuế, Đăng ký mua). KHÔNG gộp chung Sự kiện vào Doanh nghiệp.

QUY TẮC CẠNH (EDGES):
1. "source" và "target": Dùng id ngắn (E1) hoặc temp_id (NEW_1).
   - MẸO CHỐNG SÓT: Phân tích từng câu, liệt kê nhẩm các hành động "mua cổ phiếu", "mở ngành hàng" trước khi tạo cạnh.
2. "label" CHỈ ĐƯỢC CHỌN 1 TRONG CÁC NHÃN:
   - "Bao gồm", "Sở hữu", "Hành động"
     * QUY CHUẨN MẸ/CON: BẮT BUỘC dùng nhãn "Sở hữu" với mũi tên từ [Công ty mẹ] ➔ [Công ty con]. Không dùng nhãn Công ty mẹ/con.
   - "Thúc đẩy", "Hưởng lợi", "Tác động tích cực", "Gây áp lực", "Tác động tiêu cực", "Làm giảm", "Làm tăng"
     * TỐT/XẤU: "Tác động tiêu cực/Tích cực" CHỈ dùng khi target là TICKER hoặc COMPANY. Nếu target là MACRO, phải dùng "Làm tăng/Làm giảm/Thúc đẩy".
     * LOẠI CẠNH YẾU: Bỏ qua nếu evidence chỉ là tiêu đề, nhận định chung chung, không có cơ chế hay số liệu cụ thể.
3. "relation": Ngắn gọn (max 8 từ).
   - Chỉ dùng từ có trong evidence, KHÔNG tự thêm tính từ đánh giá (như kỷ lục, nghiêm trọng...).
   - Nếu có từ "dự kiến"/"kỳ vọng" trong văn bản, BẮT BUỘC thêm chữ "Dự kiến"/"Kỳ vọng" vào đầu relation.
4. "evidence": SAO CHÉP NGUYÊN VĂN 1 câu chứng minh trực tiếp từ báo cáo.
   - Nếu khuyết chủ ngữ, hãy dùng ngoặc vuông để bổ sung: VD "[FMC] ghi nhận sản lượng đi lùi...". KHÔNG viết lại nguyên câu.
5. Chỉ trích cạnh trực tiếp.

JSON FORMAT BẮT BUỘC:
{{
  "new_nodes": [{{"temp_id": "NEW_1", "name": "Lãi suất Fed", "node_type": "MACRO", "aliases": []}}],
  "edges": [{{"source": "E1", "target": "NEW_1", "label": "Làm giảm", "relation": "Kỳ vọng duy trì mặt bằng", "evidence": "Lạm phát cao khiến Fed tiếp tục duy trì mặt bằng lãi suất..."}}]
}}

BÁO CÁO:
{text[:40000]}
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
                    contents=prompt,
                    config={"response_mime_type": "application/json"}
                )
                result_text = response.text
                success = True
                break
            except Exception as e:
                err_str = str(e)
                print(f"Lỗi khi gọi {model_name}: {err_str}")
                if "503" in err_str or "429" in err_str or "UNAVAILABLE" in err_str:
                    time.sleep(2 ** attempt)
                else:
                    break
        if success:
            break

    if not result_text:
        raise Exception("Tất cả các model đều thất bại hoặc quá tải.")
    if "```json" in result_text:
        result_text = result_text.split("```json")[1].split("```")[0].strip()
    elif "```" in result_text:
        result_text = result_text.split("```")[1].split("```")[0].strip()

    try:
        data = json.loads(result_text)

        if "edges" in data:
            for edge in data["edges"]:
                if edge["source"] in short_to_uuid:
                    edge["source"] = short_to_uuid[edge["source"]]
                if edge["target"] in short_to_uuid:
                    edge["target"] = short_to_uuid[edge["target"]]

        nodes_by_ref = {n["id"]: n for n in existing_nodes}
        if "new_nodes" in data:
            for n in data["new_nodes"]:
                nodes_by_ref[n["temp_id"]] = n

        valid_edges, rejected_edges = validate_edges(data.get("edges", []), nodes_by_ref, text)
        if rejected_edges:
            print(f"Cảnh báo: Bỏ qua {len(rejected_edges)} cạnh không hợp lệ:")
            for r in rejected_edges:
                print(f" - Lỗi: {r.get('errors')} => Quan hệ: {r.get('relation')} ({r.get('evidence')})")

        data["edges"] = valid_edges
        return data
    except Exception as e:
        print("Lỗi parse JSON trả về:", e)
        print("Raw response:", result_text)
        return None


def save_to_supabase(data, file_name):
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

    try:
        print("Trích xuất text từ PDF...")
        text = extract_text(pdf_path)

        print("Upload bản .md lên Storage...")
        if not upload_report_to_storage(report_info['file_name'], text):
            print("Dừng lại vì upload .md thất bại, file chưa được đánh dấu là đã parse.")
            return

        print("Lấy existing nodes từ DB...")
        nodes = fetch_existing_nodes()

        print("Gọi Gemini để parse KG JSON...")
        kg_data = extract_kg_from_report(text, nodes)

        if kg_data:
            print("Lưu vào Supabase kg_nodes & kg_edges...")
            save_to_supabase(kg_data, report_info['file_name'])
            mark_file_as_parsed(report_info['id'])
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

if __name__ == "__main__":
    main() 