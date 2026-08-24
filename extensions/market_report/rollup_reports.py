import os
import sys
import argparse
import glob
import re
import json
import asyncio
from datetime import datetime
import pdfplumber
import markdown
from google import genai
from playwright.async_api import async_playwright
import requests
import subprocess
from dotenv import load_dotenv

# Load .env
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "rag_server", ".env")
load_dotenv(env_path)

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Supabase config
SUPABASE_URL = "https://jqzlmzbvaesczarqptye.supabase.co"
SUPABASE_KEY = "sb_publishable_wXUovp36dvd_VwdX-U8ecg_P-OrGwEb"
BACKEND_URL = "https://vonika-git-863156331978.europe-west1.run.app/api"

def get_target_files(rollup_type):
    """
    Tìm kiếm các file PDF sẽ được tổng hợp dựa vào rollup_type.
    """
    files = []
    prefix = ""
    if rollup_type == "weekly":
        prefix = "Báo cáo thị trường ngày"
    elif rollup_type == "monthly":
        prefix = "Báo cáo Tuần"
    elif rollup_type in ["quarterly", "halfyear", "yearly"]:
        # Quý thì gộp Tháng, Nửa năm/Năm thì gộp Quý
        if rollup_type == "quarterly":
            prefix = "Báo cáo Tháng"
        else:
            prefix = "Báo cáo Quý"
            
    all_pdfs = glob.glob(os.path.join(OUTPUT_DIR, f"{prefix} *.pdf"))
    all_pdfs.sort()
    return all_pdfs

def extract_text_from_pdfs(pdf_paths):
    combined_text = ""
    for path in pdf_paths:
        file_name = os.path.basename(path)
        combined_text += f"\n\n--- Trích xuất từ: {file_name} ---\n\n"
        try:
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        combined_text += text + "\n"
        except Exception as e:
            print(f"Lỗi khi đọc file {path}: {e}")
    return combined_text

def get_rollup_title(rollup_type):
    now = datetime.now()
    if rollup_type == "weekly":
        iso_week = now.isocalendar()[1]
        return f"Báo cáo Tuần {iso_week} năm {now.year}"
    elif rollup_type == "monthly":
        # Usually run on 1st of next month, so we take previous month
        month = now.month - 1 if now.month > 1 else 12
        year = now.year if now.month > 1 else now.year - 1
        return f"Báo cáo Tháng {month} năm {year}"
    elif rollup_type == "quarterly":
        # Runs on 1, 4, 7, 10
        q = 1 if now.month == 4 else (2 if now.month == 7 else (3 if now.month == 10 else 4))
        year = now.year if now.month > 1 else now.year - 1
        return f"Báo cáo Quý {q} năm {year}"
    elif rollup_type == "halfyear":
        # Runs on 1, 7
        h = 1 if now.month == 7 else 2
        year = now.year if now.month > 1 else now.year - 1
        return f"Báo cáo Nửa năm {h} năm {year}"
    elif rollup_type == "yearly":
        year = now.year - 1
        return f"Báo cáo Năm {year}"
    return "Báo cáo Tổng hợp"

def generate_markdown_via_ai(combined_text, rollup_type, title):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Lỗi: Không tìm thấy GEMINI_API_KEY trong environment variables.")
        
    client = genai.Client(api_key=api_key)
    
    prompt = f"""Bạn là một chuyên gia phân tích tài chính cấp cao. 
Nhiệm vụ của bạn là tổng hợp các báo cáo thị trường con thành một {title} hoàn chỉnh và sắc sảo.

VĂN PHONG VÀ CẤU TRÚC YÊU CẦU:
- Báo cáo phải được viết bằng ngôn ngữ Markdown.
- Bắt đầu các phần chính bằng đúng cú pháp "## PHẦN X: [Tên phần]".
- Có độ dài vừa phải, tóm lược được những xu hướng chính trong kỳ báo cáo (không sa đà vào biến động chi tiết từng ngày, hãy nhìn bức tranh lớn).
- Phải chia thành các phần sau:
  ## PHẦN 1: BỨC TRANH TOÀN CẢNH KỲ QUA
  ## PHẦN 2: DIỄN BIẾN NHÓM NGÀNH DẪN DẮT
  ## PHẦN 3: ĐỊNH VỊ RỦI RO & KHUYẾN NGHỊ CHIẾN LƯỢC

DỮ LIỆU ĐẦU VÀO:
{combined_text[:50000]}

Bắt đầu viết Báo cáo:
"""
    max_retries = 3
    current_model = "gemini-3.6-flash"
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=current_model,
                contents=prompt
            )
            return response.text
        except Exception as e:
            if "503" in str(e) and attempt < max_retries - 1:
                import time
                sleep_time = 15 * (2 ** attempt)
                print(f"Gemini API 503 Error. Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
            else:
                raise e

async def build_report_pdf(md_text, title, out_pdf):
    html_body = markdown.markdown(md_text, extensions=['tables'])
    
    report_date = datetime.now().strftime('%d/%m/%Y')
    
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                color: #333;
                line-height: 1.6;
                padding: 40px;
                margin: 0;
            }}
            h1 {{ color: #003366; text-align: center; border-bottom: 2px solid #003366; padding-bottom: 10px; text-transform: uppercase; }}
            h2 {{ color: #004080; margin-top: 30px; border-bottom: 1px solid #ddd; padding-bottom: 5px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 15px; page-break-inside: avoid; }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
            th {{ background-color: #f2f2f2; color: #333; font-weight: bold; }}
            li {{ margin-bottom: 8px; }}
            .footer {{ text-align: center; font-size: 10px; color: #888; margin-top: 50px; border-top: 1px solid #eee; padding-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1 style="margin-bottom: 5px;">{title}</h1>
            <p style="text-align: center; color: #666; margin-top: 0;">Ngày xuất báo cáo: {report_date}</p>
        </div>
        {html_body}
        
        <div class="footer">
            Báo cáo được tổng hợp tự động bởi Vonika
        </div>
    </body>
    </html>
    """
    
    temp_html_path = "temp_rollup_report.html"
    with open(temp_html_path, 'w', encoding='utf-8') as f:
        f.write(full_html)
        
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        html_url = f"file:///{os.path.abspath(temp_html_path).replace(chr(92), '/')}"
        await page.goto(html_url, wait_until='networkidle')
        await page.pdf(
            path=out_pdf,
            format='A4',
            margin={"top": "0.75in", "right": "0.75in", "bottom": "0.75in", "left": "0.75in"}
        )
        await browser.close()

    if os.path.exists(temp_html_path):
        os.remove(temp_html_path)

def upload_market_report_to_supabase(pdf_path):
    file_name = os.path.basename(pdf_path)
    unique_file_name = f"market_reports/{int(datetime.now().timestamp() * 1000)}_{file_name.replace(' ', '_')}"
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    
    try:
        with open(pdf_path, 'rb') as f:
            file_bytes = f.read()
        
        upload_url = f"{SUPABASE_URL}/storage/v1/object/chat-files/{unique_file_name}"
        upload_res = requests.post(
            upload_url, 
            headers={**headers, "Content-Type": "application/pdf"}, 
            data=file_bytes
        )
        if not upload_res.ok:
            print("Failed to upload to storage:", upload_res.text)
            return
            
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/chat-files/{unique_file_name}"
        db_url = f"{SUPABASE_URL}/rest/v1/uploaded_files"
        db_res = requests.post(
            db_url,
            headers={**headers, "Content-Type": "application/json", "Prefer": "return=representation"},
            json={"file_name": file_name, "file_url": public_url}
        )
        if not db_res.ok:
            print("Failed to insert DB:", db_res.text)
            return
            
        db_data = db_res.json()
        file_id = db_data[0]['id']
        
        process_res = requests.post(
            f"{BACKEND_URL}/process-file",
            headers={"Content-Type": "application/json"},
            json={"file_id": file_id}
        )
        if not process_res.ok:
            print("Failed to process file on backend:", process_res.text)
    except Exception as e:
        print("Error uploading to Supabase:", str(e))

def delete_source_files(pdf_paths):
    """
    Xóa file từ Git và gọi Supabase API xóa file từ Storage và uploaded_files.
    """
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    for path in pdf_paths:
        file_name = os.path.basename(path)
        print(f"Deleting {file_name}...")
        
        query_url = f"{SUPABASE_URL}/rest/v1/uploaded_files?file_name=eq.{requests.utils.quote(file_name)}&select=id,file_url"
        resp = requests.get(query_url, headers=headers)
        if resp.ok and len(resp.json()) > 0:
            file_data = resp.json()[0]
            file_id = file_data['id']
            file_url = file_data['file_url']
            
            del_db = requests.delete(f"{SUPABASE_URL}/rest/v1/uploaded_files?id=eq.{file_id}", headers=headers)
            
            storage_path = ""
            if "chat-files/" in file_url:
                storage_path = file_url.split("chat-files/")[-1]
            else:
                storage_path = file_url.split("/")[-1]
                
            if storage_path:
                del_storage = requests.delete(
                    f"{SUPABASE_URL}/storage/v1/object/chat-files/{storage_path}", 
                    headers=headers
                )
                
        try:
            subprocess.run(["git", "rm", path], check=True, stdout=subprocess.DEVNULL)
            print(f"Removed {path} from git.")
        except subprocess.CalledProcessError:
            # Nếu git rm thất bại (ví dụ file chưa được commit), ta xóa bằng os.remove
            if os.path.exists(path):
                os.remove(path)
                print(f"Deleted local file {path}.")

def main():
    parser = argparse.ArgumentParser(description="Rolling Report Generator")
    parser.add_argument("--type", choices=["weekly", "monthly", "quarterly", "halfyear", "yearly"], required=True)
    args = parser.parse_args()
    
    rollup_type = args.type
    target_files = get_target_files(rollup_type)
    
    if not target_files:
        print(f"Không có báo cáo nguồn nào để cuộn cho '{rollup_type}'. Thoát.")
        return
        
    print(f"Đang tổng hợp {len(target_files)} báo cáo cho kỳ {rollup_type}...")
    
    # Đọc text từ các file nguồn
    combined_text = extract_text_from_pdfs(target_files)
    if not combined_text.strip():
        print("No text extracted. Exiting.")
        return
        
    title = get_rollup_title(rollup_type)
    md_text = generate_markdown_via_ai(combined_text, rollup_type, title)
    
    out_pdf = f"{title}.pdf"
    print(f"Đang tạo file PDF {out_pdf}...")
    asyncio.run(build_report_pdf(md_text, title, out_pdf))
    upload_market_report_to_supabase(out_pdf)
    
    if rollup_type in ["weekly", "monthly"]:
        delete_source_files(target_files)
        
    with open("NEW_REPORT_FILENAME.txt", "w", encoding='utf-8') as f:
        f.write(out_pdf)

if __name__ == "__main__":
    main()
