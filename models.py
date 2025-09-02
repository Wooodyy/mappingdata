from pydantic import BaseModel
from typing import List, Dict

class ExcelRow(BaseModel):
    data: dict
    sheet: str

class ContainerGroup(BaseModel):
    container_no: str
    rows: List[ExcelRow]

class Totals(BaseModel):
    total_quantity: float = 0
    total_weight: float = 0
    total_amount: float = 0

class Calc(BaseModel):
    calc_quantity: float = 0
    calc_weight: float = 0
    calc_amount: float = 0

class ExcelData(BaseModel):
    rows: List[ExcelRow]  # Сохраняем для обратной совместимости
    containers: Dict[str, List[dict]] = {}  # Новое поле для группированных данных
    totals: Totals
    calc: Calc
    sender: str = ""
    truck: str = ""
    recipient: str = ""
