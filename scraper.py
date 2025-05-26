import asyncio
import json
import aiohttp
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import os

API_URL = os.getenv("API_URL")  # Set this in Render environment variables

async def scrape_and_send():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://growagardenvalues.com/stock/stocks.php", timeout=60000)
        await page.wait_for_selector(".stock-sections-grid", timeout=10000)
        await page.wait_for_selector(".stock-item", timeout=10000)
        await page.wait_for_selector(".item-name", timeout=10000)
        await page.wait_for_selector(".item-quantity", timeout=10000)
        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")

    def extract_items(section_id):
        section = soup.find(id=section_id)
        items = []
        if section:
            stock_items = section.select(".stock-item")
            for item in stock_items:
                name = item.select_one(".item-name")
                quantity = item.select_one(".item-quantity")
                if name and quantity:
                    items.append({
                        "name": name.get_text(strip=True),
                        "quantity": quantity.get_text(strip=True)
                    })
        return items

    data = {
        "gears": extract_items("gear-section"),
        "seeds": extract_items("seeds-section"),
        "eggs": extract_items("eggs-section")
    }

    print("Scraped data:", json.dumps(data, indent=4))

    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL + "/api/upload", json=data) as resp:
            resp_json = await resp.json()
            print("Server response:", resp_json)

if __name__ == "__main__":
    if not API_URL:
        print("Error: Please set the API_URL environment variable.")
    else:
        asyncio.run(scrape_and_send())
