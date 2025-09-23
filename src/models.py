from pydantic import BaseModel
from typing import Dict, List, Any, Optional

class Totals(BaseModel):
    total_quantity: float = 0
    total_weight: float = 0
    total_amount: float = 0

class Calc(BaseModel):
    calc_quantity: float = 0
    calc_weight: float = 0
    calc_amount: float = 0

class ExcelData(BaseModel):
    containers: Dict[str, List[dict]] = {}
    container_info: Dict[str, dict] = {}  # Информация об отправителе и получателе для каждого контейнера
    totals: Totals
    calc: Calc
    invoice: str = ""
    date_invoice: str = ""
    sender_name: str = ""  # Название отправителя из XML
    sender_address: str = ""  # Адрес отправителя из XML
    recipient_name: str = ""  # Название получателя из XML
    recipient_address: str = ""  # Адрес получателя из XML

class RawDataRequest(BaseModel):
    """Модель для принятия сырых данных из localStorage"""
    containers: Dict[str, List[Dict[str, Any]]]
    container_info: Dict[str, dict] = {}  # Информация об отправителе и получателе для каждого контейнера
    totals: Dict[str, Any] = {}  # Итоговые значения
    calc: Dict[str, Any] = {}  # Расчетные значения
    sender_name: str = ""  # Название отправителя из XML
    sender_address: str = ""  # Адрес отправителя из XML
    recipient_name: str = ""  # Название получателя из XML
    recipient_address: str = ""  # Адрес получателя из XML
    invoice: str = ""  # Номер инвойса
    date_invoice: str = ""  # Дата инвойса
    sender: str = ""  # Для обратной совместимости
    recipient: str = ""  # Для обратной совместимости
    truck: str = ""


# ===== Модели для сравнения =====
class DocumentInfo(BaseModel):
    """Информация о документе."""
    DocKindCode: str = ""
    DocName: str = ""
    DocId: str = ""
    DocCreationDate: str = ""
    has_error: bool = False
    error_message: str = ""
