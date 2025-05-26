import asyncio
import json
import aiohttp
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import os

app = FastAPI()

stored_data = {}
previous_data = {}


API_URL = os.getenv("API_URL")  # Should point to your own API URL (e.g., http://localhost:8000 or your deployed url)

def is_empty(data):
    return not any(data.values())

@app.post("/api/upload")
async def upload(request: Request):
    global stored_data, previous_data
    new_data = await request.json()

    if not is_empty(new_data):
        previous_data = stored_data.copy()
        stored_data.update({
            k: v if v else stored_data.get(k, []) for k, v in new_data.items()
        })

    return {"status": "success", "received_items": len(new_data)}

@app.get("/api/data", response_class=JSONResponse)
async def get_data():
    return stored_data if not is_empty(stored_data) else previous_data

@app.get("/view", response_class=HTMLResponse)
async def view_data():
    data = stored_data if not is_empty(stored_data) else previous_data

    def render_column(title, items):
        rows = "".join(
            f"<div class='item'><span>{item['name']}</span><span>{item['quantity']}</span></div>"
            for item in items
        )
        return f"<div class='column'><h2>{title}</h2>{rows}</div>"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; text-align: center; }}
            .container {{ display: flex; justify-content: space-around; }}
            .column {{ border: 1px solid #ccc; padding: 10px; width: 30%; }}
            .column h2 {{ text-align: center; }}
            .item {{ display: flex; justify-content: space-between; margin-bottom: 5px; }}
        </style>
    </head>
    <body>
        <h1>Garden Stock</h1>
        <div class="container">
            {render_column("Seeds", data.get("seeds", []))}
            {render_column("Gear", data.get("gears", []))}
            {render_column("Eggs", data.get("eggs", []))}
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

async def scrape_and_send():
    try:
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

        # Post scraped data to your own API upload endpoint
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{API_URL}/api/upload", json=data) as resp:
                resp_json = await resp.json()
                print("Server response:", resp_json)

    except Exception as e:
        print("Error during scraping:", e)

async def periodic_scrape():
    while True:
        await scrape_and_send()
        await asyncio.sleep(10)  # Run every 10 seconds

@app.on_event("startup")
async def startup_event():
    if not API_URL:
        print("Warning: API_URL env var not set, scraper will NOT run.")
    else:
        asyncio.create_task(periodic_scrape())
