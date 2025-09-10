from pydantic import BaseModel
from typing import Dict, List

class Totals(BaseModel):
    total_quantity: float = 0
    total_weight: float = 0
    total_amount: float = 0

class Calc(BaseModel):
    calc_quantity: float = 0
    calc_weight: float = 0
    calc_amount: float = 0

class ExcelData(BaseModel):
    containers: Dict[str, List[dict]] = {}  # Основное поле для группированных данных
    totals: Totals
    calc: Calc
    sender: str = ""
    truck: str = ""
    recipient: str = ""
    buyer: str = ""
