from fastapi import FastAPI, Request, File, UploadFile, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from processors import PROCESSORS

app = FastAPI()
templates = Jinja2Templates(directory="templates")

static_dir = Path("static")
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "upload.html",
        {"request": request, "processors": list(PROCESSORS.keys())}
    )

@app.post("/upload")
async def upload_file(sender: str = Form(...), file: UploadFile = File(...)):
    processor = PROCESSORS.get(sender.strip().lower())
    if processor is None:
        return {"error": f"Алгоритм для отправителя '{sender}' ещё не готов"}

    contents = await file.read()
    result = processor(contents)

    if "error" in result:
        return result

    # Возвращаем обработанные данные клиенту для сохранения в localStorage
    storage = result["storage"]
    return {
        "success": True,
        "data": {
            "rows": [row.data for row in storage.rows],
            "containers": storage.containers,  # Добавляем сгруппированные данные
            "totals": storage.totals.__dict__,
            "calc": storage.calc.__dict__,
            "sender": storage.sender,
            "truck": storage.truck,
            "recipient": storage.recipient,
        }
    }

# Страница с таблицей
@app.get("/table", response_class=HTMLResponse)
async def table_page(request: Request):
    return templates.TemplateResponse("table.html", {"request": request})

# Этот endpoint больше не используется, данные хранятся в localStorage
@app.get("/table/json")
async def get_table_json():
    return JSONResponse(
        content={
            "error": "Данные больше не хранятся на сервере. Используйте localStorage.",
            "message": "Data is now stored in localStorage for each user separately."
        },
        status_code=410
    )
