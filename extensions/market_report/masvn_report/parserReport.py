import pdfplumber
import json
import re
import requests
import os
from datetime import datetime
import sys
import codecs

# Fix Windows console unicode print errors
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

from glob import glob

PDF_DIR = os.path.dirname(os.path.abspath(__file__))

def get_latest_pdf_path():
    files = glob(os.path.join(PDF_DIR, "report_*.pdf"))
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]


def extract_report_date(pdf_path):
    """Trích xuất ngày báo cáo từ tên file PDF hoặc từ nội dung trang 1.
    
    Ưu tiên 1: Tên file có dạng *_YYYYMMDD.pdf  → vd: MiraeAsset_Daily_VN_20260306.pdf
    Ưu tiên 2: Dòng đầu trang 1 PDF chứa ngày định dạng DD/MM/YYYY hoặc YYYY-MM-DD.
    Fallback  : Trả về None.
    """
    # Lấy ngày từ tên file (pattern YYYYMMDD, năm phải trong khoảng 2000-2099)
    filename = os.path.basename(pdf_path)
    for m in re.finditer(r'(\d{4})(\d{2})(\d{2})', filename):
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 2000 <= year <= 2099 and 1 <= month <= 12 and 1 <= day <= 31:
            return f"{day:02d}/{month:02d}/{year}"
    
    # Fallback: quét trang 1 tìm dòng chứa ngày
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page1_text = pdf.pages[0].extract_text() or ""
            
            # Ưu tiên 1: Dạng "23 Tháng 03, 2026"
            m1 = re.search(r'(\d{1,2})\s+[tT]háng\s+(\d{1,2}),\s+(\d{4})', page1_text)
            if m1:
                return f"{m1.group(1).zfill(2)}/{m1.group(2).zfill(2)}/{m1.group(3)}"
                
            # Ưu tiên 2: Dạng "23/03/2026" (Chỉ dùng dấu /, không dùng -)
            m2 = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', page1_text)
            if m2:
                return f"{m2.group(1).zfill(2)}/{m2.group(2).zfill(2)}/{m2.group(3)}"
    except Exception:
        pass
    
    return None



def extract_analytical_text(pdf_path, silent=False):
    if not silent:
        pass
    text_content = {
        "nhan_dinh_thi_truong": "",
        "thong_tin_cap_nhat": ""
    }
    
    with pdfplumber.open(pdf_path) as pdf:
        tin_tuc_text = ""
        for page in pdf.pages[6:]: # Page 7 onwards
            tin_tuc_text += (page.extract_text() or "") + "\n"
        
        if "Thông tin cập nhật" in tin_tuc_text:
            start_idx = tin_tuc_text.find("Thông tin cập nhật") + len("Thông tin cập nhật")
            
            # Tìm nhiều dấu hiệu kết thúc khác nhau để phòng hờ form báo cáo thay đổi
            end_markers = [
                "Chỉ báo tham khảo", "CHỈ BÁO THAM KHẢO",
                "Bản tin thị trường", "BẢN TIN THỊ TRƯỜNG",
                "Khuyến cáo", "KHUYẾN CÁO"
            ]
            
            end_idx = -1
            for marker in end_markers:
                idx = tin_tuc_text.find(marker, start_idx)
                if idx != -1 and (end_idx == -1 or idx < end_idx):
                    end_idx = idx
                
            if end_idx != -1:
                text_content["thong_tin_cap_nhat"] = tin_tuc_text[start_idx:end_idx].strip()
            else:
                text_content["thong_tin_cap_nhat"] = tin_tuc_text[start_idx:].strip()

    import fitz
    doc = fitz.open(pdf_path)
    page1 = doc[0]
    blocks = page1.get_text("blocks")
    
    page1_text = "\n".join([b[4] for b in blocks if b[6] == 0]) 
    
    analyst_markers = ["Nguyễn Viết Sang", "Lâm Tuấn Nhã", "Huỳnh Thị Thu Thảo", "Trần Khánh Linh"]

    if "Nhận định thị trường" in page1_text:
        start_idx = page1_text.find("Nhận định thị trường") + len("Nhận định thị trường")
        
        nhan_dinh_end_markers = analyst_markers + ["Analyst", "Cập nhật kỹ thuật"]
        
        end_idx = -1
        for marker in nhan_dinh_end_markers:
            idx = page1_text.find(marker, start_idx)
            if idx != -1 and (end_idx == -1 or idx < end_idx):
                end_idx = idx
        
        if start_idx != -1 and end_idx != -1:
            raw_text = page1_text[start_idx:end_idx].strip()
            clean_lines = []
            for line in raw_text.split('\n'):
                if line.strip():
                    clean_lines.append(line.strip())
            text_content["nhan_dinh_thi_truong"] = "\n".join(clean_lines)
    
    doc.close()            
    return text_content


        
def extract_all_page1_data(pdf_path, silent=False):
    if not silent:
        pass
    all_data = {
        "Tổng quan thị trường": [],
        "Định giá thị trường": [],
        "Lãi suất tham chiếu": [],
        "Tỷ giá ngoại hối": [],
        "Giá trị giao dịch bình quân/ngày (triệu US$)": []
    }
    
    with pdfplumber.open(pdf_path) as pdf:
        if len(pdf.pages) == 0:
            return {}

        first_page = pdf.pages[0]
        text = first_page.extract_text()
        if not text:
            return {}
            
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # 1. Tổng quan thị trường
            m_tong_quan = re.search(r'^(UPCOM|VN INDEX|HNX|MSCI EM|NIKKEI|HANG SENG|KOSPI|FTSE|S&P 500|NASDAQ)\s+([\d,\.]+)\s+([\-\d\.]+)\s+([\-\d\.]+)\s+([\-\d\.]+)', line)
            if m_tong_quan:
                chi_so = m_tong_quan.group(1)
                if chi_so == "UPCOM" and not "." in m_tong_quan.group(2) and len(m_tong_quan.group(2)) < 4:
                    pass
                else:
                    all_data["Tổng quan thị trường"].append({
                        "Chỉ số": chi_so,
                        "Thị giá": m_tong_quan.group(2),
                        "1D (%)": m_tong_quan.group(3),
                        "1M (%)": m_tong_quan.group(4),
                        "1Y (%)": m_tong_quan.group(5)
                    })
                    continue
            
            # 2. Định giá thị trường
            m_dinh_gia = re.search(r'^(Việt Nam|Vietnam|Mỹ|Nhật Bản|Hàn Quốc|Trung Quốc|Đài Loan|Ấn Độ|Thái Lan|Thailand|Indonesia|Malaysia|Philippines)\s+([\d,\.]+)\s+([\d,\.]+)\s+([\d,\.]+)', line, re.IGNORECASE)
            if m_dinh_gia:
                all_data["Định giá thị trường"].append({
                    "Quốc gia": m_dinh_gia.group(1),
                    "P/E": m_dinh_gia.group(2),
                    "P/B": m_dinh_gia.group(3),
                    "ROE": m_dinh_gia.group(4)
                })
                continue
                
            # 3. Lãi suất tham chiếu
            m_lai_suat = re.search(r'^(Tái cấp vốn|Chiết khấu|Tín phiếu \(28 ngày\)|LNH \(ON\)|LNH \(1 tuần\)|LNH \(1 tháng\)|TPCP 5 năm|TPCP 10 năm)\s+([\d\.]+)\s+([\-\d\.]+)\s+([\-\d\.]+)\s+([\-\d\.]+)', line, re.IGNORECASE)
            if m_lai_suat:
                all_data["Lãi suất tham chiếu"].append({
                    "Loại": m_lai_suat.group(1),
                    "Thị giá": m_lai_suat.group(2),
                    "1D (bps)": m_lai_suat.group(3),
                    "1M (bps)": m_lai_suat.group(4),
                    "1Y (bps)": m_lai_suat.group(5)
                })
                continue
                
            # 4. Tỷ giá ngoại hối
            m_ty_gia = re.search(r'^(US\$/VND|US\$/KRW|US\$/JPY|US\$/CNY|US\$/THB|US\$/MYR|US\$/IDR|US\$/EUR|US\$/GBP|US\$/SGD)\s+([\d,\.]+)\s+([\-\d\.]+)\s+([\-\d\.]+)\s+([\-\d\.]+)', line, re.IGNORECASE)
            if m_ty_gia:
                all_data["Tỷ giá ngoại hối"].append({
                    "Loại": m_ty_gia.group(1),
                    "Thị giá": m_ty_gia.group(2),
                    "1D (%)": m_ty_gia.group(3),
                    "1M (%)": m_ty_gia.group(4),
                    "1Y (%)": m_ty_gia.group(5)
                })
                continue
                
            # 5. Giá trị giao dịch
            m_giao_dich = re.search(r'^(HOSE|HNX|VN-INDEX)\s+([\d,\.]+)\s+([\d,\.]+)\s+([\d,\.]+)', line, re.IGNORECASE)
            if m_giao_dich:
                all_data["Giá trị giao dịch bình quân/ngày (triệu US$)"].append({
                    "Sàn": m_giao_dich.group(1),
                    "Gần nhất": m_giao_dich.group(2),
                    "TB 1 tháng": m_giao_dich.group(3),
                    "TB 6 tháng": m_giao_dich.group(4)
                })
                continue
            
            # Giao dịch UPCOM
            m_giao_dich_upcom = re.search(r'^UPCOM\s+([\d,\.]+)\s+([\d,\.]+)\s+([\d,\.]+)', line, re.IGNORECASE)
            if m_giao_dich_upcom and not "." in m_giao_dich_upcom.group(1) and len(m_giao_dich_upcom.group(1)) < 4:
                all_data["Giá trị giao dịch bình quân/ngày (triệu US$)"].append({
                    "Sàn": "UPCOM",
                    "Gần nhất": m_giao_dich_upcom.group(1),
                    "TB 1 tháng": m_giao_dich_upcom.group(2),
                    "TB 6 tháng": m_giao_dich_upcom.group(3)
                })
                
    return all_data


if __name__ == "__main__":
    import sys
    
    pdf_path = get_latest_pdf_path()
    if not pdf_path:
        sys.exit(1)
        
    report_date = extract_report_date(pdf_path)
    text_data = extract_analytical_text(pdf_path)
    json_data = extract_all_page1_data(pdf_path)

    if report_date:
        text_data["report_date"] = report_date
        json_data["report_date"] = report_date
        pass
    
    with open(os.path.join(PDF_DIR, "extracted_text.json"), "w", encoding="utf-8") as f:
        json.dump(text_data, f, ensure_ascii=False, indent=4)
        
    with open(os.path.join(PDF_DIR, "extracted_data.json"), "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)
        