import pandas as pd
import io
from src.models import ExcelData, Totals, Calc

def process_unified(file_content: bytes, CON_NUMBER: str = None) -> dict:
    
    storage = ExcelData(
        containers={},
        container_info={},
        totals=Totals(),
        calc=Calc(),
        invoice="-",
        date_invoice="-",
        sender_name="-",
        sender_address="-",
        recipient_name="-",
        recipient_address="-"
    )

    column_mapping = {
        "Unnamed: 0": "Номер",
        "Unnamed: 1": "Код ТН ВЭД",
        "Unnamed: 2": "Коммерческое описание товара",
        "Unnamed: 3": "Кол-во штук",
        "Unnamed: 4": "Кол-во мест",
        "Unnamed: 5": "Упаковка",
        "Unnamed: 6": "Нетто",
        "Unnamed: 7": "Брутто",
        "Unnamed: 8": "Валюта",
        "Unnamed: 9": "Сумма",
        "Unnamed: 10": "Номер контейнера",
        "Unnamed: 11": "Номер инвойса",
        "Unnamed: 12": "Дата инвойса",
        "Unnamed: 13": "Отправитель:",
        "Unnamed: 14": "Адрес отправителя:",
        "Unnamed: 15": "Продавец:",
        "Unnamed: 16": "Получатель:",
        "Unnamed: 17": "Адрес получателя:",
        "Unnamed: 18": "Покупатель:",
    }

    try:
        # Читаем Excel файл
        df = pd.read_excel(io.BytesIO(file_content), sheet_name="PL")
        
        # Начинаем сканирование с 9 строки (индекс 8, так как индексация с 0)
        start_row = 1
        data_df = df.iloc[start_row:].copy()
        # Переменные для подсчета общих значений
        calculated_total_quantity = 0
        calculated_total_weight = 0
        calculated_total_amount = 0
        
        # Сначала собираем все данные для анализа инвойсов по контейнерам
        container_invoices = {}  # {container_number: set(invoice_numbers)}
        all_items = []  # Список всех товаров для последующей обработки
        
        # Первый проход - собираем информацию о контейнерах и инвойсах
        for idx, row in data_df.iterrows():
            container_number = row.get('Unnamed: 10')
            if pd.isna(container_number) or str(container_number).strip() == '':
                continue
            
            container_number = str(container_number).strip()
            if CON_NUMBER == container_number or CON_NUMBER is None:
                invoice_number = str(row.get('Unnamed: 11', '')).strip() if pd.notna(row.get('Unnamed: 11')) else ''
                
                if container_number not in container_invoices:
                    container_invoices[container_number] = set()
                if invoice_number:
                    container_invoices[container_number].add(invoice_number)
                
                all_items.append((idx, row))
        
        # Второй проход - обрабатываем товары с правильными ключами
        for idx, row in all_items:
            container_number = str(row.get('Unnamed: 10')).strip()
            invoice_number = str(row.get('Unnamed: 11', '')).strip() if pd.notna(row.get('Unnamed: 11')) else ''
            
            # Определяем ключ контейнера
            # Если в контейнере несколько разных инвойсов, добавляем номер инвойса к ключу
            if len(container_invoices[container_number]) > 1 and invoice_number:
                container_key = f"{container_number}_{invoice_number}"
            else:
                container_key = container_number
            
            # Создаем запись товара
            item = {
                "Код ТН ВЭД": str(row.get('Unnamed: 1', '')).strip()[:6] if pd.notna(row.get('Unnamed: 1')) else '',
                "Коммерческое описание товара": str(row.get('Unnamed: 2', '')).strip() if pd.notna(row.get('Unnamed: 2')) else '',
                "Признак товара, свободного от применения запретов и ограничений (всегда 1)": 1,
                "Информация об упаковке (0-БЕЗ, 1 С)": 1 if (pd.notna(row.get("Unnamed: 7")) and pd.notna(row.get("Unnamed: 6")) and float(row.get("Unnamed: 7", 0)) > float(row.get("Unnamed: 6", 0))) else 0,
                #"Кол-во штук": float(row.get('Unnamed: 3', 0)) if pd.notna(row.get('Unnamed: 3')) else 0,
                "Количество грузовых мест": float(row.get('Unnamed: 4', 0)) if pd.notna(row.get('Unnamed: 4')) else 0,
                "Вид информации об упаковке (всегда 0)": 0,
                "Вид упаковки ": str(row.get('Unnamed: 5', '')).strip() if pd.notna(row.get('Unnamed: 5')) else '',
                "Количество упаковок": float(row.get('Unnamed: 4', 0)) if pd.notna(row.get('Unnamed: 4')) else 0,
                #"Нетто": float(row.get('Unnamed: 6', 0)) if pd.notna(row.get('Unnamed: 6')) else 0,
                "Номер контейнера": container_number, 
                "Вес брутто": float(row.get('Unnamed: 7', 0)) if pd.notna(row.get('Unnamed: 7')) else 0,
                "Валюта": str(row.get('Unnamed: 8', '')).strip() if pd.notna(row.get('Unnamed: 8')) else '',
                "Сумма": float(row.get('Unnamed: 9', 0)) if pd.notna(row.get('Unnamed: 9')) else 0,
                #"Номер инвойса": str(row.get('Unnamed: 11', '')).strip() if pd.notna(row.get('Unnamed: 11')) else '',
                #"Case No": str(row.get('Unnamed: 10', '')).strip() if pd.notna(row.get('Unnamed: 10')) else '',
            }
            
            # Добавляем товар в контейнер (используем уникальный ключ)
            if container_key not in storage.containers:
                storage.containers[container_key] = []
            
            storage.containers[container_key].append(item)
            
            sender_name = str(row.get('Unnamed: 13', '')).strip() + (f" П/П {str(row.get('Unnamed: 15', '')).strip()}" if pd.notna(row.get('Unnamed: 15')) and str(row.get('Unnamed: 15')).strip() else "")
            sender_address = str(row.get('Unnamed: 14', '')).strip()
            recipient_name = str(row.get('Unnamed: 16', '')).strip() + (f" ДЛЯ {str(row.get('Unnamed: 18', '')).strip()}" if pd.notna(row.get('Unnamed: 18')) and str(row.get('Unnamed: 18')).strip() else "")
            recipient_address = str(row.get('Unnamed: 17', '')).strip()
           
            # Сохраняем информацию об отправителе и получателе для каждого контейнера
            if container_key not in storage.container_info:
                storage.container_info[container_key] = {
                    'sender_name': sender_name,
                    'sender_address': sender_address,
                    'recipient_name': recipient_name,
                    'recipient_address': recipient_address,
                    'invoice': str(row.get('Unnamed: 11', '')).strip() if pd.notna(row.get('Unnamed: 11')) else '',
                    'date_invoice': str(row.get('Unnamed: 12', '')).strip() if pd.notna(row.get('Unnamed: 12')) else ''
                }
            
            # Также сохраняем общую информацию для совместимости
            storage.sender_name = sender_name
            storage.sender_address = sender_address
            storage.recipient_name = recipient_name
            storage.recipient_address = recipient_address

            storage.invoice = str(row.get('Unnamed: 11', '')).strip() if pd.notna(row.get('Unnamed: 11')) else ''
            storage.date_invoice = str(row.get('Unnamed: 12', '')).strip() if pd.notna(row.get('Unnamed: 12')) else ''

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
    # Устанавливаем значения по умолчанию для totals (можно будет обновить при необходимости)
    storage.totals.total_quantity = round(calculated_total_quantity, 2)
    storage.totals.total_weight = round(calculated_total_weight, 2)
    storage.totals.total_amount = round(calculated_total_amount, 2)

    # Возвращаем результат обработки
    return {"success": True, "storage": storage}

