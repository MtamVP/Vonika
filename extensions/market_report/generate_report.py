import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import base64
import asyncio
import pandas as pd
import matplotlib.pyplot as plt
import markdown
from datetime import datetime
from google import genai
from playwright.async_api import async_playwright
from dotenv import load_dotenv
import glob
import requests

# Load .env file from rag_server directory
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "rag_server", ".env")
load_dotenv(env_path)

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Segoe UI', 'Arial', 'DejaVu Sans', 'sans-serif']

def _draw_single_investor_chart(df_filtered, title, output_path):
    df_grouped = df_filtered.groupby(['StockSymbol', 'TradeDirection'])['NetTradingValue'].sum().reset_index()
    
    df_buy = df_grouped[df_grouped['TradeDirection'] == 'Mua ròng'].copy()
    df_sell = df_grouped[df_grouped['TradeDirection'] == 'Bán ròng'].copy()
    
    top_buy = df_buy.nlargest(5, 'NetTradingValue')
    top_sell = df_sell.nlargest(5, 'NetTradingValue')
    top_sell['NetTradingValue'] = -top_sell['NetTradingValue']
    
    df_plot = pd.concat([top_buy, top_sell]).sort_values(by='NetTradingValue', ascending=False)
    
    plt.figure(figsize=(10, 6))
    colors = ['#2ca02c' if val > 0 else '#d62728' for val in df_plot['NetTradingValue']]
    bars = plt.bar(df_plot['StockSymbol'], df_plot['NetTradingValue'], color=colors)
    
    for bar in bars:
        yval = bar.get_height()
        offset = abs(yval) * 0.05
        plt.text(bar.get_x() + bar.get_width()/2, yval + offset if yval >= 0 else yval - offset,
                 f'{abs(yval):.1f}', ha='center', va='bottom' if yval >= 0 else 'top', fontsize=9)
    
    plt.title(title, fontsize=14, pad=20)
    plt.axhline(0, color='black', linewidth=1)
    plt.ylabel('Giá trị (Tỷ VNĐ)')
    plt.xlabel('Cổ phiếu')
    plt.tight_layout()
    plt.savefig(output_path, format='png', dpi=150)
    plt.close()

def create_foreign_chart(csv_path, output_path):
    df = pd.read_csv(csv_path)
    df_foreign = df[df['InvestorType'] == 'Nhà đầu tư nước ngoài']
    _draw_single_investor_chart(df_foreign, 'Top Giao dịch ròng - Khối Ngoại (Tỷ VNĐ)', output_path)

def create_proprietary_chart(csv_path, output_path):
    df = pd.read_csv(csv_path)
    df_prop = df[df['InvestorType'] == 'Tự doanh']
    _draw_single_investor_chart(df_prop, 'Top Giao dịch ròng - Tự Doanh (Tỷ VNĐ)', output_path)

def create_index_chart(json_path, output_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    indices = data.get('Tổng quan thị trường', [])
    if not indices:
        return
        
    df = pd.DataFrame(indices)
    required_cols = ['Chỉ số', '1D (%)', '1M (%)', '1Y (%)']
    if not all(col in df.columns for col in required_cols):
        return
        
    df_plot = df[required_cols].dropna()
    for col in required_cols[1:]:
        df_plot[col] = pd.to_numeric(df_plot[col].astype(str).str.replace('%', '').str.strip(), errors='coerce')
        
    df_plot = df_plot.dropna()
    df_plot = df_plot.set_index('Chỉ số')
    
    ax = df_plot.plot(kind='bar', figsize=(11, 6), color=['#1f77b4', '#ff7f0e', '#2ca02c'])
    plt.title('Hiệu suất Chỉ số khu vực (1 Ngày, 1 Tháng, 1 Năm)', fontsize=14, pad=20)
    plt.ylabel('Hiệu suất (%)')
    plt.xlabel('Thị trường')
    plt.axhline(0, color='black', linewidth=1)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_path, format='png', dpi=150)
    plt.close()

def generate_markdown_via_ai(text_json_path, data_json_path):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Lỗi: Không tìm thấy GEMINI_API_KEY trong environment variables.")
        
    client = genai.Client(api_key=api_key)
    
    with open(text_json_path, 'r', encoding='utf-8') as f:
        text_data = json.load(f)
    with open(data_json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    prompt = f"""Bạn là một chuyên gia phân tích tài chính cấp cao. Dưới đây là dữ liệu báo cáo thị trường chứng khoán được trích xuất.
    Hãy đọc các dữ liệu này và viết ra một bản Báo cáo Thị trường Chứng khoán hoàn chỉnh. 

VĂN PHONG VÀ CẤU TRÚC YÊU CẦU:
- Báo cáo phải được viết bằng ngôn ngữ Markdown (sử dụng thẻ ##, ###, **bold**,...).
- Bắt đầu các phần chính bằng đúng cú pháp "## PHẦN X: [Tên phần]". Ví dụ: "## PHẦN 1: TỔNG QUAN & BẢNG SỐ LIỆU THỊ TRƯỜNG"
- Có độ dài vừa phải, súc tích, văn phong chuyên nghiệp và sắc sảo.
- BẮT BUỘC PHẢI CHIA THÀNH ĐÚNG 5 PHẦN theo cấu trúc sau:

## PHẦN 1: TỔNG QUAN & BẢNG SỐ LIỆU THỊ TRƯỜNG
Trình bày dữ liệu từ phần "Tổng quan thị trường", "Định giá thị trường" dưới dạng Markdown Table đẹp. (Gồm Bảng 1 - Biến động chỉ số, Bảng 2 - Định giá khu vực).

## PHẦN 2: BỨC TRANH TOÀN CẢNH & CỘI NGUỒN DÒNG TIỀN
Dựa vào text_data (các đoạn văn bản Nhận định thị trường) để viết lại mạch lạc. Phân tích nguyên nhân cốt lõi chi phối dòng tiền, tổng kết giá trị giao dịch, hành vi mua bán ròng của khối ngoại và tự doanh.

## PHẦN 3: ĐỘNG LỰC NHÓM NGÀNH & ĐIỂM SÁNG DOANH NGHIỆP
Phân tích các nhóm ngành nổi bật (như Tiêu dùng, Ngân hàng, Chứng khoán...) và một số cổ phiếu đáng chú ý dựa trên dữ liệu giao dịch ròng hoặc thông tin bài viết. Đánh giá CƠ HỘI hoặc RỦI RO hoặc THEO DÕI cho từng nhóm.

## PHẦN 4: ĐỊNH VỊ RỦI RO & KHUNG CHIẾN LƯỢC QUẢN TRỊ
Đánh giá sức mạnh kỹ thuật (dựa trên text_data phần Phân tích kỹ thuật nếu có). Đưa ra Kịch bản Cơ sở (Xác suất 70%) và Kịch bản Rủi ro (Xác suất 30%). Cuối cùng đưa ra Khuyến nghị chiến lược quản trị rủi ro, phân bổ tỷ trọng.

## PHẦN 5: TÓM GỌN TIN TỨC VÀ TÁC ĐỘNG NGOẠI BIÊN
Tóm tắt các tin tức vĩ mô thế giới, tin doanh nghiệp trong nước có trong text_data. Ghi rõ đánh giá tác động: TRUNG TÍNH, CƠ HỘI, hoặc RỦI RO cho mỗi tin.

DỮ LIỆU ĐẦU VÀO:
=== TEXT DATA ===
{json.dumps(text_data, ensure_ascii=False, indent=2)}

=== JSON DATA ===
{json.dumps(json_data, ensure_ascii=False, indent=2)}

Lưu ý: Không dùng markdown code block bao quanh kết quả trả về, chỉ cần trả về text markdown trực tiếp. Đảm bảo dùng đúng tiền tố "## PHẦN 1", "## PHẦN 2", v.v... để hệ thống nhận diện.
Bắt đầu viết Báo cáo:
"""
    max_retries = 5
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
                # Exponential backoff: 20s, 40s, 80s...
                sleep_time = 20 * (2 ** attempt)
                print(f"Gemini API 503 Error (High demand). Retrying in {sleep_time}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(sleep_time)
                # Fallback to a lighter model after 2 failed attempts
                if attempt == 1:
                    print("Falling back to gemini-2.5-flash due to prolonged high demand.")
                    current_model = "gemini-2.5-flash"
            else:
                raise e

def get_base64_image(image_path):
    if not os.path.exists(image_path):
        return ""
    with open(image_path, "rb") as img_file:
        encoded = base64.b64encode(img_file.read()).decode('utf-8')
        return f"data:image/png;base64,{encoded}"

def inject_charts_to_html(html_content, chart1_path, chart1b_path, chart2_path):
    img1_tag = f'<div style="text-align: center; margin: 20px 0;"><img src="{get_base64_image(chart1_path)}" style="max-width: 100%; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"></div>' if os.path.exists(chart1_path) else ''
    img1b_tag = f'<div style="text-align: center; margin: 20px 0;"><img src="{get_base64_image(chart1b_path)}" style="max-width: 100%; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"></div>' if os.path.exists(chart1b_path) else ''
    img2_tag = f'<div style="text-align: center; margin: 20px 0;"><img src="{get_base64_image(chart2_path)}" style="max-width: 100%; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"></div>' if os.path.exists(chart2_path) else ''

    if '<h2>PHẦN 1' in html_content:
        parts = html_content.split('<h2>PHẦN 2')
        if len(parts) == 2:
            html_content = parts[0] + img2_tag + '<h2>PHẦN 2' + parts[1]
    
    if '<h2>PHẦN 2' in html_content:
        parts = html_content.split('<h2>PHẦN 3')
        if len(parts) == 2:
            html_content = parts[0] + img1_tag + img1b_tag + '<h2>PHẦN 3' + parts[1]
            
    return html_content

async def build_report_pdf(text_json, data_json, vietstock_csv, out_pdf):
    chart1 = "temp_chart1.png"
    chart1b = "temp_chart1b.png"
    chart2 = "temp_chart2.png"
    
    try:
        # Bước 1: Vẽ đồ thị
        create_foreign_chart(vietstock_csv, chart1)
        create_proprietary_chart(vietstock_csv, chart1b)
        create_index_chart(data_json, chart2)
        
        # Bước 2: AI Viết báo cáo
        md_text = generate_markdown_via_ai(text_json, data_json)
        
        # Bước 3: Build HTML
        html_body = markdown.markdown(md_text, extensions=['tables'])
        html_body = inject_charts_to_html(html_body, chart1, chart1b, chart2)
        
        report_date = datetime.now().strftime('%d/%m/%Y')
        with open(data_json, 'r', encoding='utf-8') as f:
            d = json.load(f)
            if 'report_date' in d:
                report_date = d['report_date']
        
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
                h1 {{ color: #003366; text-align: center; border-bottom: 2px solid #003366; padding-bottom: 10px; }}
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
                <h1 style="margin-bottom: 5px;">BÁO CÁO THỊ TRƯỜNG</h1>
                <p style="text-align: center; color: #666; margin-top: 0;">Cập nhật ngày {report_date}</p>
            </div>
            {html_body}
            
            <div class="footer">
                Báo cáo được tạo tự động bởi Vonika
            </div>
        </body>
        </html>
        """
        
        temp_html_path = "temp_report.html"
        with open(temp_html_path, 'w', encoding='utf-8') as f:
            f.write(full_html)
            
        # Bước 4: Xuất PDF bằng Playwright
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


    finally:
        # Dọn rác
        for f in [chart1, chart1b, chart2, "temp_report.html"]:
            if os.path.exists(f):
                os.remove(f)

def upload_market_report_to_supabase(pdf_path):
    import unicodedata
    supabase_url = "https://jqzlmzbvaesczarqptye.supabase.co"
    supabase_key = "sb_publishable_wXUovp36dvd_VwdX-U8ecg_P-OrGwEb"
    backend_url = "https://vonika-git-863156331978.europe-west1.run.app/api"
    
    file_name = os.path.basename(pdf_path)
    safe_name = unicodedata.normalize('NFKD', file_name).encode('ASCII', 'ignore').decode('utf-8')
    unique_file_name = f"market_reports/{int(datetime.now().timestamp() * 1000)}_{safe_name.replace(' ', '_')}"
    
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}"
    }
    
    try:
        # 1. Upload to Storage
        print(f"Uploading {file_name} to Supabase Storage...")
        with open(pdf_path, 'rb') as f:
            file_bytes = f.read()
        
        upload_url = f"{supabase_url}/storage/v1/object/chat-files/{unique_file_name}"
        upload_res = requests.post(
            upload_url, 
            headers={**headers, "Content-Type": "application/pdf"}, 
            data=file_bytes
        )
        if not upload_res.ok:
            print("Failed to upload to storage:", upload_res.text)
            return
            
        # 2. Insert to uploaded_files
        print("Inserting into uploaded_files table...")
        public_url = f"{supabase_url}/storage/v1/object/public/chat-files/{unique_file_name}"
        
        db_url = f"{supabase_url}/rest/v1/uploaded_files"
        db_res = requests.post(
            db_url,
            headers={**headers, "Content-Type": "application/json", "Prefer": "return=representation"},
            json={"file_name": file_name, "file_url": public_url, "category": "market_reports"}
        )
        if not db_res.ok:
            print("Failed to insert DB:", db_res.text)
            return
            
        db_data = db_res.json()
        file_id = db_data[0]['id']
        
        # 3. Process file via RAG backend
        print(f"Processing file {file_id} via RAG backend...")
        process_res = requests.post(
            f"{backend_url}/process-file",
            headers={"Content-Type": "application/json"},
            json={"file_id": file_id}
        )
        if process_res.ok:
            print("Successfully processed market report file for RAG.")
        else:
            print("Failed to process file on backend:", process_res.text)
    except Exception as e:
        print("Error uploading/processing to Supabase:", str(e))

if __name__ == "__main__":
    import subprocess
    import sys
    
    # 1. Cơ chế Tự thoát (Idempotency) - Kiểm tra file của ngày hôm nay đã tồn tại chưa
    today_date = datetime.now().strftime('%d/%m/%Y')
    today_file_date = today_date.replace('/', '-')
    expected_pdf = os.path.join(OUTPUT_DIR, f"Báo cáo thị trường ngày {today_file_date}.pdf")
    
    if os.path.exists(expected_pdf):
        print(f"File '{expected_pdf}' đã tồn tại. Bỏ qua chạy để tránh trùng lặp.")
        sys.exit(0)

    # Tự động chạy các script cập nhật dữ liệu mới nhất
    try:
        subprocess.run([sys.executable, "download_report.py"], cwd="masvn_report", check=True)
        subprocess.run([sys.executable, "parserReport.py"], cwd="masvn_report", check=True)
        subprocess.run([sys.executable, "extract_vietstock.py"], cwd="vietstock", check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(1)

    text_path = os.path.join("masvn_report", "extracted_text.json")
    data_path = os.path.join("masvn_report", "extracted_data.json")
    csv_path = os.path.join("vietstock", "combined_net_trading.csv")
    
    with open(data_path, 'r', encoding='utf-8') as f:
        d = json.load(f)
        if 'report_date' in d:
            report_date = d['report_date']
            
    if report_date != today_date:
        print(f"Dữ liệu web mới nhất là ngày {report_date}, chưa có của hôm nay ({today_date}). Bỏ qua.")
        sys.exit(0)

    out_path = f"Báo cáo thị trường ngày {report_date.replace('/', '-')}.pdf"
    
    if not os.path.exists(csv_path):
        sys.exit(1)
    elif not os.path.exists(text_path) or not os.path.exists(data_path):
        sys.exit(1)
    else:
        asyncio.run(build_report_pdf(text_path, data_path, csv_path, out_path))
        
        # Tự động upload báo cáo mới lên Supabase
        upload_market_report_to_supabase(out_path)
        
        # Đánh dấu đã tạo file thành công trong phiên chạy này
        with open("NEW_REPORT_GENERATED", "w") as f:
            f.write("OK")

    for old_report in glob.glob(os.path.join(OUTPUT_DIR, "Báo cáo thị trường ngày *.pdf")):
        # We need to make sure out_path is also absolute when comparing
        if os.path.abspath(old_report) != os.path.abspath(os.path.join(OUTPUT_DIR, out_path)):
            try:
                subprocess.run(["git", "rm", old_report], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"Removed {old_report} from git.")
            except Exception:
                try:
                    os.remove(old_report)
                    print(f"Deleted local file {old_report}.")
                except OSError:
                    pass