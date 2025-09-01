import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL = "gemini-2.5-flash"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"

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
