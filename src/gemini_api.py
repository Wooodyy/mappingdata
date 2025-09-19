import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = "AIzaSyA-hM5QWer-jOGZP86l9e91PIBc1BTfpn4"
MODEL = "gemini-2.0-flash-lite"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"

def _send_to_gemini(prompt: str) -> str:
    """Универсальная функция для отправки запросов к Gemini API."""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        resp = requests.post(URL, json=payload)
        resp.raise_for_status()
        data = resp.json()
        
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            return "Нет ответа от Gemini"
    except requests.exceptions.RequestException as e:
        return f"Ошибка при отправке запроса к Gemini API: {str(e)}"

def chat_with_gemini(prompt: str):
    """Общая функция для общения с Gemini."""
    return _send_to_gemini(prompt)

def detect_currency(file_content: str):
    """Определяет валюту из документа."""
    prompt = f"""Проанализируй следующий документ и определи валюту товаров. 
Ответь только одним словом - код валюты (например: USD, CNY, EUR, RUB).
Если валюта не найдена, ответь USD.

Документ:
{file_content}"""
    
    result = _send_to_gemini(prompt)
    if result.startswith("Ошибка"):
        return "USD"
    
    currency = result.strip().replace('\n', '').replace('\r', '').upper()
    return currency if len(currency) == 3 and currency.isalpha() else "USD"

def detect_recipient(file_content: str):
    """Определяет получателя из документа."""
    prompt = f"""Проанализируй следующий документ и определи For Account & Risk of Messrs в общем нужно определить получателя. 
Подумай о том, чтобы определить только название компании.
Ответь только Названием компании, адрес и номер телефона вообще не нужен (например: MTL TECHNOLOGY CO., LTD.).
Если получатель не найден, ответь Не опознан.

Документ:
{file_content}"""
    
    result = _send_to_gemini(prompt)
    if result.startswith("Ошибка"):
        return "Не опознан"
    
    recipient = result.strip().replace('\n', '').replace('\r', '').upper()
    return recipient if len(recipient) > 0 else "Не опознан"

def detect_sender(file_content: str):
    """Определяет отправителя из документа."""
    prompt = f"""Проанализируй следующий документ и определи Shipper и Exporter, нужно определить отправителя. 
Подумай о том, чтобы определить только название компании.
Ответь только Названием компании, адрес и номер телефона вообще не нужен (например: MTL TECHNOLOGY CO., LTD.).
Если отправителя не найден, ответь Не опознан.

Документ:
{file_content}"""
    
    result = _send_to_gemini(prompt)
    if result.startswith("Ошибка"):
        return "Не опознан"
    
    sender = result.strip().replace('\n', '').replace('\r', '').upper()
    return sender if len(sender) > 0 else "Не опознан"


def sort_containers_data(invoice_containers: dict, xml_containers: dict):
    """
    Сортирует массивы контейнеров так, чтобы соответствующие записи были на одинаковых позициях.
    
    Args:
        invoice_containers: Словарь с данными контейнеров из инвойса
        xml_containers: Словарь с данными контейнеров из XML
    
    Returns:
        dict: Словарь с отсортированными массивами или None в случае ошибки
    """
    import json
    
    # Проверяем структуру исходных данных
    if not _validate_containers_structure(invoice_containers) or not _validate_containers_structure(xml_containers):
        return None
    
    # Подготавливаем данные для отправки
    data_to_send = {
        "invoice_containers": invoice_containers,
        "xml_containers": xml_containers
    }
    
    # Конвертируем в JSON строку для отправки
    json_data = json.dumps(data_to_send, ensure_ascii=False, indent=2)
    
    sorting_prompt = f"""Ты должен отсортировать два массива данных так, чтобы соответствующие записи из invoice_containers и xml_containers были на одинаковых позициях.

КРИТИЧЕСКИ ВАЖНО: 
- НЕ МЕНЯЙ содержимое записей - все данные должны остаться точно такими же
- НЕ МЕНЯЙ структуру данных - все ключи и типы данных должны остаться идентичными
- ТОЛЬКО меняй порядок элементов внутри массивов записей для каждого контейнера
- Сопоставляй записи по схожести данных (номера контейнеров, описания товаров, коды ТН ВЭД, веса, суммы)
- Результат должен быть в формате JSON с двумя массивами: "sorted_invoice_containers" и "sorted_xml_containers"
- Структура должна быть точно такой же: словарь где ключи - номера контейнеров, значения - массивы записей
- Каждая запись должна сохранить все свои поля и типы данных

Пример результата (структура должна быть идентичной исходной):
{{
  "sorted_invoice_containers": {{ 
    "RBGU4046656": [
      {{"Код ТН ВЭД": 123, "Коммерческое описание товара": "описание", "Вес брутто": 100.0, ...}},
      {{"Код ТН ВЭД": 456, "Коммерческое описание товара": "описание2", "Вес брутто": 200.0, ...}}
    ],
    "RBGU4046657": [...]
  }},
  "sorted_xml_containers": {{ 
    "RBGU4046656": [
      {{"Код ТН ВЭД": 123, "Коммерческое описание товара": "описание", "Вес брутто": 100.0, ...}},
      {{"Код ТН ВЭД": 456, "Коммерческое описание товара": "описание2", "Вес брутто": 200.0, ...}}
    ],
    "RBGU4046657": [...]
  }}
}}

Данные для анализа:
{json_data}

ВАЖНО: Ответь ТОЛЬКО в формате JSON без дополнительных комментариев или объяснений. Сохрани точную структуру исходных данных."""
    
    response = _send_to_gemini(sorting_prompt)
    sorted_data = _parse_gemini_json_response(response)
    
    # Проверяем что структура сохранилась после сортировки
    if sorted_data and _validate_sorted_data_structure(sorted_data, invoice_containers, xml_containers):
        return sorted_data
    else:
        return None

def _parse_gemini_json_response(response_text: str):
    """
    Парсит JSON ответ от Gemini API и извлекает отсортированные массивы.
    
    Args:
        response_text: Текстовый ответ от Gemini API
    
    Returns:
        dict: Словарь с отсортированными массивами или None в случае ошибки
    """
    import json
    import re
    
    try:
        # Пытаемся найти JSON в ответе (на случай если есть дополнительные комментарии)
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            parsed_data = json.loads(json_str)
            
            # Проверяем наличие нужных ключей и структуру
            if ("sorted_invoice_containers" in parsed_data and 
                "sorted_xml_containers" in parsed_data and
                isinstance(parsed_data["sorted_invoice_containers"], dict) and
                isinstance(parsed_data["sorted_xml_containers"], dict)):
                
                # Дополнительная проверка структуры - убеждаемся что это словари с массивами
                invoice_containers = parsed_data["sorted_invoice_containers"]
                xml_containers = parsed_data["sorted_xml_containers"]
                
                # Проверяем что все значения в словарях являются списками
                for container_id, records in invoice_containers.items():
                    if not isinstance(records, list):
                        return None
                
                for container_id, records in xml_containers.items():
                    if not isinstance(records, list):
                        return None
                
                return parsed_data
            else:
                return None
        else:
            # Если не нашли JSON, пытаемся парсить весь ответ
            parsed_data = json.loads(response_text)
            if ("sorted_invoice_containers" in parsed_data and 
                "sorted_xml_containers" in parsed_data and
                isinstance(parsed_data["sorted_invoice_containers"], dict) and
                isinstance(parsed_data["sorted_xml_containers"], dict)):
                return parsed_data
            else:
                return None
                
    except json.JSONDecodeError:
        return None

def _validate_containers_structure(containers: dict) -> bool:
    """
    Проверяет что структура контейнеров корректна.
    
    Args:
        containers: Словарь с данными контейнеров
    
    Returns:
        bool: True если структура корректна, False иначе
    """
    if not isinstance(containers, dict):
        return False
    
    for container_id, records in containers.items():
        if not isinstance(container_id, str):
            return False
        if not isinstance(records, list):
            return False
        for record in records:
            if not isinstance(record, dict):
                return False
    
    return True

def _validate_sorted_data_structure(sorted_data: dict, original_invoice: dict, original_xml: dict) -> bool:
    """
    Проверяет что структура отсортированных данных соответствует исходной.
    
    Args:
        sorted_data: Отсортированные данные от Gemini
        original_invoice: Исходные данные инвойса
        original_xml: Исходные данные XML
    
    Returns:
        bool: True если структура сохранена, False иначе
    """
    try:
        # Проверяем наличие нужных ключей
        if ("sorted_invoice_containers" not in sorted_data or 
            "sorted_xml_containers" not in sorted_data):
            return False
        
        sorted_invoice = sorted_data["sorted_invoice_containers"]
        sorted_xml = sorted_data["sorted_xml_containers"]
        
        # Проверяем что это словари
        if not isinstance(sorted_invoice, dict) or not isinstance(sorted_xml, dict):
            return False
        
        # Проверяем что количество контейнеров совпадает
        if (len(sorted_invoice) != len(original_invoice) or 
            len(sorted_xml) != len(original_xml)):
            return False
        
        # Проверяем что все контейнеры присутствуют
        for container_id in original_invoice.keys():
            if container_id not in sorted_invoice:
                return False
            if not isinstance(sorted_invoice[container_id], list):
                return False
        
        for container_id in original_xml.keys():
            if container_id not in sorted_xml:
                return False
            if not isinstance(sorted_xml[container_id], list):
                return False
        
        return True
        
    except Exception:
        return False


def check_spelling_errors(invoice_sender: str, invoice_recipient: str, 
                         xml_sender_name: str, xml_sender_address: str,
                         xml_recipient_name: str, xml_recipient_address: str):
    """
    Проверяет орфографические ошибки в данных отправителя и получателя из XML,
    сравнивая их с эталонными данными из инвойса.
    
    Args:
        invoice_sender: Название и адресотправителя из инвойса (эталон)
        invoice_recipient: Название и адрес получателя из инвойса (эталон)
        xml_sender_name: Название отправителя из XML
        xml_sender_address: Адрес отправителя из XML
        xml_recipient_name: Название получателя из XML
        xml_recipient_address: Адрес получателя из XML
    
    Returns:
        dict: Словарь с булевыми значениями для каждого поля
    """
    prompt = f"""Ты эксперт по проверке орфографических ошибок в международных торговых документах.

ЗАДАЧА: Проверь данные из XML на орфографические ошибки, сравнивая их с эталонными данными из инвойса.

ЭТАЛОННЫЕ ДАННЫЕ (из инвойса):
- Отправитель: "{invoice_sender}"
- Получатель: "{invoice_recipient}"

ДАННЫЕ ДЛЯ ПРОВЕРКИ (из XML):
- Название отправителя: "{xml_sender_name}"
- Адрес отправителя: "{xml_sender_address}"
- Название получателя: "{xml_recipient_name}"
- Адрес получателя: "{xml_recipient_address}"

КРИТЕРИИ ПРОВЕРКИ:
1. Орфографические ошибки в названиях компаний
2. Неправильное написание адресов
3. Опечатки в географических названиях
4. Неправильное написание улиц, городов, стран
5. Ошибки в сокращениях (LTD, CO., INC и т.д.)

ВАЖНО:
- Учитывай что названия могут быть на разных языках (английский, русский, китайский)
- Сравнивай с эталонными данными, но не требуй точного совпадения
- Фокусируйся именно на орфографических ошибках, а не на различиях в формате

ОТВЕТ: Ответь ТОЛЬКО в формате JSON без дополнительных комментариев:
{{
  "sender_name_correct": true/false,
  "sender_address_correct": true/false,
  "recipient_name_correct": true/false,
  "recipient_address_correct": true/false
}}

где true = нет орфографических ошибок, false = есть орфографические ошибки."""

    response = _send_to_gemini(prompt)
    return _parse_spelling_check_response(response)


def _parse_spelling_check_response(response_text: str) -> dict:
    """
    Парсит ответ от Gemini API для проверки орфографических ошибок.
    
    Args:
        response_text: Текстовый ответ от Gemini API
    
    Returns:
        dict: Словарь с булевыми значениями или значения по умолчанию при ошибке
    """
    import json
    import re
    
    try:
        # Пытаемся найти JSON в ответе
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            parsed_data = json.loads(json_str)
            
            # Проверяем наличие нужных ключей и возвращаем результат
            result = {
                "sender_name_correct": parsed_data.get("sender_name_correct", True),
                "sender_address_correct": parsed_data.get("sender_address_correct", True),
                "recipient_name_correct": parsed_data.get("recipient_name_correct", True),
                "recipient_address_correct": parsed_data.get("recipient_address_correct", True)
            }
            
            # Убеждаемся что все значения булевые
            for key in result:
                if not isinstance(result[key], bool):
                    result[key] = True  # По умолчанию считаем корректным
            
            return result
        else:
            # Если не нашли JSON, пытаемся парсить весь ответ
            parsed_data = json.loads(response_text)
            return {
                "sender_name_correct": parsed_data.get("sender_name_correct", True),
                "sender_address_correct": parsed_data.get("sender_address_correct", True),
                "recipient_name_correct": parsed_data.get("recipient_name_correct", True),
                "recipient_address_correct": parsed_data.get("recipient_address_correct", True)
            }
                
    except json.JSONDecodeError:
        # В случае ошибки парсинга возвращаем значения по умолчанию (все корректно)
        return {
            "sender_name_correct": True,
            "sender_address_correct": True,
            "recipient_name_correct": True,
            "recipient_address_correct": True
        }