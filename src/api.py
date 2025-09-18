from fastapi import FastAPI, Request, File, UploadFile, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from src.processors import PROCESSORS
from src.compare import COMPARE_HANDLERS
from src.models import RawDataRequest
from src.services import handle_raw_data

app = FastAPI(title="Mapping Data API", version="1.0.0")

# Настройка статических файлов
static_dir = Path("static")
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Настройка папки assets для иконок
assets_dir = Path("assets")
assets_dir.mkdir(parents=True, exist_ok=True)
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# Настройка шаблонов
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "upload.html",
        {"request": request, "processors": list(PROCESSORS.keys()), "compare_senders": list(COMPARE_HANDLERS.keys())}
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
            "containers": storage.containers,  # Основные данные в контейнерах
            "totals": storage.totals.__dict__,
            "calc": storage.calc.__dict__,
            "sender": storage.sender,
            "truck": storage.truck,
            "recipient": storage.recipient,
            "buyer": storage.buyer,
        }
    }

@app.get("/table", response_class=HTMLResponse)
async def table_page(request: Request):
    return templates.TemplateResponse("table.html", {"request": request})

@app.get("/compare", response_class=HTMLResponse)
async def compare_page(request: Request):
    return templates.TemplateResponse(
        "compare.html",
        {"request": request, "compare_senders": list(COMPARE_HANDLERS.keys())}
    )

@app.post("/compare")
async def compare_files(
    sender: str = Form(...),
    invoice: UploadFile = File(...),
    declaration: UploadFile = File(...),
):
    handler = COMPARE_HANDLERS.get(sender.strip().lower())
    if handler is None:
        return {"success": False, "error": f"Алгоритм сравнения для '{sender}' ещё не готов"}

    invoice_bytes = await invoice.read()
    decl_bytes = await declaration.read()

    result = handler(invoice_bytes, decl_bytes, invoice.filename, declaration.filename)
    return result

@app.get("/table/json")
async def get_table_json():
    return JSONResponse(
        content={
            "error": "Данные больше не хранятся на сервере. Используйте localStorage.",
            "message": "Data is now stored in localStorage for each user separately."
        },
        status_code=410
    )

@app.post("/save")
async def save_data(request: RawDataRequest):
    """
    Endpoint для сохранения данных из localStorage
    Принимает сырые данные и преобразует их в формат 1.json на сервере
    """
    try:
        # Используем функцию для обработки сырых данных
        result = handle_raw_data(request)
        
        if result["success"]:
            return result
        else:
            return JSONResponse(
                content=result,
                status_code=400
            )
            
    except Exception as e:
        print(f"Критическая ошибка при обработке данных: {e}")
        return JSONResponse(
            content={"success": False, "error": f"Критическая ошибка: {str(e)}"},
            status_code=500
        )
