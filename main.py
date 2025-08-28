from fastapi import FastAPI, Request, File, UploadFile, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from processors import PROCESSORS
from models import ExcelData, Totals

app = FastAPI()
templates = Jinja2Templates(directory="templates")

static_dir = Path("static")
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Хранилище данных
storage: ExcelData = ExcelData(rows=[], totals=Totals(), sender="")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "upload.html",
        {"request": request, "processors": PROCESSORS.keys()}
    )

@app.post("/upload")
async def upload_file(sender: str = Form(...), file: UploadFile = File(...)):
    global storage

    processor = PROCESSORS.get(sender.strip().lower())
    if processor is None:
        return {"error": f"Алгоритм для отправителя '{sender}' ещё не готов"}

    contents = await file.read()
    result = processor(contents)

    if "error" in result:
        return result

    storage = result["storage"]
    return {"success": True}

# Страница с таблицей
@app.get("/table", response_class=HTMLResponse)
async def table_page(request: Request):
    return templates.TemplateResponse("table.html", {"request": request})

# JSON с данными для таблицы
@app.get("/table/json")
async def get_table_json():
    return JSONResponse(
        content={
            "rows": [row.data for row in storage.rows],
            "totals": storage.totals.__dict__,
            "sender": storage.sender
        }
    )
