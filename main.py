"""
Точка входа в приложение
"""
import uvicorn
import logging
from src.api import app

# Настраиваем фильтр для uvicorn.access логгера, чтобы не показывать 404
class No404Filter(logging.Filter):
    def filter(self, record):
        # Фильтруем записи с 404 статусом (проверяем и атрибут, и сообщение)
        if hasattr(record, 'status_code') and record.status_code == 404:
            return False
        if hasattr(record, 'getMessage'):
            message = record.getMessage()
            if '404' in message and 'Not Found' in message:
                return False
        return True

# Применяем фильтр к access логгеру
logging.getLogger("uvicorn.access").addFilter(No404Filter())

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )