from fastapi import FastAPI, Request, File, UploadFile
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
from pydantic import BaseModel
from typing import List
from pathlib import Path
import io

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Check if static directory exists, if not create it
static_dir = Path("static")
if not static_dir.exists():
    static_dir.mkdir(parents=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

class ExcelRow(BaseModel):
    data: dict
    sheet: str

class Totals(BaseModel):
    total_quantity: float = 0
    total_weight: float = 0
    total_amount: float = 0
 
class ExcelData(BaseModel):
    rows: List[ExcelRow]
    totals: Totals

storage: ExcelData = ExcelData(rows=[], totals=Totals())

def process_excel(file_content: bytes):
    global storage
    storage = ExcelData(rows=[], totals=Totals())

    column_mapping = {
        "Xinjiang Xindudu \nImport and Export Trading Co.,Ltd": "Наименование/модель",
        "Unnamed: 1": "Код ТН ВЭД",
        "Unnamed: 2": "Кол-во мест",
        "Unnamed: 5": "Общий вес брутто",
        "Unnamed: 6": "Общая сумма"
    }

    try:
        sheets = pd.read_excel(io.BytesIO(file_content), sheet_name=None)
        
        # Определяем валюту, проверяя все листы на наличие CNY
        currency = "USD"
        for sheet_name, df in sheets.items():
            df_str = df.to_string().lower()
            
            if 'cny' in df_str or any('cny' in str(col).lower() for col in df.columns):
                currency = "CNY"
                break
        
        print(f"Selected currency: {currency}")
        
        for sheet_name, df in sheets.items():
            start_idx = df[df.iloc[:, 0] == "Наименование/модель"].index
            
            if len(start_idx) > 0:
                df = df.iloc[start_idx[0]:]
                df = df.reset_index(drop=True)
                df.rename(columns=column_mapping, inplace=True)
                
                # Extract and store totals from the last row
                last_row = df.iloc[-1]
                storage.totals = Totals(
                    total_quantity=float(last_row["Кол-во мест"]),
                    total_weight=float(last_row["Общий вес брутто"]),
                    total_amount=float(last_row["Общая сумма"])
                )
                
                # Process regular rows (excluding header and totals)
                records = df.iloc[1:-1].to_dict(orient="records")
                for record in records:
                    ordered_record = {
                        "Код ТН ВЭД": record.get("Код ТН ВЭД", ""),
                        "Наименование/модель": record.get("Наименование/модель", ""),
                        "Кол-во мест": record.get("Кол-во мест", 0),
                        "Общий вес брутто": record.get("Общий вес брутто", 0),
                        "Общая сумма": record.get("Общая сумма", 0),
                        "Тип валюты": currency
                    }
                    storage.rows.append(ExcelRow(data=ordered_record, sheet=sheet_name))

    except Exception as e:
        return {"error": str(e)}
    
    return {"success": True}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "upload.html",
        {"request": request}
    )

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    result = process_excel(contents)
    return result

@app.get("/table", response_class=HTMLResponse)
async def get_table(request: Request):
    return templates.TemplateResponse(
        "table.html",
        {"request": request, "data": storage.rows, "totals": storage.totals}
    )