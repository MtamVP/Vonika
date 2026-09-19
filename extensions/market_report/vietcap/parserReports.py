import pdfplumber
import json
from datetime import datetime
import sys
import codecs
import os
import re

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

from glob import glob

PDF_DIR = os.path.dirname(os.path.abspath(__file__))

def get_latest_pdf_path():
    files = glob(os.path.join(PDF_DIR, "*_DailyVN.pdf"))
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]

def extract_report_date(pdf_path):
    filename = os.path.basename(pdf_path)
    for m in re.finditer(r'(\\d{4})(\\d{2})(\\d{2})', filename):
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 2000 <= year <= 2099 and 1 <= month <= 12 and 1 <= day <= 31:
            return f"{day:02d}/{month:02d}/{year}"
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page1_text = pdf.pages[0].extract_text() or ""

            m = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', page1_text)
            if m:
                return f"{m.group(1).zfill(2)}/{m.group(2).zfill(2)}/{m.group(3)}"
    except Exception:
        pass
    return None


def table_to_markdown(table):
    if not table or not table[0]:
        return ""
    
    clean_table = []
    for row in table:
        clean_row = [str(cell).replace('\n', ' ') if cell is not None else "" for cell in row]
        if any(cell.strip() for cell in clean_row):
            clean_table.append(clean_row)
            
    if not clean_table:
        return ""
        
    md = []
    # Header
    header = clean_table[0]
    md.append("| " + " | ".join(header) + " |")
    md.append("|" + "|".join(["---"] * len(header)) + "|")
    
    # Body
    for row in clean_table[1:]:
        padded_row = row + [""] * (len(header) - len(row))
        md.append("| " + " | ".join(padded_row[:len(header)]) + " |")
        
    return "\n".join(md)

def extract_text(pdf_path, silent=False):
    if not silent:
        print(f"Extracting data from {pdf_path}...")
        
    stop_phrase = "Giá mục tiêu & Khuyến nghị - Cổ phiếu Vietcap theo dõi"
    
    extracted_content = {
        "report_date": extract_report_date(pdf_path),
        "pages": []
    }
    
    full_markdown_text = ""
    
    with pdfplumber.open(pdf_path) as pdf:
        stop_page_idx = -1
        
        # Find stop page
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text and stop_phrase in text:
                stop_page_idx = i
                break
                
        if stop_page_idx == -1:
            stop_page_idx = len(pdf.pages)
            
        if not silent:
            print(f"Parsing pages 1 to {stop_page_idx}...")
            
        for i in range(stop_page_idx):
            page = pdf.pages[i]
            page_text = page.extract_text() or ""
            tables = page.extract_tables()
            
            page_data = {
                "page_num": i + 1,
                "text": page_text,
                "tables_markdown": []
            }
            
            full_markdown_text += f"## PAGE {i + 1}\n\n"
            full_markdown_text += page_text + "\n\n"
            
            if tables:
                for idx, table in enumerate(tables):
                    md_table = table_to_markdown(table)
                    if md_table:
                        page_data["tables_markdown"].append(md_table)
                        full_markdown_text += f"### Bảng dữ liệu {idx + 1} (Trang {i + 1})\n\n"
                        full_markdown_text += md_table + "\n\n"
                        
            extracted_content["pages"].append(page_data)
            
    extracted_content["full_markdown"] = full_markdown_text
    
    output_path = os.path.join(PDF_DIR, "extracted_vietcap.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(extracted_content, f, ensure_ascii=False, indent=4)
        
    if not silent:
        print(f"Saved extracted data to {output_path}")
        
    return extracted_content

if __name__ == "__main__":
    pdf_path = get_latest_pdf_path()
    if pdf_path:
        extract_text(pdf_path)