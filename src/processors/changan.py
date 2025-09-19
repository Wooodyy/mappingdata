import pandas as pd
import io
from src.models import ExcelData, Totals, Calc
from src.gemini_api import detect_currency, detect_recipient, detect_sender

def process_changan(file_content: bytes) -> dict:
    
    storage = ExcelData(containers={}, totals=Totals(), truck="", calc=Calc(), recipient="", sender="")
    
    column_mapping = {
        "Unnamed: 2": "Код ТН ВЭД",
        "Unnamed: 1": "Коммерческое описание товара",
        "Unnamed: 3": "VIN",
        "Unnamed: 7": "Дата выпуска",
        "Unnamed: 9": "Количество грузовых мест",
        "Unnamed: 12": "Вес брутто",
        "Unnamed: 13": "Сумма",
        }

    try:
        # Читаем Excel файл
        sheets = pd.read_excel(io.BytesIO(file_content), sheet_name=None)
        #print(sheets[list(sheets.keys())[0]].iloc[0:10, 0:6].reset_index(drop=True).to_string())    
        
        # Используем самый первый лист в файле и извлекаем нужные данные начиная с 12-й строки и 2 по 18 столбец
        df = sheets[list(sheets.keys())[0]].iloc[12:, 1:18].reset_index(drop=True)

        df.rename(columns=column_mapping, inplace=True)
        # Оставляем только нужные столбцы из column_mapping
        df = df[list(column_mapping.values())]
        
        # Вырежь от начала до первой строки, где "Код ТН ВЭД" не может быть преобразован в число или равен NaN
        def is_not_number_or_nan(val):
            try:
                if pd.isna(val):
                    return True
                float(str(val).replace(" ", ""))
                return False
            except (ValueError, TypeError):
                return True

        cut_idx = None
        for idx, val in enumerate(df["Код ТН ВЭД"]):
            if is_not_number_or_nan(val):
                cut_idx = idx
                break

        if cut_idx is not None:
            df = df.iloc[:cut_idx].reset_index(drop=True)
        
        # Определяем валюту
        currency = "USD"  # значение по умолчанию
        df_for_ai = sheets[list(sheets.keys())[0]].iloc[11:, 1:18].reset_index(drop=True)
        if len(df_for_ai) >= 4:
            invoice_content = df_for_ai.to_string()
            currency = detect_currency(invoice_content)
            
        # Определяем отправителя
        sender = "Не опознан"  # значение по умолчанию
        sender_value = sheets[list(sheets.keys())[0]].iloc[5]["Unnamed: 2"]
        sender_value = sender_value.split("\n")
        sender = sender_value[0]+" \n "+sender_value[1]+" \n "+sender_value[2]
        storage.sender = sender
        
        # Определяем получателя
        recipient = "Не опознан"  # значение по умолчанию
        recipient_value = sheets[list(sheets.keys())[0]].iloc[3]["Unnamed: 2"]
        recipient_value = recipient_value.split("\n")
        recipient = " \n ".join([str(x) for x in recipient_value if str(x).strip() != ""])
        storage.recipient = recipient
        
        # Определяем покупателя
        buyer = "Не опознан"  # значение по умолчанию
        buyer_value = sheets[list(sheets.keys())[0]].iloc[5]["Unnamed: 12"]
        buyer_value = buyer_value.split("\n")
        storage.buyer = buyer_value[0]
        
        # Определяем контейнер
        truck = "Не опознан"  # значение по умолчанию
        truck_value = sheets[list(sheets.keys())[0]].iloc[9]["Unnamed: 2"]
        storage.truck = truck_value
        
        # Обрабатываем строки данных (кроме последней, если она итоги)
        data_rows = df  # df уже обрезан выше
        calculated_total_quantity = 0
        calculated_total_weight = 0
        calculated_total_amount = 0
        
        # Определяем номер контейнера для группировки
        container_no = storage.truck.strip()
        if not container_no:
            container_no = "Без номера контейнера"
        
        # Инициализируем контейнер если его еще нет
        if container_no not in storage.containers:
            storage.containers[container_no] = []

        for _, row in data_rows.iterrows():
            # Создаем запись с данными (убираем все NaN значения для JSON совместимости)
            item_name=row.get("Коммерческое описание товара", "")
            item_name=item_name.split("\n")
            date = row.get("Дата выпуска", "")
            try:
                date_str = "" if pd.isna(date) or date == "" else pd.to_datetime(date, errors="coerce").strftime("%d.%m.%Y") if not pd.isna(pd.to_datetime(date, errors="coerce")) else str(date)
            except Exception:
                date_str = str(date)
            
            
            item_name = item_name[0] + " VIN:" + row.get("VIN", "") + " Дата выпуска:" + date_str
            
            record_data = {
                "Код ТН ВЭД": row.get("Код ТН ВЭД", ""),
                "Коммерческое описание товара": item_name,
                "Признак товара, свободного от применения запретов и ограничений (всегда 1)": 1,
                "Информация об упаковке (0-БЕЗ, 1 С)": 1,
                "Количество грузовых мест": row.get("Количество грузовых мест", 0) if not pd.isna(row.get("Количество грузовых мест", 0)) else 0,
                "Вид информации об упаковке (всегда 0)": 0,
                "Вид упаковки ": "PP",
                "Количество упаковок": row.get("Количество грузовых мест", 0) if not pd.isna(row.get("Количество грузовых мест", 0)) else 0,
                "Номер контейнера": storage.truck,
                "Вес брутто": round(float(row.get("Вес брутто", 0)), 2) if not pd.isna(row.get("Вес брутто", 0)) else 0,
                "Валюта": currency,
                "Сумма": round(float(row.get("Сумма", 0)), 2)*row.get("Количество грузовых мест", 0) if not pd.isna(row.get("Сумма", 0)) else 0,
            }
            calculated_total_quantity += float(record_data["Количество грузовых мест"])
            calculated_total_weight += float(record_data["Вес брутто"])
            calculated_total_amount += float(record_data["Сумма"])
            
            # Добавляем данные напрямую в контейнер
            storage.containers[container_no].append(record_data)

        # Итоги
        storage.calc = Calc(
            calc_quantity=calculated_total_quantity,
            calc_weight=calculated_total_weight,
            calc_amount=calculated_total_amount
        )
        
        storage.totals = Totals(
            total_quantity=calculated_total_quantity,
            total_weight=calculated_total_weight,
            total_amount=calculated_total_amount
        )
        
        # Обновляем информацию о контейнерах
        storage.truck = f"Количество контейнеров: {len(storage.containers)}"

    except Exception as e:
        return {"error": str(e)}

    # Возвращаем результат обработки
    return {"success": True, "storage": storage}

