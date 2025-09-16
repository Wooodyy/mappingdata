from pydantic import BaseModel
from typing import Dict, List, Any
from datetime import date

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
    recipient: str = ""
    buyer: str = ""

class RawDataRequest(BaseModel):
    """Модель для принятия сырых данных из localStorage"""
    containers: Dict[str, List[Dict[str, Any]]]
    sender: str
    recipient: str
    invoice: str
    date_invoice: date  # формат: "25.02.2025"
    seller: str = None
    buyer: str = None
    truck: str = ""
    calc: Dict[str, Any] = {}
    totals: Dict[str, Any] = {}
