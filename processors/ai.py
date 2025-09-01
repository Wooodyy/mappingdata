import pandas as pd
import io
import re
from models import ExcelRow, ExcelData, Totals, Calc
from gemini_api import detect_currency
import json

def process_ai(file_content: bytes) -> dict:
    storage = ExcelData(rows=[], totals=Totals(), sender="", truck="", calc=Calc())

    column_mapping = {
        "Xinjiang Xindudu \nImport and Export Trading Co.,Ltd": "Наименование/модель",
        "Unnamed: 1": "Код ТН ВЭД",
        "Unnamed: 2": "Кол-во мест",
        "Unnamed: 4": "Общий вес нетто",
        "Unnamed: 5": "Общий вес брутто",
        "Unnamed: 6": "Общая сумма"
    }

    try:
        sheets = pd.read_excel(io.BytesIO(file_content), sheet_name=None)
        
        # Найдем запись, начинающуюся с 'FROM:' до конца строки
        sender = ""
        for _, df in sheets.items():
            for col in df.columns:
                for cell in df[col]:
                    if isinstance(cell, str):
                        # Разбиваем ячейку на строки
                        lines = cell.split("\n")
                        for line in lines:
                            if line.startswith("FROM:"):
                                sender = line[len("FROM:"):].strip()  # Берем текст после FROM:
                                break
                        if sender:
                            break
                if sender:
                    break
            if sender:
                break

        storage.sender = sender

        # определение валюты по документу
        # Отправляем весь Excel в ИИ для анализа
        excel_content_for_ai = ""
        for sheet_name, df in sheets.items():
            excel_content_for_ai += f"Лист: {sheet_name}\n"
            excel_content_for_ai += df.to_string() + "\n\n"

        # Отправляем в ИИ для получения валюты
        currency = detect_currency(excel_content_for_ai)

        
        # Найдем запись, начинающуюся с 'Truck:№ ' до конца строки
        truck = ""
        for _, df in sheets.items():
            for col in df.columns:
                for cell in df[col]:
                    if isinstance(cell, str):
                        # Разбиваем ячейку на строки
                        lines = cell.split("\n")
                        for line in lines:
                            if line.startswith("Truck:№ "):
                                truck = line[len("Truck:№ "):].strip()  # Берем текст после Truck:№
                                break
                        if truck:
                            break
                if truck:
                    break
            if truck:
                break
        truck = truck.replace(" ", "")
        storage.truck = truck

        for sheet_name, df in sheets.items():
            start_idx = df[df.iloc[:, 0] == "Наименование/модель"].index

            if len(start_idx) > 0:
                df = df.iloc[start_idx[0]:]
                df = df.reset_index(drop=True)
                df.rename(columns=column_mapping, inplace=True)

                # Последняя строка = итоги
                last_row = df.iloc[-1]
                storage.totals = Totals(
                    total_quantity=float(last_row.get("Кол-во мест", 0)),
                    total_weight=float(last_row.get("Общий вес брутто", 0)),
                    total_amount=float(last_row.get("Общая сумма", 0))
                )


                # Расчетные итоги - считаем вручную по данным таблицы
                calculated_total_quantity = 0
                calculated_total_weight = 0
                calculated_total_amount = 0
                
                # Считаем итоги по всем строкам данных (исключая заголовок и последнюю строку)
                data_rows = df.iloc[1:-1]
                for _, row in data_rows.iterrows():
                    calculated_total_quantity += float(row.get("Кол-во мест", 0))
                    calculated_total_weight += float(row.get("Общий вес брутто", 0))
                    calculated_total_amount += float(row.get("Общая сумма", 0))
                
                storage.calc = Calc(
                    calc_quantity=calculated_total_quantity,
                    calc_weight=calculated_total_weight,
                    calc_amount=calculated_total_amount
                )
                
                
                
                # Остальные строки
                records = df.iloc[1:-1].to_dict(orient="records")
                for record in records:
                    ordered_record = {
                        "1Код ТН ВЭД": record.get("Код ТН ВЭД", ""),
                        "1Коммерческое описание товара": record.get("Наименование/модель", ""),
                        "1Признак товара, свободного от применения запретов и ограничений (всегда 1)": 1,
                        "1Информация об упаковке (0-БЕЗ, 1 С)": 1 if record.get("Общий вес нетто", 0) < record.get("Общий вес брутто", 0) else 0,
                        "1Количество грузовых мест": record.get("Кол-во мест", 0),
                        "1Вид информации об упаковке (всегда 0)": 0,
                        "Вид упаковки ": "CT",
                        "Количество упаковок": record.get("Кол-во мест", 0),
                        "Номер контейнера": storage.truck,
                        "Вес брутто": record.get("Общий вес брутто", 0),
                        "Валюта": currency,
                        "Сумма": record.get("Общая сумма", 0)
                    }
                    storage.rows.append(ExcelRow(data=ordered_record, sheet=sheet_name))

    except Exception as e:
        return {"error": str(e)}

    # Возвращаем результат и найденный текст 'FROM:'
    return {"success": True, "storage": storage, "truck": storage.truck}
