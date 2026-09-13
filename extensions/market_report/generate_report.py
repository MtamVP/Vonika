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
from dotenv import load_dotenv
import glob
import requests
import urllib.parse
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

def dicts_to_html_table(data_list):
    if not data_list: return ""
    headers = list(data_list[0].keys())
    html = "<table><thead><tr>"
    for h in headers:
        html += f"<th>{h}</th>"
    html += "</tr></thead><tbody>"
    for row in data_list:
        html += "<tr>"
        for h in headers:
            html += f"<td>{row.get(h, '')}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    return html

def clean_markdown_table(md_str):
    import re
    lines = md_str.strip().split('\n')
    if len(lines) < 2: return md_str
    
    rows = []
    for line in lines:
        if line.strip().startswith('|') and line.strip().endswith('|'):
            cells = [c.strip() for c in line.strip()[1:-1].split('|')]
            rows.append(cells)
            
    if not rows: return md_str
    
    num_cols = max(len(r) for r in rows)
    for r in rows:
        r.extend([''] * (num_cols - len(r)))
        
    cols = list(zip(*rows))
    
    keep_cols = []
    for col in cols:
        is_empty = True
        for i, cell in enumerate(col):
            if i == 1: continue 
            if cell and not re.match(r'^[-:]+$', cell):
                is_empty = False
                break
        if not is_empty:
            keep_cols.append(col)
            
    if not keep_cols: return md_str
    
    new_rows = list(zip(*keep_cols))
    new_lines = []
    for i, r in enumerate(new_rows):
        if i == 1:
            new_lines.append("| " + " | ".join(['---']*len(r)) + " |")
        else:
            new_lines.append("| " + " | ".join(r) + " |")
            
    return '\n'.join(new_lines)

def clean_all_markdown_tables_in_text(full_md):
    lines = full_md.split('\n')
    cleaned_lines = []
    in_table = False
    table_lines = []
    
    for line in lines:
        if line.strip().startswith('|') and line.strip().endswith('|'):
            in_table = True
            table_lines.append(line)
        else:
            if in_table:
                cleaned_table = clean_markdown_table('\n'.join(table_lines))
                cleaned_lines.append(cleaned_table)
                table_lines = []
                in_table = False
            cleaned_lines.append(line)
            
    if in_table:
        cleaned_table = clean_markdown_table('\n'.join(table_lines))
        cleaned_lines.append(cleaned_table)
        
    return '\n'.join(cleaned_lines)

def generate_markdown_via_ai(text_json_path, data_json_path, vietcap_json_path=None):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Lỗi: Không tìm thấy GEMINI_API_KEY trong environment variables.")
        
    client = genai.Client(api_key=api_key)
    
    with open(text_json_path, 'r', encoding='utf-8') as f:
        text_data = json.load(f)
        
    vietcap_text = ""
    if vietcap_json_path and os.path.exists(vietcap_json_path):
        with open(vietcap_json_path, 'r', encoding='utf-8') as f:
            vietcap_data = json.load(f)
            raw_v_text = vietcap_data.get("full_markdown", "")
            vietcap_text = clean_all_markdown_tables_in_text(raw_v_text)
            
    prompt = f"""Bạn là một chuyên gia phân tích tài chính cấp cao. Dưới đây là dữ liệu báo cáo thị trường từ MASVN và Vietcap.
Hãy đọc và tổ chức các dữ liệu này thành bản tin thị trường chuyên nghiệp.

VĂN PHONG VÀ CẤU TRÚC YÊU CẦU:
- Viết bằng Markdown.
- TUYỆT ĐỐI KHÔNG TRỘN LẪN (MIX) số liệu của MASVN và Vietcap vào cùng một câu chuyện. Phải tách biệt rõ ràng thông tin của từng nguồn để đảm bảo tính nhất quán của số liệu.
- BẮT BUỘC CHỈ SỬ DỤNG 3 HEADING CHÍNH (dùng thẻ ##):

## NHẬN ĐỊNH THỊ TRƯỜNG
- Dùng ĐỘC QUYỀN dữ liệu từ phần "nhan_dinh_thi_truong" của MASVN để viết. Không được lấy số liệu VNI từ Vietcap đưa vào đây để tránh mâu thuẫn.

## GIAO DỊCH KHỐI NGOẠI & TỰ DOANH
- Dùng ĐỘC QUYỀN dữ liệu của MASVN để đảm bảo thống nhất với phần trên.

## THÔNG TIN CẬP NHẬT
- Trình bày lần lượt các tin tức và phân tích doanh nghiệp.
- BẮT BUỘC phải ghi rõ nguồn ở cuối MỖI tin/bài phân tích (ví dụ: *Nguồn: vietstock.vn*, *Nguồn: Vietcap*...).
- LƯU Ý TỐI QUAN TRỌNG VỀ ĐỘ DÀI: KHÔNG ĐƯỢC TÓM TẮT QUÁ NGẮN. Phải giữ lại đầy đủ các phân tích chuyên sâu, định giá, khuyến nghị, số liệu chi tiết. Báo cáo TỐI THIỂU phải dài 10-15 trang. Việc rút ngắn là vi phạm yêu cầu.
- BẮT BUỘC KHÔNG DÙNG THẺ h1 (tức là dấu #). CHỈ SỬ DỤNG 3 HEADING CHÍNH với thẻ h2 (##) như đã yêu cầu. Tuyệt đối không tự bịa thêm tiêu đề tổng đầu trang.
- DỌN DẸP RÁC VĂN BẢN: Hãy tự động nhận diện và loại bỏ các ký tự rác, tiêu đề trang/chân trang lặp lại do lỗi parse PDF (ví dụ: Trang 14 / 18, Bản tin thị trường, Vonika, v.v.).
- ĐỊNH DẠNG MARKDOWN: BẮT BUỘC in đậm (**) các từ khóa, tên mã cổ phiếu (ví dụ **MBB**, **HPG**) và các tiêu đề phụ (ví dụ: **Luận điểm đầu tư:**, **Định giá:**) để làm nổi bật thông tin.
- PHỤC HỒI BẢNG BIỂU: Dữ liệu bảng của Vietcap có thể bị lỗi dính chữ do parse PDF. Bạn HÃY TỰ ĐỘNG PHỤC HỒI và format lại chúng thành các bảng Markdown ngay ngắn, tuyệt đẹp. TUYỆT ĐỐI KHÔNG xóa bỏ bảng, và KHÔNG biến các dòng trong bảng thành các gạch đầu dòng.
- KỶ LUẬT XUỐNG DÒNG DANH SÁCH: Khi viết các mục liệt kê (như `- Ngành...`, `- Giá...`), BẠN PHẢI CHỦ ĐỘNG XUỐNG DÒNG (Enter 2 lần) trước mỗi dấu `-` hoặc `*` để tạo List chuẩn Markdown. TUYỆT ĐỐI KHÔNG viết dính chùm trên cùng một dòng.

DỮ LIỆU ĐẦU VÀO:
=== TEXT DATA MASVN ===
{json.dumps(text_data, ensure_ascii=False, indent=2)}

=== TEXT DATA VIETCAP ===
{vietcap_text}

Bắt đầu viết Báo cáo:
"""
    max_retries = 5
    current_model = "gemini-3.8-flash"
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
                # Progressive model fallback strategy
                if attempt == 0:
                    print("Falling back to gemini-3.7-flash due to high demand.")
                    current_model = "gemini-3.7-flash"
                elif attempt == 1:
                    print("Falling back to gemini-3.6-flash due to prolonged high demand.")
                    current_model = "gemini-3.6-flash"
                elif attempt == 2:
                    print("Falling back to gemini-2.5-flash due to extreme high demand.")
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
    img1_tag = f'<div style="text-align: center; margin: 15px 0; clear: both;"><img src="{get_base64_image(chart1_path)}" style="max-width: 100%; height: auto; display: block; margin: 0 auto; border-radius: 4px; border: 1px solid #eee;"></div>' if os.path.exists(chart1_path) else ''
    img1b_tag = f'<div style="text-align: center; margin: 15px 0; clear: both;"><img src="{get_base64_image(chart1b_path)}" style="max-width: 100%; height: auto; display: block; margin: 0 auto; border-radius: 4px; border: 1px solid #eee;"></div>' if os.path.exists(chart1b_path) else ''
    img2_tag = f'<div style="text-align: center; margin: 15px 0; clear: both;"><img src="{get_base64_image(chart2_path)}" style="max-width: 100%; height: auto; display: block; margin: 0 auto; border-radius: 4px; border: 1px solid #eee;"></div>' if os.path.exists(chart2_path) else ''

    # Replace H2 headers with our styled divs and inject charts
    if '<h2>NHẬN ĐỊNH THỊ TRƯỜNG' in html_content:
        html_content = html_content.replace('<h2>NHẬN ĐỊNH THỊ TRƯỜNG</h2>', f'{img2_tag}<div class="mas-section-header">NHẬN ĐỊNH THỊ TRƯỜNG</div>')
    
    if '<h2>GIAO DỊCH KHỐI NGOẠI' in html_content:
        html_content = html_content.replace('<h2>GIAO DỊCH KHỐI NGOẠI &amp; TỰ DOANH</h2>', f'<div class="mas-section-header">GIAO DỊCH KHỐI NGOẠI & TỰ DOANH</div>')
        html_content = html_content.replace('<h2>GIAO DỊCH KHỐI NGOẠI & TỰ DOANH</h2>', f'<div class="mas-section-header">GIAO DỊCH KHỐI NGOẠI & TỰ DOANH</div>')
        
    if '<h2>THÔNG TIN CẬP NHẬT' in html_content:
        html_content = html_content.replace('<h2>THÔNG TIN CẬP NHẬT</h2>', f'{img1_tag}{img1b_tag}<div class="mas-section-header">THÔNG TIN CẬP NHẬT</div>')
        
    # Fallback for any other h2
    html_content = html_content.replace('<h2>', '<div class="mas-section-header">').replace('</h2>', '</div>')
    return html_content

async def build_report_pdf(text_json, data_json, vietstock_csv, vietcap_json, out_pdf):
    chart1 = "temp_chart1.png"
    chart1b = "temp_chart1b.png"
    chart2 = "temp_chart2.png"
    
    try:
        # Bước 1: Vẽ đồ thị
        create_foreign_chart(vietstock_csv, chart1)
        create_proprietary_chart(vietstock_csv, chart1b)
        create_index_chart(data_json, chart2)
        
        # Bước 2: AI Viết báo cáo (Chỉ cho cột phải)
        md_text = generate_markdown_via_ai(text_json, data_json, vietcap_json)
        
        # Hậu xử lý: Dùng Regex ép xuống dòng cho các bullet points bị AI viết dính chùm
        import re
        md_text = re.sub(r'(?<!\n)\s+-\s+\*\*', r'\n\n- **', md_text)
        md_text = re.sub(r'(?<!\n)\s+\*\s+\*\*', r'\n\n* **', md_text)
        
        with open(data_json, 'r', encoding='utf-8') as f:
            d = json.load(f)
            
        report_date = datetime.now().strftime('%d/%m/%Y')
        if 'report_date' in d:
            report_date = d['report_date']

        # Bước 3: Build HTML Cột Trái (Data Tables)
        left_html = f'<div style="text-align: center; font-size: 14px; font-weight: bold; color: #7f8c8d; margin-bottom: 15px; text-transform: uppercase;">Báo cáo thị trường<br/>Ngày {report_date}</div>'        
            
        for section in ["Tổng quan thị trường", "Định giá thị trường", "Lãi suất tham chiếu", "Tỷ giá ngoại hối", "Giá trị giao dịch bình quân/ngày (triệu US$)"]:
            if section in d:
                left_html += f'<div class="mas-table-header">{section}</div>'
                left_html += dicts_to_html_table(d[section])
                
        # Bước 4: Build HTML Cột Phải (Text + Charts)
        right_html = markdown.markdown(md_text, extensions=['tables'])
        right_html = inject_charts_to_html(right_html, chart1, chart1b, chart2)
        
        split_marker = '<div class="mas-section-header">THÔNG TIN CẬP NHẬT</div>'
        if split_marker in right_html:
            parts = right_html.split(split_marker, 1)
            right_top_html = parts[0]
            full_bottom_html = split_marker + parts[1]
        else:
            right_top_html = right_html
            full_bottom_html = ""
            
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    color: #333;
                    line-height: 1.5;
                    padding: 30px 40px;
                    margin: 0;
                    background: #fff;
                }}
                .report-container {{
                    display: flex;
                    flex-direction: row;
                    justify-content: space-between;
                    width: 100%;
                }}
                .col-left {{
                    width: 38%;
                    padding-right: 20px;
                    box-sizing: border-box;
                }}
                .col-right {{
                    width: 59%;
                    box-sizing: border-box;
                }}
                
                /* Style cho các Header bảng bên cột trái */
                .mas-table-header {{
                    background-color: #003366;
                    color: white;
                    padding: 6px 10px;
                    font-size: 11px;
                    font-weight: bold;
                    text-transform: uppercase;
                    margin-top: 15px;
                    margin-bottom: 5px;
                    border-radius: 2px;
                }}
                
                /* Style cho bảng bên cột trái */
                .col-left table {{
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 10px;
                    margin-top: 5px;
                    margin-bottom: 12px;
                    table-layout: fixed;
                    word-wrap: break-word;
                    color: #333;
                }}
                .col-left th, .col-left td {{
                    border-bottom: 1px solid #e0e0e0;
                    padding: 6px 4px;
                    text-align: right;
                    line-height: 1.3;
                }}
                .col-left th {{
                    background-color: #f0f4f8;
                    color: #003366;
                    text-align: center;
                    font-weight: bold;
                    border-bottom: 2px solid #003366;
                }}
                .col-left tr:nth-child(even) {{
                    background-color: #f8f9fa;
                }}
                .col-left td:first-child {{
                    text-align: left;
                    font-weight: 500;
                }}
                .vietcap-table-wrapper table {{
                    font-size: 8px !important;
                }}
                .vietcap-table-wrapper th, .vietcap-table-wrapper td {{
                    padding: 4px 2px !important;
                }}

                /* Style cho cột phải (Phần nội dung) */
                .mas-title {{
                    color: #003366;
                    font-size: 32px;
                    font-weight: bold;
                    margin-bottom: 5px;
                    border-bottom: 2px solid #003366;
                    padding-bottom: 10px;
                }}
                .mas-section-header {{
                    background-color: #f2f2f2;
                    color: #333;
                    padding: 8px 12px;
                    font-weight: bold;
                    font-size: 16px;
                    margin-top: 25px;
                    margin-bottom: 10px;
                    text-transform: uppercase;
                    border-left: 4px solid #003366;
                }}
                .col-right p, .col-full p {{
                    font-size: 13px;
                    text-align: justify;
                    margin-bottom: 12px;
                }}
                .col-right h3, .col-full h3 {{
                    color: #003366;
                    font-size: 16px;
                    border-left: 3px solid #e67e22;
                    padding-left: 8px;
                    margin-top: 25px;
                    margin-bottom: 12px;
                }}
                .col-right h4, .col-right h5, .col-full h4, .col-full h5 {{
                    color: #d35400;
                    font-size: 14px;
                    margin-top: 15px;
                    margin-bottom: 8px;
                }}
                .col-right table, .col-full table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                    font-size: 11px;
                    color: #333;
                }}
                .col-right th, .col-right td, .col-full th, .col-full td {{
                    border: none;
                    border-bottom: 1px solid #e0e0e0;
                    padding: 8px 6px;
                    text-align: right;
                }}
                .col-right th, .col-full th {{
                    background-color: #f0f4f8;
                    color: #003366;
                    text-align: center;
                    font-weight: bold;
                    border-bottom: 2px solid #003366;
                }}
                .col-right tr:nth-child(even), .col-full tr:nth-child(even) {{
                    background-color: #f8f9fa;
                }}
                .col-right td:first-child, .col-right th:first-child, .col-full td:first-child, .col-full th:first-child {{
                    text-align: left;
                    font-weight: 500;
                }}
                .col-full {{
                    width: 100%;
                    clear: both;
                    margin-top: 30px;
                }}
                .footer {{ 
                    text-align: center; 
                    font-size: 11px; 
                    color: #888; 
                    margin-top: 40px; 
                    border-top: 1px solid #eee; 
                    padding-top: 10px; 
                }}
                strong {{
                    color: #003366;
                }}
            </style>
        </head>
        <body>
            <div class="report-container">
                <div class="col-left">
                    {left_html}
                </div>
                <div class="col-right">
                    <div class="mas-title">Bản tin cuối ngày</div>
                    {right_top_html}
                </div>
            </div>
            
            <div class="col-full">
                {full_bottom_html}
            </div>
            
            <div class="footer">
                Bản tin cuối ngày - Báo cáo được tạo tự động bởi Vonika - Cập nhật ngày {report_date}
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
                print_background=True,
                margin={"top": "1.2in", "right": "0.75in", "bottom": "0.75in", "left": "0.75in"},
                display_header_footer=True,
                header_template='<div style="width: 100%; font-size: 11px; padding: 0 0.75in; display: flex; justify-content: space-between; color: #003366; font-family: sans-serif; font-weight: bold;"><span>Vonika</span><span>Bản tin thị trường | Thông tin cập nhật</span></div>',
                footer_template='<div style="width: 100%; font-size: 9px; text-align: center; color: #7f8c8d; font-family: sans-serif;">Trang <span class="pageNumber"></span> / <span class="totalPages"></span></div>'
            )
            await browser.close()


    finally:
        # Dọn rác
        for f in [chart1, chart1b, chart2, "temp_report.html"]:
            if os.path.exists(f):
                os.remove(f)

def upload_market_report_to_supabase(pdf_path, folder_name="daily"):
    import unicodedata
    supabase_url = "https://jqzlmzbvaesczarqptye.supabase.co"
    supabase_key = "sb_publishable_wXUovp36dvd_VwdX-U8ecg_P-OrGwEb"
    backend_url = "https://vonika-git-110018515227.us-central1.run.app/api"
    
    file_name = os.path.basename(pdf_path)
    safe_name = unicodedata.normalize('NFKD', file_name).encode('ASCII', 'ignore').decode('utf-8')
    unique_file_name = f"market_reports/{folder_name}/{int(datetime.now().timestamp() * 1000)}_{safe_name.replace(' ', '_')}"
    
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
        
        # 3. Process file via RAG backend (with Retry/Backoff for Cloud Run cold starts)
        print(f"Processing file {file_id} via RAG backend...")
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                process_res = requests.post(
                    f"{backend_url}/process-file",
                    headers={"Content-Type": "application/json"},
                    json={"file_id": file_id},
                    timeout=120
                )
                if process_res.ok:
                    print("Successfully processed market report file for RAG.")
                    break
                else:
                    print(f"Failed to process file on backend (Attempt {attempt+1}):", process_res.text)
                    if attempt < max_retries - 1:
                        time.sleep(10 * (attempt + 1))
            except Exception as e:
                print(f"Error calling backend (Attempt {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(10 * (attempt + 1))
    except Exception as e:
        print("Error uploading/processing to Supabase:", str(e))

if __name__ == "__main__":
    import subprocess
    import sys
    
    # 1. Cơ chế Tự thoát (Idempotency) - Kiểm tra file của ngày hôm nay đã tồn tại chưa
    today_date = datetime.now().strftime('%d/%m/%Y')
    today_file_date = today_date.replace('/', '-')
    expected_file_name = f"Báo cáo thị trường ngày {today_file_date}.pdf"
    
    supabase_url = "https://jqzlmzbvaesczarqptye.supabase.co"
    supabase_key = "sb_publishable_wXUovp36dvd_VwdX-U8ecg_P-OrGwEb"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}"
    }
    
    query_url = f"{supabase_url}/rest/v1/uploaded_files?file_name=eq.{urllib.parse.quote(expected_file_name)}&select=id"
    try:
        resp = requests.get(query_url, headers=headers)
        if resp.ok and len(resp.json()) > 0:
            print(f"File '{expected_file_name}' đã tồn tại trên Supabase. Bỏ qua chạy để tránh trùng lặp.")
            sys.exit(0)
    except Exception as e:
        print(f"Lỗi khi kiểm tra file trên Supabase: {e}")

    # Tự động chạy các script cập nhật dữ liệu mới nhất
    res_download = subprocess.run([sys.executable, "download_report.py"], cwd="masvn_report")
    if res_download.returncode == 2:
        print(f"Trang nguồn chưa cập nhật báo cáo hôm nay. Dừng sớm để tiết kiệm tài nguyên.")
        sys.exit(0)
    elif res_download.returncode != 0:
        sys.exit(1)

    try:
        subprocess.run([sys.executable, "parserReport.py"], cwd="masvn_report", check=True)
        subprocess.run([sys.executable, "extract_vietstock.py"], cwd="vietstock", check=True)
        
        print("Đang tải & trích xuất báo cáo Vietcap...")
        # Sử dụng capture_output=False để không in lỗi ra làm hỏng pipeline nếu failed, hoặc dùng try-except
        subprocess.run([sys.executable, "auto_download_vietcap.py"], cwd="vietcap")
        subprocess.run([sys.executable, "parserReports.py"], cwd="vietcap")
    except subprocess.CalledProcessError as e:
        sys.exit(1)

    text_path = os.path.join("masvn_report", "extracted_text.json")
    data_path = os.path.join("masvn_report", "extracted_data.json")
    csv_path = os.path.join("vietstock", "combined_net_trading.csv")
    vietcap_path = os.path.join("vietcap", "extracted_vietcap.json")
    
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
        asyncio.run(build_report_pdf(text_path, data_path, csv_path, vietcap_path, out_path))
        
        # Tự động upload báo cáo mới lên Supabase
        upload_market_report_to_supabase(out_path)
        
        # Đánh dấu đã tạo file thành công trong phiên chạy này
        with open("NEW_REPORT_GENERATED", "w", encoding='utf-8') as f:
            f.write(out_path)