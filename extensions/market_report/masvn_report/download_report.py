import requests
import os
import re
import glob
from playwright.sync_api import sync_playwright

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_latest_report_link():
    with sync_playwright() as p:
        print("Opening browser...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print("Navigating to masvn.com...")
        page.goto("https://www.masvn.com/cate/bao-cao-thuong-nhat-22", wait_until="domcontentloaded", timeout=60000)
        print("Waiting 3 seconds...")
        
        page.wait_for_timeout(3000)
        
        # Get all links
        print("Extracting links...")
        links = page.evaluate("() => Array.from(document.querySelectorAll('a')).map(a => a.href)")
        browser.close()
        
        # Filter and parse dates
        report_links = []
        for link in links:
            match = re.search(r'MiraeAsset_Daily_VN_(\d{8})\.pdf', link, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                report_links.append((date_str, link))
                
        if not report_links:
            pass
            return None, None
            
        # Sort by date descending
        report_links.sort(key=lambda x: x[0], reverse=True)
        
        latest_date, latest_link = report_links[0]
        # output file format: report_DDMM.pdf
        mm = latest_date[4:6]
        dd = latest_date[6:8]
        filename = f"report_{dd}{mm}.pdf"
        print(f"Latest report: {latest_link} -> {filename}")
        
        return latest_link, filename

def download_pdf(url, output_path):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }
        print(f"Downloading PDF from {url}...")
        response = requests.get(url, verify=False, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Đảm bảo file tải về là PDF chứ không phải trang HTML chặn truy cập
        if 'application/pdf' in response.headers.get('Content-Type', ''):
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"Saved to {output_path}")
        else:
            print(f"Failed: Content-Type is {response.headers.get('Content-Type')}")
    except requests.exceptions.RequestException as e:
        print(f"Download error: {e}")

if __name__ == "__main__":
    import sys
    from datetime import datetime
    latest_url, filename = get_latest_report_link()
    if latest_url:
        today_ddmm = datetime.now().strftime('%d%m')
        if filename != f"report_{today_ddmm}.pdf":
            print(f"Latest report on web is {filename}, but today is report_{today_ddmm}.pdf. Skipping.")
            sys.exit(2)
            
        output_file = os.path.join(OUTPUT_DIR, filename)
        
        # Xóa các file báo cáo cũ trước khi tải file mới
        print("Cleaning up old reports...")
        for old_pdf in glob.glob(os.path.join(OUTPUT_DIR, "report_*.pdf")):
            try:
                os.remove(old_pdf)
            except:
                pass
                
        download_pdf(latest_url, output_file)
    else:
        print("No report link found.")
