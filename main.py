import asyncio
import json
import aiohttp
import re
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import os
import traceback

app = FastAPI()

stored_data = {}
previous_data = {}
weather_data = {}

API_URL = os.getenv("API_URL", "https://seedscrape.onrender.com")

# Emoji mapping based on item name
def get_emoji(name: str) -> str:
    t = name.lower()
    return (
        "\U0001F6BF" if "watering can" in t else
        "\U0001FA9A" if "trowel" in t else
        "\U0001F527" if "recall wrench" in t else
        "\U0001F9FF" if "basic sprinkler" in t else
        "\U0001F4A6" if "advanced sprinkler" in t else
        "\U0001F52B" if "godly sprinkler" in t else
        "\U0001F40A" if "master sprinkler" in t else
        "⚔️" if "lightning rod" in t else
        "\U0001F6E1" if "favorite tool" in t else
        "\U0001F4A6" if "sprinkler" in t else
        "\U0001F528" if "tool" in t else
        "\U0001F95A" if "common egg" in t else
        "\U0001F9F6" if "uncommon egg" in t else
        "\U0001F535" if "rare egg" in t else
        "\U0001F98E" if "bug egg" in t else
        "\U0001F9E8" if "legendary egg" in t else
        "\U0001F52E" if "mythical egg" in t else
        "\U0001F95A" if "egg" in t else
        "\U0001F955" if "carrot" in t else
        "\U0001F353" if "strawberry" in t else
        "\U0001FAD0" if "blueberry" in t else
        "\U0001F337" if "orange tulip" in t or "tulip" in t else
        "\U0001F345" if "tomato" in t else
        "\U0001F33D" if "corn" in t else
        "\U0001F33C" if "daffodil" in t else
        "\U0001F349" if "watermelon" in t else
        "\U0001F383" if "pumpkin" in t else
        "\U0001F34E" if "apple" in t else
        "\U0001F38D" if "bamboo" in t else
        "\U0001F965" if "coconut" in t else
        "\U0001F335" if "cactus" in t else
        "\U0001F409" if "dragon fruit" in t else
        "\U0001F96D" if "mango" in t else
        "\U0001F347" if "grape" in t else
        "\U0001F344" if "mushroom" in t else
        "\U0001F336" if "pepper" in t else
        "\U0001F36B" if "cacao" in t else
        "\U0001F331" if "beanstalk" in t else
        "📦"
    )

def is_empty(data):
    return not any(data.get(k) for k in ["gears", "seeds", "eggs"])

def format_item(item: str) -> dict:
    """Extract name for emoji and format display by removing **."""
    try:
        # Extract name before **xN** (e.g., "Carrot" from "Carrot **x21**")
        match = re.match(r"^(.*?)\s*\*\*x(\d+)\*\*$", item.strip())
        if match:
            name, quantity = match.groups()
            display = f"{name.strip()} x{quantity}"
        else:
            name = item.strip()
            display = name
        return {"display": display, "emoji": get_emoji(name)}
    except Exception as e:
        print(f"Error formatting item '{item}': {e}")
        return {"display": item, "emoji": "📦"}

@app.post("/api/upload")
async def upload(request: Request):
    global stored_data, previous_data
    try:
        new_data = await request.json()
        print("Received upload data:", json.dumps(new_data, indent=2))
        processed_data = {"gears": [], "seeds": [], "eggs": []}
        # Process items and normalize category names
        for category, api_category in [("gears", "gear"), ("seeds", "seeds"), ("eggs", "egg")]:
            items = new_data.get(api_category, new_data.get(category, []))
            if isinstance(items, list):
                processed_data[category] = [item for item in items if isinstance(item, str)]
                print(f"Items for {category}:", json.dumps(processed_data[category], indent=2))
            else:
                print(f"Invalid or missing category {api_category}/{category}: {items}")

        if any(processed_data[category] for category in ["gears", "seeds", "eggs"]):
            previous_data = stored_data.copy()
            stored_data.clear()
            stored_data.update(processed_data)
            print("Updated stored_data:", json.dumps(stored_data, indent=2))
        else:
            print("No valid data to update (empty or invalid categories)")
        total_items = sum(len(v) for v in processed_data.values() if isinstance(v, list))
        return {"status": "success", "received_items": total_items}
    except Exception as e:
        print(f"Error in /api/upload: {str(e)}", traceback.format_exc())
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})

@app.get("/api/data", response_class=JSONResponse)
async def get_data():
    data = stored_data if not is_empty(stored_data) else previous_data
    print("Serving /api/data:", json.dumps(data, indent=2))
    return data

@app.get("/api/weather", response_class=JSONResponse)
async def get_weather():
    print("Serving /api/weather:", json.dumps(weather_data, indent=2))
    return weather_data or {"status": "unknown"}

@app.get("/view", response_class=HTMLResponse)
async def view_data():
    try:
        data = stored_data if not is_empty(stored_data) else previous_data
        if not data or not any(data.get(k) for k in ["gears", "seeds", "eggs"]):
            # Fallback sample data for debugging
            data = {
                "seeds": [
                    "Carrot **x21**", "Corn **x2**", "Strawberry **x6**", "Tomato **x2**", "Blueberry **x2**"
                ],
                "gears": [
                    "Watering Can **x1**", "Favorite Tool **x3**", "Recall Wrench **x2**", "Trowel **x3**"
                ],
                "eggs": [
                    "Common Egg **x1**", "Common Egg **x1**", "Uncommon Egg **x1**"
                ]
            }
            print("Using fallback sample data:", json.dumps(data, indent=2))
        print("Rendering /view with data:", json.dumps(data, indent=2))
        print("Weather data:", json.dumps(weather_data, indent=2))

        def render_column(title, items):
            if not items:
                return f"<div class='column'><h2>{title}</h2><p>No {title.lower()} available</p></div>"
            rows = "".join(
                f"<div class='item'><span>{format_item(item)['emoji']} {format_item(item)['display']}</span></div>"
                for item in items if isinstance(item, str)
            )
            return f"<div class='column'><h2>{title}</h2>{rows}</div>"

        weather_html = (
            f"<div class='weather'>🌤️ Weather: {weather_data.get('weatherType', 'Unknown')} - {weather_data.get('description', '')}</div>"
            if weather_data else "<div class='weather'>Weather: loading...</div>"
        )

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center;}}
                body::-webkit-scrollbar {{display: none;}}
                h1 {{font-size: 1.4em;}}
                .weather {{ font-size: 1.2em; margin-bottom: 3px; }}
                .container {{ display: flex; justify-content: space-around; flex-wrap: wrap; }}
                .column {{ border: 1px solid #ccc; width: 30%;; min-height: 100px; }}
                .column h2 {{ text-align: center; margin-bottom: 5px; }}
                .item {{ display: flex; justify-content: space-between; margin-bottom: 5px; }}
                .item span {{ font-size: 1.1em; }}
            </style>
        </head>
        <body>
            <h1>Garden Stock</h1>
            {weather_html}
            <div class="container">
                {render_column("Seeds", data.get("seeds", []))}
                {render_column("Gear", data.get("gears", []))}
                {render_column("Eggs", data.get("eggs", []))}
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html)
    except Exception as e:
        print("Error in /view endpoint:", traceback.format_exc())
        return HTMLResponse(content="<h1>Error rendering page</h1><p>An error occurred. Check server logs.</p>", status_code=500)

async def fetch_weather():
    global weather_data
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://growagardenstock.com/api/stock/weather") as resp:
                if resp.status == 200:
                    weather_data = await resp.json()
                    print("Weather updated:", json.dumps(weather_data, indent=2))
                else:
                    print(f"Error fetching weather API: {resp.status}")
    except Exception as e:
        print("Weather fetch error:", e)

async def scrape_and_send():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://growagardenstock.com/api/stock") as resp:
                if resp.status != 200:
                    print(f"Error fetching stock API: {resp.status}")
                    return
                raw_data = await resp.text()
                print("Raw stock API response:", raw_data)
                try:
                    data = json.loads(raw_data)
                except json.JSONDecodeError as e:
                    print(f"Error decoding stock API response as JSON: {e}")
                    return

                if not isinstance(data, dict):
                    print(f"Error: Stock API returned non-dictionary data: {type(data)}")
                    return

                # Map API category names to expected names
                processed_data = {
                    "gears": data.get("gear", []),
                    "seeds": data.get("seeds", []),
                    "eggs": data.get("egg", [])
                }

                # Validate items are strings
                for category in ["gears", "seeds", "eggs"]:
                    if isinstance(processed_data[category], list):
                        processed_data[category] = [item for item in processed_data[category] if isinstance(item, str)]
                        print(f"Items for {category}:", json.dumps(processed_data[category], indent=2))
                    else:
                        print(f"Error: Category '{category}' is not a list: {type(processed_data[category])}")
                        processed_data[category] = []

                print("Fetched and parsed stock data:", json.dumps(processed_data, indent=2))

                global stored_data, previous_data
                if any(processed_data.get(k) for k in ["gears", "seeds", "eggs"]):
                    previous_data = stored_data.copy()
                    stored_data.clear()
                    stored_data.update(processed_data)
                    print("Updated stored_data directly (no POST):", json.dumps(stored_data, indent=2))


    except Exception as e:
        print("Error during stock fetch/send:", traceback.format_exc())

async def periodic_tasks():
    while True:
        await asyncio.gather(scrape_and_send(), fetch_weather())
        await asyncio.sleep(10)

@app.on_event("startup")
async def startup_event():
    if not API_URL:
        print("Warning: API_URL env var not set, scraper will NOT run.")
    else:
        asyncio.create_task(periodic_tasks())
