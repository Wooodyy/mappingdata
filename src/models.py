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
    totals: Totals
    calc: Calc
    sender: str = ""
    truck: str = ""
    seller: str = ""
    recipient: str = ""
    buyer: str = ""
    invoice: str = ""
    date_invoice: str = ""
    sender_name: str = ""  # Название отправителя из XML
    sender_address: str = ""  # Адрес отправителя из XML
    recipient_name: str = ""  # Название получателя из XML
    recipient_address: str = ""  # Адрес получателя из XML

class RawDataRequest(BaseModel):
    """Модель для принятия сырых данных из localStorage"""
    containers: Dict[str, List[Dict[str, Any]]]
    sender: str
    recipient: str
    seller: str = None
    buyer: str = None
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


class CompareData(BaseModel):
    """Данные ответа для страницы сравнения."""
    xml_data: Optional[ExcelData] = None  # XML данные в формате ExcelData
    xml_documents: List[DocumentInfo] = []  # Документы из XML
    invoice_data: Optional[ExcelData] = None
