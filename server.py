from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from ticker_prices import get_tickers_ccl_df
from settings import tickers
import uvicorn
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime

df = None
updated_time: str = ""

async def update_df():
    global df
    global updated_time
    while True:
        df = get_tickers_ccl_df(tickers)
        updated_time = datetime.now().strftime("%H:%M:%S")
        await asyncio.sleep(60)  # Wait for 60 seconds before updating again

@asynccontextmanager
async def lifespan(app: FastAPI):
    global df
    asyncio.create_task(update_df())
    yield
    df = None

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    global df
    global updated_time
    if df is None:
        raise HTTPException(status_code=500, detail="DataFrame not initialized yet")
    table_html = df.to_html(classes='table table-striped', index=False)

    return templates.TemplateResponse("index.html", {"request": request, "table_html": table_html, "updated_time": updated_time})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)