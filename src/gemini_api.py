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
    
    # Подготавливаем данные для отправки
    data_to_send = {
        "invoice_containers": invoice_containers,
        "xml_containers": xml_containers
    }
    
    # Конвертируем в JSON строку для отправки
    json_data = json.dumps(data_to_send, ensure_ascii=False, indent=2)
    
    sorting_prompt = f"""Ты должен отсортировать два массива данных так, чтобы соответствующие записи из invoice_containers и xml_containers были на одинаковых позициях.

ВАЖНО: 
- НЕ МЕНЯЙ содержимое записей - все данные должны остаться точно такими же
- ТОЛЬКО меняй порядок строк в массивах
- Сопоставляй записи по схожести данных (номера контейнеров, описания товаров, коды ТН ВЭД, веса, суммы)
- Результат должен быть в формате JSON с двумя массивами: "sorted_invoice_containers" и "sorted_xml_containers" в виде словаря с ключами - номерами контейнеров и значениями - массивами записей

Пример результата:
{{
  "sorted_invoice_containers":{ "RBGU4046656":[...], "RBGU4046657":[...], "RBGU4046658":[...] },
  "sorted_xml_containers":{ "RBGU4046656":[...], "RBGU4046657":[...], "RBGU4046658":[...] }
}}

Данные для анализа:
{json_data}

ВАЖНО: Ответь ТОЛЬКО в формате JSON без дополнительных комментариев или объяснений."""
    
    response = _send_to_gemini(sorting_prompt)
    return _parse_gemini_json_response(response)

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
            
            # Проверяем наличие нужных ключей
            if "sorted_invoice_containers" in parsed_data and "sorted_xml_containers" in parsed_data:
                return parsed_data
            else:
                return None
        else:
            # Если не нашли JSON, пытаемся парсить весь ответ
            parsed_data = json.loads(response_text)
            if "sorted_invoice_containers" in parsed_data and "sorted_xml_containers" in parsed_data:
                return parsed_data
            else:
                return None
                
    except json.JSONDecodeError:
        return None