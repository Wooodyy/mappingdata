from fastapi import FastAPI, Request, File, UploadFile, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from src.processors import PROCESSORS
from src.compare import COMPARE_HANDLERS
from src.models import RawDataRequest
from src.services import handle_raw_data, DataHandler
from src.database import init_db_pool, save_data_to_db

# Загружаем переменные окружения
load_dotenv()

# Настраиваем фильтр для uvicorn.access логгера, чтобы не показывать 404
import logging

class No404Filter(logging.Filter):
    def filter(self, record):
        # Фильтруем записи с 404 статусом (проверяем и атрибут, и сообщение)
        if hasattr(record, 'status_code') and record.status_code == 404:
            return False
        if hasattr(record, 'getMessage'):
            message = record.getMessage()
            if '404' in message and 'Not Found' in message:
                return False
        return True

# Применяем фильтр к access логгеру
logging.getLogger("uvicorn.access").addFilter(No404Filter())

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: инициализация БД
    try:
        init_db_pool()
        print("База данных успешно инициализирована")
    except Exception as e:
        print(f"Предупреждение: не удалось инициализировать БД: {e}")
        print("Приложение будет работать без сохранения в БД")
    yield
    # Shutdown: закрытие соединений (если нужно)

app = FastAPI(title="Mapping Data API", version="1.0.0", lifespan=lifespan)

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
    Принимает сырые данные, преобразует их и сохраняет в БД и JSON файл
    """
    try:
        # Отладочная информация
        print(f"Получены данные: containers={len(request.containers)}, sender_name='{request.sender_name}', recipient_name='{request.recipient_name}'")
        print(f"Адреса: sender_address='{request.sender_address}', recipient_address='{request.recipient_address}'")
        print(f"Инвойс: invoice='{request.invoice}', date_invoice='{request.date_invoice}'")
        
        # Подготавливаем данные через DataHandler
        handler = DataHandler()
        prepare_result = handler.prepare_data(request)
        
        if not prepare_result["success"]:
            return JSONResponse(
                content=prepare_result,
                status_code=400
            )
        
        # Валидация обязательных полей для БД
        if not request.client_name or not request.order_number:
            return JSONResponse(
                content={
                    "success": False,
                    "error": "client_name и order_number обязательны для сохранения в БД"
                },
                status_code=400
            )
        
        # Сохраняем в БД
        db_result = None
        try:
            db_result = save_data_to_db(
                handler.prepared_data,
                client_name=request.client_name,
                order_number=request.order_number
            )
            if not db_result["success"]:
                error_msg = db_result.get('error', 'Неизвестная ошибка')
                print(f"Предупреждение: не удалось сохранить в БД: {error_msg}")
        except Exception as db_error:
            error_msg = str(db_error)
            print(f"Исключение при сохранении в БД: {error_msg}")
            import traceback
            traceback.print_exc()
            db_result = {
                "success": False,
                "error": error_msg
            }
        
        # Сохраняем JSON файл (для обратной совместимости)
        json_result = handler.save_json_file()
        
        # Формируем ответ
        response = {
            "success": True,
            "message": "Данные успешно сохранены",
            "containers_processed": prepare_result["containers_processed"]
        }
        
        if db_result and db_result["success"]:
            response["message"] += " в базу данных"
            response["db_saved"] = True
            response["containers_saved_to_db"] = db_result.get("containers_saved", 0)
        else:
            response["db_saved"] = False
            if db_result:
                response["db_error"] = db_result.get("error", "Неизвестная ошибка")
        
        if json_result["success"]:
            response["filename"] = json_result.get("filename")
            response["download_url"] = f"/download/{json_result.get('filename')}"
        
        return response
            
    except Exception as e:
        print(f"Критическая ошибка при обработке данных: {e}")
        import traceback
        traceback.print_exc()
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
