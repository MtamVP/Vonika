import os
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

def download_vietcap_report(email, password):

    headless_mode = True
    
    with sync_playwright() as p:
        #print("Launching browser...")
        browser = p.chromium.launch(headless=headless_mode)
        context = browser.new_context()
        page = context.new_page()
        
        #print("Navigating to Vietcap homepage...")
        page.goto("https://trading.vietcap.com.vn/", wait_until="domcontentloaded", timeout=60000)
        
        #print("Clicking login button on homepage...")
        page.locator('.main-login--I81cI').click()
        
        page.wait_for_selector('input[type="password"]', timeout=10000)
        page.wait_for_timeout(1000)
        
        #print("Clicking 'Số điện thoại/Email' tab if needed...")
        try:
            page.locator("button.sliding-tab", has_text="Số điện thoại/Email").click(timeout=3000)
            page.wait_for_timeout(1000)
        except Exception as e:
            print(f"Lỗi khi click tab: {e}")

        #print("Filling credentials...")
        page.locator('#email').fill(email)
        page.locator('#password').fill(password)
        
        #print("Submitting login form...")
        page.locator('.main-button-submit--Uzc75').click()
        
        #print("Waiting 5s for login and cookies to settle...")
        page.wait_for_timeout(5000)
                
        downloaded = False
        output_dir = os.path.dirname(os.path.abspath(__file__))
        
        import json
        import sys
        
        # Đồng bộ ngày tải file với báo cáo MASVN
        masvn_data_path = os.path.join(output_dir, "..", "masvn_report", "extracted_data.json")
        try:
            with open(masvn_data_path, 'r', encoding='utf-8') as f:
                d = json.load(f)
                target_date_str = d.get('report_date', datetime.now().strftime('%d/%m/%Y'))
        except Exception:
            target_date_str = datetime.now().strftime('%d/%m/%Y')
            
        date_obj = datetime.strptime(target_date_str, '%d/%m/%Y')
        yyyymm = date_obj.strftime("%Y%m")
        yyyymmdd = date_obj.strftime("%Y%m%d")
        
        url = f"https://trading.vietcap.com.vn/iq/view-file?file=uploads%2Ffile%2F{yyyymm}%2F{yyyymmdd}_DailyVN.pdf&source=cms"
        
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        try:
            # Chờ ít nhất 1 nút của PDF viewer xuất hiện
            page.wait_for_selector('.pdf-viewer-icon-btn', timeout=20000)
            
            # Debug: In ra tất cả các nút hiện có
            titles = page.evaluate('''() => {
                return Array.from(document.querySelectorAll(".pdf-viewer-icon-btn")).map(b => b.title)
            }''')
            print(f"[DEBUG] Found PDF buttons: {titles}")
            
            page.wait_for_timeout(5000)
            
            with page.expect_download(timeout=60000) as download_info:
                download_btn = page.locator('.pdf-viewer-icon-btn[title="Tải xuống"], .pdf-viewer-icon-btn[title="Download"]')
                if download_btn.count() > 0:
                    download_btn.first.click(force=True)
                else:
                    print("[DEBUG] Falling back to the 4th button (index 3)")
                    page.locator('.pdf-viewer-icon-btn').nth(3).click(force=True)
            
            download = download_info.value
            filename = f"{yyyymmdd}_DailyVN.pdf"
            output_path = os.path.join(output_dir, filename)
            download.save_as(output_path)
            
            downloaded = True
        except Exception as e:
            print(f"[DEBUG] Error encountered: {e}")
            print("[DEBUG] Current URL:", page.url)
            try:
                print("[DEBUG] Page Text snippet:", page.evaluate('document.body.innerText')[:500])
            except:
                pass
            
            try:
                print(f"Không tìm thấy báo cáo Vietcap ngày {target_date_str}. Tạm dừng pipeline để chờ cập nhật.")
            except UnicodeEncodeError:
                print(f"Khong tim thay bao cao Vietcap ngay {target_date_str}. Tam dung pipeline.")
            browser.close()
            sys.exit(2)
            
        browser.close()
        return downloaded

if __name__ == "__main__":
    download_vietcap_report("vophucminhtam@gmail.com", "Vietkhue@2303")
