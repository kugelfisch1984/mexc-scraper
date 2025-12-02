#!/usr/bin/env python3
"""
MEXC Copy Trading Scraper für GitHub Actions
Scraped ALLE Trader und speichert sie als JSON/CSV
"""

import asyncio
import json
import csv
import re
import os
from datetime import datetime
from playwright.async_api import async_playwright

OUTPUT_DIR = "data"
MAX_PAGES = 50
TRADERS_PER_PAGE = 20

async def scrape_all_traders():
    """Scraped alle MEXC Copy Trading Trader"""
    
    all_traders = []
    
    async with async_playwright() as p:
        print("Starte Browser...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        print("Lade MEXC Copy Trading Seite...")
        await page.goto("https://futures.mexc.com/copyTrade/home", wait_until="networkidle", timeout=60000)
        
        await asyncio.sleep(5)
        
        print("Warte auf Trader-Liste...")
        try:
            await page.wait_for_selector('[class*="trader"]', timeout=30000)
        except:
            print("Keine Trader-Elemente gefunden, versuche alternative Selektoren...")
        
        await asyncio.sleep(3)
        
        page_num = 1
        while page_num <= MAX_PAGES:
            print(f"\nScrape Seite {page_num}...")
            
            traders_on_page = await extract_traders_from_page(page)
            
            if not traders_on_page:
                print(f"Keine Trader auf Seite {page_num} gefunden - Ende erreicht")
                break
            
            all_traders.extend(traders_on_page)
            print(f"  Gefunden: {len(traders_on_page)} Trader (Gesamt: {len(all_traders)})")
            
            has_next = await click_next_page(page)
            if not has_next:
                print("Keine weitere Seite verfügbar")
                break
            
            await asyncio.sleep(2)
            page_num += 1
        
        await browser.close()
    
    seen = set()
    unique_traders = []
    for t in all_traders:
        if t['trader_name'] not in seen:
            seen.add(t['trader_name'])
            unique_traders.append(t)
    
    print(f"\n=== GESAMT: {len(unique_traders)} einzigartige Trader ===")
    return unique_traders

async def extract_traders_from_page(page):
    """Extrahiert Trader-Daten von der aktuellen Seite"""
    traders = []
    
    trader_cards = await page.query_selector_all('[class*="traderCard"], [class*="trader-card"], [class*="trader-item"]')
    
    if not trader_cards:
        trader_cards = await page.query_selector_all('[class*="trader"] > div')
    
    for card in trader_cards:
        try:
            name_el = await card.query_selector('[class*="name"], [class*="nickname"]')
            name = await name_el.inner_text() if name_el else None
            
            if not name or len(name) < 2:
                continue
            
            roi_el = await card.query_selector('[class*="roi"], [class*="ROI"]')
            roi_text = await roi_el.inner_text() if roi_el else "0"
            roi = parse_number(roi_text)
            
            pnl_el = await card.query_selector('[class*="pnl"], [class*="PNL"], [class*="profit"]')
            pnl_text = await pnl_el.inner_text() if pnl_el else "0"
            pnl = parse_number(pnl_text)
            
            followers_el = await card.query_selector('[class*="follower"], [class*="copy"]')
            followers_text = await followers_el.inner_text() if followers_el else "0/1000"
            
            followers_match = re.search(r'(\d+)\s*/\s*(\d+)', followers_text)
            if followers_match:
                followers_count = int(followers_match.group(1))
                followers_max = int(followers_match.group(2))
                followers = f"{followers_count}/{followers_max}"
            else:
                followers_count = int(parse_number(followers_text))
                followers = str(followers_count)
            
            winrate_el = await card.query