import os
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

def download_vietcap_report(email, password):

    headless_mode = False 
    
    with sync_playwright() as p:
        #print("Launching browser...")
        browser = p.chromium.launch(headless=headless_mode)
        context = browser.new_context()
        page = context.new_page()
        
        #print("Navigating to Vietcap homepage...")
        page.goto("https://trading.vietcap.com.vn/")
        
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
        
        for days_back in range(10):
            date_obj = datetime.now() - timedelta(days=days_back)
            yyyymm = date_obj.strftime("%Y%m")
            yyyymmdd = date_obj.strftime("%Y%m%d")
            
            url = f"https://trading.vietcap.com.vn/iq/view-file?file=uploads%2Ffile%2F{yyyymm}%2F{yyyymmdd}_DailyVN.pdf&source=cms"
            #print(f"Trying to open: {url}")
            
            page.goto(url)
            
            try:
                page.wait_for_selector('.pdf-viewer-icon-btn[title="Tải xuống"]', timeout=10000)
                
                #print("PDF viewer loaded. Waiting 5s for PDF to fully render and blob to generate...")
                page.wait_for_timeout(5000)
                
                #print("Clicking download...")
                with page.expect_download(timeout=60000) as download_info:
                    page.locator('.pdf-viewer-icon-btn[title="Tải xuống"]').click(force=True)
                
                download = download_info.value
                filename = f"{yyyymmdd}_DailyVN.pdf"
                output_path = os.path.join(output_dir, filename)
                download.save_as(output_path)
                
                #print(f"Successfully downloaded: {filename}")
                downloaded = True
                break
            except Exception as e:
                try:
                    print(f"Không tìm thấy file ở ngày {yyyymmdd}. Đang thử ngày trước đó...")
                except UnicodeEncodeError:
                    print(f"Khong tim thay file o ngay {yyyymmdd}. Dang thu ngay truoc do...")
                
        browser.close()
        return downloaded

if __name__ == "__main__":
    download_vietcap_report("vophucminhtam@gmail.com", "Vietkhue@2303")
