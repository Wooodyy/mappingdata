from fastapi import FastAPI, Request, File, UploadFile, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from processors import PROCESSORS
from data_handler import RawDataRequest, handle_raw_data

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
            "containers": storage.containers,  # Основные данные в контейнерах
            "totals": storage.totals.__dict__,
            "calc": storage.calc.__dict__,
            "sender": storage.sender,
            "truck": storage.truck,
            "recipient": storage.recipient,
            "buyer": storage.buyer,
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

# Endpoint для сохранения данных
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
