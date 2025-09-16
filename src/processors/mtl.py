import pandas as pd
import io
from src.models import ExcelData, Totals, Calc
from src.gemini_api import detect_currency, detect_recipient, detect_sender

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

        # Ищем лист CONTAINER LIST
        if "CONTAINER LIST" not in sheets:
            return {"error": "Лист 'CONTAINER LIST' не найден"}
        else:
            # Получаем данные из нужного листа
            df_container_list = sheets["CONTAINER LIST"].copy()
            # Проверяем минимальное количество строк
            if len(df_container_list) < 4:
                return {"error": "Недостаточно строк в данных (требуется минимум 4 строки)"}
            else:
                # Найти строку с итогами (Total Case)
                total_row_index = df_container_list[df_container_list.iloc[:, 0] == 'Total Case'].index
                if len(total_row_index) > 0:
                    total_row = df_container_list.loc[total_row_index[0]]
                    
                    # Извлекаем нужные значения из соответствующих колонок
                    # Основываясь на структуре данных:
                    # Колонка 3 (Unnamed: 3) - Case Qty
                    # Колонка 6 (Unnamed: 6) - G/W(kg) 
                    # Колонка 8 (Unnamed: 8) - Amount
                    
                    storage.totals = Totals(
                        total_quantity=round(float(total_row.iloc[3]), 2),  # Case Qty
                        total_weight=round(float(total_row.iloc[6]), 2),    # G/W(kg)
                        total_amount=round(float(total_row.iloc[8]), 2)     # Amount
                    )
                else:
                    print("Строка с итогами 'Total Case' не найдена")
                    storage.totals = Totals(
                        total_quantity=0,
                        total_weight=0,
                        total_amount=0
                    )
        # Ищем лист "PACKING LIST(Weight)"
        if "PACKING LIST(Weight)" not in sheets:
            return {"error": "Лист 'PACKING LIST(Weight)' не найден"}
        else:
            # Получаем данные из нужного листа
            df = sheets["PACKING LIST(Weight)"].copy()
            # Проверяем минимальное количество строк
            if len(df) < 4:
                return {"error": "Недостаточно строк в данных (требуется минимум 4 строки)"}

        # Определяем валюту, получателя и отправителя из листа INVOICE если он существует
        currency = "USD"  # значение по умолчанию
        recipient = "Не опознан"  # значение по умолчанию
        sender = "Не опознан"  # значение по умолчанию
        if "INVOICE" in sheets:
            df_invoice = sheets["INVOICE"].copy()
            # Проверяем минимальное количество строк
            if len(df_invoice) >= 4:
                # Преобразуем DataFrame в строку для анализа
                invoice_content = df_invoice.to_string()
                currency = detect_currency(invoice_content)
                recipient = detect_recipient(invoice_content)
                sender = detect_sender(invoice_content)
        storage.recipient = recipient
        storage.sender = sender

        # Извлекаем данные начиная с 3-й строки (заголовки)
        df = df.iloc[2:].reset_index(drop=True)
        
        # Переименовываем колонки согласно mapping
        df.rename(columns=column_mapping, inplace=True)
        # Обрабатываем строки данных (пропускаем заголовки)
        data_rows = df.iloc[1:]
        calculated_total_quantity = 0
        calculated_total_weight = 0
        calculated_total_amount = 0
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
            
            # Проверяем, есть ли уже элемент с таким же Case No в контейнерах
            case_no = record_data["Case No"]
            case_already_exists = False
            
            # Проверяем во всех контейнерах
            for container_rows in storage.containers.values():
                if any(row.get("Case No") == case_no for row in container_rows):
                    case_already_exists = True
                    break
            
            # Если Case No уже встречался, устанавливаем количество грузовых мест в 0
            if case_already_exists:
                record_data["Количество грузовых мест"] = 0
                record_data["Количество упаковок"] = 0
            else:
                record_data["Количество грузовых мест"] = 1
                record_data["Количество упаковок"] = 1  
            
            # Количество мест
            calculated_total_quantity += record_data["Количество грузовых мест"]
            calculated_total_weight += record_data["Вес брутто"]
            calculated_total_amount += record_data["Сумма"]
            
            # Определяем номер контейнера для группировки из данных строки
            container_no = record_data["Номер контейнера"].strip()
            if not container_no:
                container_no = "Без номера контейнера"
            
            
            # Инициализируем контейнер если его еще нет
            if container_no not in storage.containers:
                storage.containers[container_no] = []
            
            # Добавляем данные напрямую в контейнер
            storage.containers[container_no].append(record_data)
            processed_count += 1
        
        # ВЫВОД Количество мест
        storage.calc.calc_quantity = round(calculated_total_quantity, 2)
        storage.calc.calc_weight = round(calculated_total_weight, 2)
        storage.calc.calc_amount = round(calculated_total_amount, 2)

        # Список контейнеров для статистики
        containers_list = {}
        for container_no, rows in storage.containers.items():
            containers_list[container_no] = len(rows)
        

        # Количество контейнеров
        print(len(containers_list))
        storage.truck = f"Количество контейнеров: {len(containers_list)}"

    except Exception as e:
        return {"error": str(e)}

    # Возвращаем результат обработки
    return {"success": True, "storage": storage}

