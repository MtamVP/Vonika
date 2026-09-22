import asyncio
from playwright.async_api import async_playwright
import os

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        print("Navigating to Vietcap...")
        await page.goto('https://trading.vietcap.com.vn/')
        try:
            await page.locator('.main-login--I81cI').click(timeout=5000)
        except:
            pass
            
        await page.wait_for_selector('input[type="password"]', timeout=5000)
        
        try:
            await page.locator('button.sliding-tab', has_text='Số điện thoại/Email').click(timeout=3000)
        except:
            pass
            
        print("Logging in...")
        await page.locator('#email').fill('vophucminhtam@gmail.com')
        await page.locator('#password').fill('Vietkhue@2303')
        await page.locator('.main-button-submit--Uzc75').click()
        
        await page.wait_for_timeout(5000)
        
        pdf_url = 'https://trading.vietcap.com.vn/uploads/file/202609/20260918_DailyVN.pdf'
        print(f"Fetching {pdf_url} directly...")
        response = await context.request.get(pdf_url)
        content = await response.body()
        
        print('Status:', response.status)
        print('Headers:', response.headers)
        print('First 200 bytes:', content[:200])
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
