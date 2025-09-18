import pandas as pd
import io
from src.models import ExcelData, Totals, Calc
from src.gemini_api import detect_currency, detect_recipient, detect_sender

def process_testoviy(file_content: bytes) -> dict:
    
    storage = ExcelData(containers={}, totals=Totals(), truck="", calc=Calc(), recipient="", sender="")

    column_mapping = {
        "Unnamed: 0": "No",
        "Unnamed: 1": "Case No",
        "Unnamed: 2": "Part No",
        "Unnamed: 3": "Part Name",
        "Unnamed: 4": "Part Name(RUS)",
        "Unnamed: 5": "Qty",
        "Unnamed: 6": "Unit Price",
        "Unnamed: 7": "Amount",
        "Unnamed: 8": "Производитель",
        "Unnamed: 9": "Страна происхождения",
        "Unnamed: 10": "Товарный знак",
        "Unnamed: 11": "HS Code",
        "Unnamed: 12": "Order No",
        "Unnamed: 13": "Container No",
        "Unnamed: 14": "Case total N/W",
        "Unnamed: 15": "Case total G/W"
    }

    try:
        # Читаем Excel файл
        sheets = pd.read_excel(io.BytesIO(file_content), sheet_name=None)


    except Exception as e:
        return {"error": str(e)}

    # Возвращаем результат обработки
    return {"success": True, "storage": storage}

