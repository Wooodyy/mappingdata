"""
Модуль для обработки и сохранения данных в формате 1.json
"""
import json
from typing import Dict, Any, List
from pydantic import BaseModel


class RawDataRequest(BaseModel):
    """Модель для принятия сырых данных из localStorage"""
    containers: Dict[str, List[Dict[str, Any]]]
    sender: str
    recipient: str
    seller: str = None
    buyer: str = None
    truck: str = ""
    calc: Dict[str, Any] = {}
    totals: Dict[str, Any] = {}


class DataHandler:
    """Класс для обработки и сохранения данных"""
    
    def __init__(self):
        self.prepared_data = []
    
    def prepare_data(self, raw_data: RawDataRequest) -> Dict[str, Any]:
        """
        Подготавливает сырые данные из localStorage и преобразует их в формат 1.json
        
        Args:
            raw_data: Сырые данные из localStorage
            
        Returns:
            Dict с результатом обработки
        """
        try:
            self.prepared_data = []
            containers_processed = 0
            
            # Обрабатываем каждый контейнер отдельно
            for container_no, container_rows in raw_data.containers.items():
                if not container_rows:
                    continue
                    
                # Создаем данные в формате 1.json для этого контейнера
                json_data = {
                    "container": container_no,
                    "consignor": raw_data.sender or "отправитель",
                    "consignee": raw_data.recipient or "получатель", 
                    "seller": raw_data.seller,
                    "buyer": raw_data.buyer,
                    "items": []
                }
                
                # Обрабатываем товары в контейнере
                for row in container_rows:
                    # Безопасное преобразование в числа с обработкой ошибок
                    def safe_float(value, default=0.0):
                        try:
                            if value is None or value == "":
                                return default
                            return float(value)
                        except (ValueError, TypeError):
                            return default
                    
                    def safe_int(value, default=0):
                        try:
                            if value is None or value == "":
                                return default
                            return int(float(value))  # Сначала float, потом int для корректного преобразования
                        except (ValueError, TypeError):
                            return default
                    
                    item = {
                        "code": row.get("Код ТН ВЭД", ""),
                        "goods_name": row.get("Коммерческое описание товара", ""),
                        "restriction_flag": 1,
                        "package_info": 0,  # Согласно шаблону: 0 - без упаковки
                        "places": safe_int(row.get("Количество грузовых мест", 0)),  # Целое число
                        "package_info_type": 0,
                        "package_type": row.get("Вид упаковки ", "PP"),
                        "package_count": safe_int(row.get("Количество упаковок", 0)),  # Целое число
                        "weight": safe_float(row.get("Вес брутто", 0.0)),  # Вещественное число
                        "currency": row.get("Валюта", ""),
                        "value_amount": safe_float(row.get("Сумма", 0.0))  # Вещественное число
                    }
                    json_data["items"].append(item)
                
                # Сохраняем подготовленные данные
                self.prepared_data.append(json_data)
                containers_processed += 1
            
            return {
                "success": True,
                "message": f"Данные успешно подготовлены! Обработано контейнеров: {containers_processed}",
                "containers_processed": containers_processed
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def post_data(self) -> Dict[str, Any]:
        """
        Выводит подготовленные данные в консоль (функция POST)
        
        Returns:
            Dict с результатом операции
        """
        try:
            if not self.prepared_data:
                return {
                    "success": False,
                    "error": "Нет подготовленных данных для отправки"
                }
            
            # Выводим каждый контейнер в консоль
            for json_data in self.prepared_data:
                print(json.dumps(json_data, ensure_ascii=False, indent=4))
            
            return {
                "success": True,
                "message": f"Данные успешно отправлены! Отправлено контейнеров: {len(self.prepared_data)}",
                "containers_sent": len(self.prepared_data)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


def handle_raw_data(raw_data: RawDataRequest) -> Dict[str, Any]:
    """
    Фасадная функция для обработки сырых данных из localStorage
    
    Args:
        raw_data: Сырые данные из localStorage
        
    Returns:
        Результат обработки
    """
    handler = DataHandler()
    
    # Подготавливаем данные
    prepare_result = handler.prepare_data(raw_data)
    if not prepare_result["success"]:
        return prepare_result
    
    # Отправляем данные (выводим в консоль)
    post_result = handler.post_data()
    if not post_result["success"]:
        return post_result
    
    return {
        "success": True,
        "message": f"Данные успешно обработаны и отправлены! Подготовлено: {prepare_result['containers_processed']}, отправлено: {post_result['containers_sent']}",
        "containers_processed": prepare_result["containers_processed"],
        "containers_sent": post_result["containers_sent"]
    }