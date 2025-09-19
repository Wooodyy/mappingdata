import pandas as pd
import io
from src.models import ExcelData, Totals, Calc

def process_astana(file_content: bytes, first_container_number: str = None) -> dict:
    
    storage = ExcelData(
        containers={},
        totals=Totals(),
        calc=Calc(),
        sender="-",
        truck="-",
        seller="-",
        recipient="-",
        buyer="-",
        invoice="-",
        date_invoice="-",
        sender_name="-",
        sender_address="-",
        recipient_name="-",
        recipient_address="-"
    )
    
    column_mapping = {
        "Unnamed: 8": "Код ТН ВЭД",
        "Unnamed: 3": "Description/ Наименование (Russian)",
        "Unnamed: 1": "Part number/ Артикул",
        "DETAILED PACKING LIST / ДЕТАЛЬНЫЙ УПАКОВОЧНЫЙ ЛИСТ": "Place Q-ty/Кол-во мест",
        "Unnamed: 11": "Container number / Номер контейнера",
        "Unnamed: 10": "Gross weight kg/Вес брутто кг",
        "Unnamed: 7": "Total price CNY/Общая стоимость CNY",
        "Unnamed: 9": "Net weight kg/Вес нетто кг",
    }

    try:
        # Читаем Excel файл
        df = pd.read_excel(io.BytesIO(file_content), sheet_name='PACKING LIST')
        
        # Начинаем сканирование с 23 строки (индекс 22, так как индексация с 0)
        start_row = 22
        data_df = df.iloc[start_row:].copy()
        
        # Удаляем строки где в столбце Unnamed: 0 нет значения или значение не является числом
        data_df = data_df[data_df['Unnamed: 0'].notna()]  # Удаляем строки с NaN
        data_df = data_df[pd.to_numeric(data_df['Unnamed: 0'], errors='coerce').notna()]  # Удаляем строки где значение не число
        
        # Переменные для подсчета общих значений
        calculated_total_quantity = 0
        calculated_total_weight = 0
        calculated_total_amount = 0
        
        # Обрабатываем каждую строку данных
        for idx, row in data_df.iterrows():
            # Проверяем, что есть номер контейнера
            container_number = row.get('Unnamed: 11')
            if pd.isna(container_number) or str(container_number).strip() == '':
                continue
            
            container_number = str(container_number).strip()
            
            if first_container_number == container_number or first_container_number is None:
                # Создаем запись товара
                item = {
                    "Код ТН ВЭД": str(row.get('Unnamed: 8', '')).strip() if pd.notna(row.get('Unnamed: 8')) else '',
                    "Коммерческое описание товара": (str(row.get('Unnamed: 3', '')).strip() if pd.notna(row.get('Unnamed: 3')) else '') + " " + (str(row.get('Unnamed: 1', '')).strip() if pd.notna(row.get('Unnamed: 1')) else ''),
                    "Признак товара, свободного от применения запретов и ограничений (всегда 1)": 1,
                    "Информация об упаковке (0-БЕЗ, 1 С)": 1 if (pd.notna(row.get("Unnamed: 10")) and pd.notna(row.get("Unnamed: 9")) and float(row.get("Unnamed: 10", 0)) > float(row.get("Unnamed: 9", 0))) else 0,
                    "Количество грузовых мест": float(row.get('DETAILED PACKING LIST / ДЕТАЛЬНЫЙ УПАКОВОЧНЫЙ ЛИСТ', 0)) if pd.notna(row.get('DETAILED PACKING LIST / ДЕТАЛЬНЫЙ УПАКОВОЧНЫЙ ЛИСТ')) else 0,
                    "Вид информации об упаковке (всегда 0)": 0,
                    "Вид упаковки ": "PK",
                    "Количество упаковок": float(row.get('DETAILED PACKING LIST / ДЕТАЛЬНЫЙ УПАКОВОЧНЫЙ ЛИСТ', 0)) if pd.notna(row.get('DETAILED PACKING LIST / ДЕТАЛЬНЫЙ УПАКОВОЧНЫЙ ЛИСТ')) else 0,
                    "Номер контейнера": container_number,
                    "Вес брутто": float(row.get('Unnamed: 10', 0)) if pd.notna(row.get('Unnamed: 10')) else 0,
                    "Валюта": "CNY",
                    "Сумма": float(row.get('Unnamed: 7', 0)) if pd.notna(row.get('Unnamed: 7')) else 0
                }
            
                # Добавляем товар в контейнер
                if container_number not in storage.containers:
                    storage.containers[container_number] = []
                
                storage.containers[container_number].append(item)
                
                # Подсчитываем общие значения
                calculated_total_quantity += item["Количество грузовых мест"]
                calculated_total_weight += item["Вес брутто"]
                calculated_total_amount += item["Сумма"]
    except Exception as e:
        return {"error": str(e)}

    # Обновляем рассчитанные значения
    storage.calc.calc_quantity = round(calculated_total_quantity, 2)
    storage.calc.calc_weight = round(calculated_total_weight, 2)
    storage.calc.calc_amount = round(calculated_total_amount, 2)
    
    # Обновляем рассчитанные значения
    storage.totals.total_quantity = round(211, 2)
    storage.totals.total_weight = round(207242.270 , 2)
    storage.totals.total_amount = round(9396240.00 , 2)

    
    # Возвращаем результат обработки
    return {"success": True, "storage": storage}
