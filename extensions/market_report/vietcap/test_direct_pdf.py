import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.goto('https://trading.vietcap.com.vn/', wait_until='domcontentloaded')
        
        try:
            await page.locator('.main-login--I81cI').click(timeout=5000)
        except:
            await page.get_by_role('button', name='Đăng nhập').click()
            
        await page.wait_for_selector('input[type="password"]', timeout=10000)
        
        try:
            await page.locator('button.sliding-tab', has_text='Số điện thoại/Email').click(timeout=3000)
        except:
            pass
            
        await page.locator('#email').fill('vophucminhtam@gmail.com')
        await page.locator('#password').fill('Vietkhue@2303')
        await page.locator('.main-button-submit--Uzc75').click()
        
        await page.wait_for_timeout(5000)
        
        pdf_url = 'https://trading.vietcap.com.vn/uploads/file/202609/20260918_DailyVN.pdf'
        print(f"Trying direct PDF download: {pdf_url}")
        
        try:
            # We don't use page.goto because it will navigate and download natively.
            # Playwright handles downloads differently if it's direct.
            # We can use APIRequestContext to fetch the file with cookies!
            response = await context.request.get(pdf_url)
            print("Status:", response.status)
            if response.status == 200:
                with open('test_direct_download.pdf', 'wb') as f:
                    f.write(await response.body())
                print("Successfully downloaded PDF directly via API!")
            else:
                print("Failed with status:", response.status)
        except Exception as e:
            print("Direct download failed:", e)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
