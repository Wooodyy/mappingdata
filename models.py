from pydantic import BaseModel
from typing import List

class ExcelRow(BaseModel):
    data: dict
    sheet: str

class Totals(BaseModel):
    total_quantity: float = 0
    total_weight: float = 0
    total_amount: float = 0

class ExcelData(BaseModel):
    rows: List[ExcelRow]
    totals: Totals
    sender: str = ""
    truck: str = ""
