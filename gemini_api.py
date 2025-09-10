import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL = "gemini-2.0-flash-lite"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key=AIzaSyA-hM5QWer-jOGZP86l9e91PIBc1BTfpn4"

def chat_with_gemini(prompt: str):
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    resp = requests.post(URL, json=payload)
    resp.raise_for_status()
    data = resp.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return text
    except (KeyError, IndexError):
        return "Нет ответа от Gemini"

def detect_currency(file_content: str):
    prompt = f"""Проанализируй следующий документ и определи валюту товаров. 
Ответь только одним словом - код валюты (например: USD, CNY, EUR, RUB).
Если валюта не найдена, ответь USD.

Документ:
{file_content}"""
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    resp = requests.post(URL, json=payload)
    resp.raise_for_status()
    data = resp.json()
    try:
        currency = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        # Убираем лишние символы и возвращаем только код валюты
        currency = currency.replace('\n', '').replace('\r', '').upper()
        # Проверяем что это валидный код валюты (3 символа)
        if len(currency) == 3 and currency.isalpha():
            return currency
        else:
            return "USD"
    except (KeyError, IndexError):
        return "USD"

def detect_recipient(file_content: str):
    prompt = f"""Проанализируй следующий документ и определи For Account & Risk of Messrs в общем нужно определить получателя. 
    Подумай о том, чтобы определить только название компании.
    Ответь только Названием компании, адрес и номер телефона вообще не нужен (например: MTL TECHNOLOGY CO., LTD.).
    Если получатель не найден, ответь Не опознан.

Документ:
{file_content}"""
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    resp = requests.post(URL, json=payload)
    resp.raise_for_status()
    data = resp.json()
    try:
        recipient = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        # Убираем лишние символы и возвращаем только получателя
        recipient = recipient.replace('\n', '').replace('\r', '').upper()
        # Проверяем что это валидный получатель

        if len(recipient) > 0:
            return recipient
        else:
            return "Не опознан"
    except (KeyError, IndexError):
        return "Не опознан"

def detect_sender(file_content: str):
    prompt = f"""Проанализируй следующий документ и определи Shipper и Exporter, нужно определить отправителя. 
    Подумай о том, чтобы определить только название компании.
    Ответь только Названием компании, адрес и номер телефона вообще не нужен (например: MTL TECHNOLOGY CO., LTD.).
    Если отправителя не найден, ответь Не опознан.

Документ:
{file_content}"""
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    resp = requests.post(URL, json=payload)
    resp.raise_for_status()
    data = resp.json()
    try:
        sender = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        # Убираем лишние символы и возвращаем только отправителя
        sender = sender.replace('\n', '').replace('\r', '').upper()
        # Проверяем что это валидный отправителя
        
        if len(sender) > 0:
            return sender
        else:
            return "Не опознан"
    except (KeyError, IndexError):
        return "Не опознан"
