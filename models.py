from pydantic import BaseModel
from typing import List

class ExcelRow(BaseModel):
    data: dict
    sheet: str

class Totals(BaseModel):
    total_quantity: float = 0
    total_weight: float = 0
    total_amount: float = 0

class Calc(BaseModel):
    calc_quantity: float = 0
    calc_weight: float = 0
    calc_amount: float = 0

class ExcelData(BaseModel):
    rows: List[ExcelRow]
    totals: Totals
    calc: Calc
    sender: str = ""
    truck: str = ""
    sender: str = ""
