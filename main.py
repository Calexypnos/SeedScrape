import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

app = FastAPI()

stored_data = {}
previous_data = {}

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

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
