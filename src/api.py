from fastapi import FastAPI, Request, File, UploadFile, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
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
        {"request": request}
    )

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Используем только единый алгоритм
    processor = PROCESSORS["единый шаблон"]
    
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
            "container_info": storage.container_info,  # Информация об отправителе и получателе для каждого контейнера
            "totals": storage.totals.__dict__,
            "calc": storage.calc.__dict__,
            "sender_name": storage.sender_name,
            "sender_address": storage.sender_address,
            "recipient_name": storage.recipient_name,
            "recipient_address": storage.recipient_address, 
            "invoice": storage.invoice,
            "date_invoice": storage.date_invoice,
        }
    }

@app.get("/table", response_class=HTMLResponse)
async def table_page(request: Request):
    return templates.TemplateResponse("table.html", {"request": request})

@app.get("/compare", response_class=HTMLResponse)
async def compare_page(request: Request):
    return templates.TemplateResponse(
        "compare.html",
        {"request": request}
    )

@app.post("/compare")
async def compare_files(
    invoice: UploadFile = File(...),
    declaration: UploadFile = File(...),
):
    # Используем только единый алгоритм сравнения
    handler = COMPARE_HANDLERS["единый шаблон"]

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
        # Отладочная информация
        print(f"Получены данные: containers={len(request.containers)}, sender_name='{request.sender_name}', recipient_name='{request.recipient_name}'")
        print(f"Адреса: sender_address='{request.sender_address}', recipient_address='{request.recipient_address}'")
        print(f"Инвойс: invoice='{request.invoice}', date_invoice='{request.date_invoice}'")
        
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

@app.get("/download/{filename}")
async def download_file(filename: str):
    """
    Endpoint для скачивания JSON файла
    """
    try:
        file_path = os.path.join("static", "downloads", filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Файл не найден")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/json'
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при скачивании файла: {str(e)}")
