import asyncio
import json
import csv
import os
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto("https://finance.vietstock.vn/", wait_until="domcontentloaded", timeout=30000)
        
        # 1. Wait for JS charts to fully render
        await asyncio.sleep(5)
        
        # 2. Extract Token
        token = await page.evaluate('''() => {
            let el = document.querySelector('input[name="__RequestVerificationToken"]');
            return el ? el.value : null;
        }''')
        
        # 3. Extract Dates from chart titles
        dates = await page.evaluate('''() => {
            let texts = [];
            document.querySelectorAll('span, h2, h3, div').forEach(el => {
                let txt = el.textContent || '';
                if (txt.includes('Giá trị giao dịch ròng theo mã CK ngày')) {
                    texts.push(txt.trim());
                }
            });
            let dateMatches = [];
            texts.forEach(t => {
                let m = t.match(/(\\d{2}\\/\\d{2}\\/\\d{4})/);
                if (m && !dateMatches.includes(m[1])) {
                    dateMatches.push(m[1]);
                }
            });
            
            let foreignDate = dateMatches.length > 0 ? dateMatches[0] : '';
            let propDate = dateMatches.length > 1 ? dateMatches[1] : foreignDate;
            
            return { foreignDate, propDate, texts };
        }''')
        
        foreign_date = dates.get("foreignDate", "")
        prop_date = dates.get("propDate", "")
        
        from datetime import datetime, timedelta

        async def fetch_data_with_retry(page, url, token, start_date_str):
            current_date_str = start_date_str
            for _ in range(10):
                data_str = await page.evaluate('''async ({url, token, dateStr}) => {
                    const formData = new URLSearchParams();
                    formData.append('selectType', '1');
                    formData.append('code', '');
                    formData.append('detailType', '6');
                    formData.append('criterion', '1');
                    formData.append('type', '1');
                    formData.append('dateString', dateStr);
                    formData.append('__RequestVerificationToken', token);
                    
                    const req = await fetch(url, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                        body: formData.toString()
                    });
                    return await req.text();
                }''', {"url": url, "token": token, "dateStr": current_date_str})
                
                if data_str and len(data_str) > 20 and "[[],[]]" not in data_str:
                    return data_str, current_date_str
                    
                try:
                    dt = datetime.strptime(current_date_str, "%d/%m/%Y")
                    dt -= timedelta(days=1)
                    current_date_str = dt.strftime("%d/%m/%Y")
                except Exception as e:
                    break
            return data_str, current_date_str

        foreign_data_str, foreign_date = await fetch_data_with_retry(page, '/data/KQGDGiaoDichNDTNNTopStockFilter', token, foreign_date)
        prop_data_str, prop_date = await fetch_data_with_retry(page, '/data/KQGDGiaoDichTuDoanhTopStockFilter', token, prop_date)
         
        await browser.close()
        
        # 5. Parse JSON and write to CSV
        output_dir = os.path.dirname(os.path.abspath(__file__))
        
        def save_to_csv(data_str, prefix, date_str):
            try:
                data = json.loads(data_str)
            except Exception as e:
                return
            
            buy_rows = []
            sell_rows = []
            
            if len(data) > 0 and isinstance(data[0], list):
                # Buys
                for item in data[0]:
                    symbol = item.get("StockCode")
                    val = item.get("GTBuyRong_Total") or item.get("GTBuyRong") or 0
                    if symbol:
                        buy_rows.append({"Date": date_str, "StockSymbol": symbol, "NetTradingValue": val})
            
            if len(data) > 1 and isinstance(data[1], list):
                # Sells
                for item in data[1]:
                    symbol = item.get("StockCode")
                    val = item.get("GTSellRong_Total") or item.get("GTSellRong") or 0
                    val = abs(val) if val else 0
                    if symbol:
                        sell_rows.append({"Date": date_str, "StockSymbol": symbol, "NetTradingValue": val})
                        
            # Write Buy CSV
            buy_filepath = os.path.join(output_dir, f"{prefix}_buy.csv")
            with open(buy_filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['Date', 'StockSymbol', 'NetTradingValue']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for row in buy_rows:
                    writer.writerow(row)
            
            # Write Sell CSV
            sell_filepath = os.path.join(output_dir, f"{prefix}_sell.csv")
            with open(sell_filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['Date', 'StockSymbol', 'NetTradingValue']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for row in sell_rows:
                    writer.writerow(row)
            
            return buy_rows, sell_rows
            
        f_buy, f_sell = save_to_csv(foreign_data_str, "foreign_net_trading", foreign_date)
        p_buy, p_sell = save_to_csv(prop_data_str, "prop_net_trading", prop_date)
        
        # 6. Combine all outputs into one single file
        combined_filepath = os.path.join(output_dir, "combined_net_trading.csv")
        with open(combined_filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = ['Date', 'StockSymbol', 'NetTradingValue', 'InvestorType', 'TradeDirection']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            def write_rows(rows, investor, direction):
                for row in (rows or []):
                    row['InvestorType'] = investor
                    row['TradeDirection'] = direction
                    writer.writerow(row)
                    
            write_rows(f_buy, 'Nhà đầu tư nước ngoài', 'Mua ròng')
            write_rows(f_sell, 'Nhà đầu tư nước ngoài', 'Bán ròng')
            write_rows(p_buy, 'Tự doanh', 'Mua ròng')
            write_rows(p_sell, 'Tự doanh', 'Bán ròng')

if __name__ == "__main__":
    asyncio.run(run())
