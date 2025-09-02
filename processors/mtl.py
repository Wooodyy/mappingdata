import pandas as pd
import io
from models import ExcelRow, ExcelData, Totals, Calc

def process_mtl(file_content: bytes) -> dict:
    """
    Обрабатывает MTL Excel файл и извлекает данные из листа 'PACKING LIST(Weight)'.
    
    Структура файла:
    - Заголовки находятся в 3-й строке (индекс 2)
    - Данные начинаются с 4-й строки (индекс 3)
    
    Args:
        file_content: Содержимое Excel файла в байтах
        
    Returns:
        dict: Результат обработки с ключами 'success' и 'storage' или 'error'
    """
    storage = ExcelData(rows=[], totals=Totals(), sender="", truck="", calc=Calc(), recipient="")

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

        # Ищем лист "PACKING LIST(Weight)"
        if "PACKING LIST(Weight)" not in sheets:
            return {"error": "Лист 'PACKING LIST(Weight)' не найден"}
        
        # Получаем данные из нужного листа
        df = sheets["PACKING LIST(Weight)"].copy()
        # Проверяем минимальное количество строк
        if len(df) < 4:
            return {"error": "Недостаточно строк в данных (требуется минимум 4 строки)"}
        
        # Извлекаем данные начиная с 3-й строки (заголовки)
        df = df.iloc[2:].reset_index(drop=True)
        
        # Переименовываем колонки согласно mapping
        df.rename(columns=column_mapping, inplace=True)
        

        currency="USD"



        # Обрабатываем строки данных (пропускаем заголовки)
        data_rows = df.iloc[1:]
        calculated_total_quantity = 0
        # Извлекаем и сохраняем каждую запись
        processed_count = 0
        for _, row in data_rows.iloc[:-1].iterrows():
            # Создаем запись с данными (убираем все NaN значения для JSON совместимости)
            record_data = {
                "Код ТН ВЭД": str(row.get("HS Code", "")) if pd.notna(row.get("HS Code")) else "",
                "Case No": str(row.get("Case No", "")) if pd.notna(row.get("Case No")) else "",
                "Коммерческое описание товара": (str(row.get("Part No", "")) if pd.notna(row.get("Part No")) else "") + " " + (str(row.get("Part Name(RUS)", "")) if pd.notna(row.get("Part Name(RUS)")) else ""),
                "Признак товара, свободного от применения запретов и ограничений (всегда 1)": 1,
                "Информация об упаковке (0-БЕЗ, 1 С)": 1 if (pd.notna(row.get("Case total G/W")) and pd.notna(row.get("Case total N/W")) and float(row.get("Case total G/W", 0)) > float(row.get("Case total N/W", 0))) else 0,
                "Количество грузовых мест": 1,
                "Вид информации об упаковке (всегда 0)": 0,
                "Вид упаковки ": "CS",
                "Количество упаковок":1,
                "Номер контейнера": str(row.get("Container No", "")) if pd.notna(row.get("Container No")) else "",
                "Вес брутто": round(float(row.get("Case total G/W", 0)), 2) if pd.notna(row.get("Case total G/W")) else 0,
                "Валюта": currency,
                "Сумма": round(float(row.get("Amount", 0)), 2) if pd.notna(row.get("Amount")) else 0,

                #"No": str(row.get("No", "")) if pd.notna(row.get("No")) else "",
                #"Qty": round(float(row.get("Qty", 0)), 2) if pd.notna(row.get("Qty")) else 0,
                #"Unit Price": round(float(row.get("Unit Price", 0)), 2) if pd.notna(row.get("Unit Price")) else 0,
                #"Производитель": str(row.get("Производитель", "")) if pd.notna(row.get("Производитель")) else "",
                #"Страна происхождения": str(row.get("Страна происхождения", "")) if pd.notna(row.get("Страна происхождения")) else "",
                #"Товарный знак": str(row.get("Товарный знак", "")) if pd.notna(row.get("Товарный знак")) else "",
                #"Order No": str(row.get("Order No", "")) if pd.notna(row.get("Order No")) else "",
                #"Case total N/W": round(float(row.get("Case total N/W", 0)), 2) if pd.notna(row.get("Case total N/W")) else 0,
            }
            
            # Проверяем, есть ли уже элемент с таким же Case No
            case_no = record_data["Case No"]
            case_already_exists = any(row.data.get("Case No") == case_no for row in storage.rows)
            
            # Если Case No уже встречался, устанавливаем количество грузовых мест в 0
            if case_already_exists:
                record_data["Количество грузовых мест"] = 0
                record_data["Количество упаковок"] = 0
            else:
                record_data["Количество грузовых мест"] = 1
                record_data["Количество упаковок"] = 1  
            # Количество мест
            calculated_total_quantity += record_data["Количество грузовых мест"]
            
            storage.rows.append(ExcelRow(data=record_data, sheet="PACKING LIST(Weight)"))
            processed_count += 1
        
        
        # ВЫВОД Количество записей
        storage.sender = f"Count:{processed_count}"
        # ВЫВОД Количество мест
        storage.calc.calc_quantity = calculated_total_quantity

        # Список контейнеров
        containers_list = {}


        # Группируем данные по номерам контейнеров
        containers_grouped = {}
        for row in storage.rows:
            container_no = row.data.get("Номер контейнера", "").strip()
            containers_list[container_no] = containers_list.get(container_no, 0) + 1
            if not container_no:
                container_no = "Без номера контейнера"
            
            if container_no not in containers_grouped:
                containers_grouped[container_no] = []
            
            containers_grouped[container_no].append(row.data)
        # Сохраняем сгруппированные данные
        storage.containers = containers_grouped

        # Количество контейнеров
        print(len(containers_list))
        storage.truck = f"Количество контейнеров: {len(containers_list)}"

    except Exception as e:
        return {"error": str(e)}

    # Возвращаем результат обработки
    return {"success": True, "storage": storage}
