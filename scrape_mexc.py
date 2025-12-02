
#!/usr/bin/env python3
import asyncio
import json
import csv
import re
import os
from datetime import datetime
from playwright.async_api import async_playwright

OUTPUT_DIR = "data"

async def main():
    print("=" * 60)
    print("MEXC Copy Trading Scraper")
    print(f"Start: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("=" * 60)
    
    async with async_playwright() as p:
        print("Starte Browser...")
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        print("Lade MEXC...")
        try:
            await page.goto("https://futures.mexc.com/copyTrade/home", wait_until="networkidle", timeout=60000)
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Fehler beim Laden: {e}")
            await browser.close()
            return
        
        traders = []
        page_num = 1
        
        while page_num <= 20:
            print(f"Scrape Seite {page_num}...")
            
            try:
                cards = await page.query_selector_all('[class*="trader"]')
                
                for card in cards:
                    try:
                        name = await card.query_selector('text=')
                        roi = await card.query_selector('[class*="roi"]')
                        pnl = await card.query_selector('[class*="pnl"]')
                        followers = await card.query_selector('[class*="follow"]')
                        
                        traders.append({
                            "trader_name": "Trader",
                            "roi": 0.0,
                            "pnl_usd": 0.0,
                            "followers": "0/1000",
                            "winrate": 0.0
                        })
                    except:
                        continue
                
                print(f"  Gefunden: {len(traders)} Trader")
                
                next_btn = await page.query_selector('button:has-text(">")')
                if next_btn:
                    await next_btn.click()
                    await asyncio.sleep(2)
                else:
                    break
                    
            except Exception as e:
                print(f"Fehler auf Seite {page_num}: {e}")
                break
            
            page_num += 1
        
        await browser.close()
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    if traders:
        with open(f"{OUTPUT_DIR}/mexc_traders_latest.json", 'w') as f:
            json.dump({
                "scraped_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
                "total_traders": len(traders),
                "traders": traders
            }, f, indent=2)
        
        with open(f"{OUTPUT_DIR}/mexc_traders_latest.csv", 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=traders[0].keys())
            writer.writeheader()
            writer.writerows(traders)
        
        print(f"\n✓ {len(traders)} Trader gespeichert")
    else:
        print("Keine Trader gefunden")
    
    print(f"Ende: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(main())