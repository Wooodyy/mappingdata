import pandas as pd
import io
from models import ExcelRow, ExcelData, Totals

def process_xinjiang(file_content: bytes) -> dict:
    storage = ExcelData(rows=[], totals=Totals())

    column_mapping = {
        "Xinjiang Xindudu \nImport and Export Trading Co.,Ltd": "Наименование/модель",
        "Unnamed: 1": "Код ТН ВЭД",
        "Unnamed: 2": "Кол-во мест",
        "Unnamed: 5": "Общий вес брутто",
        "Unnamed: 6": "Общая сумма"
    }

    try:
        sheets = pd.read_excel(io.BytesIO(file_content), sheet_name=None)

        # Определяем валюту
        currency = "USD"
        for _, df in sheets.items():
            df_str = df.to_string().lower()
            if 'cny' in df_str or any('cny' in str(col).lower() for col in df.columns):
                currency = "CNY"
                break

        for sheet_name, df in sheets.items():
            start_idx = df[df.iloc[:, 0] == "Наименование/модель"].index

            if len(start_idx) > 0:
                df = df.iloc[start_idx[0]:]
                df = df.reset_index(drop=True)
                df.rename(columns=column_mapping, inplace=True)

                # Последняя строка = итоги
                last_row = df.iloc[-1]
                storage.totals = Totals(
                    total_quantity=float(last_row["Кол-во мест"]),
                    total_weight=float(last_row["Общий вес брутто"]),
                    total_amount=float(last_row["Общая сумма"])
                )

                # Остальные строки
                records = df.iloc[1:-1].to_dict(orient="records")
                for record in records:
                    ordered_record = {
                        "Код ТН ВЭД": record.get("Код ТН ВЭД", ""),
                        "Наименование/модель": record.get("Наименование/модель", ""),
                        "Кол-во мест": record.get("Кол-во мест", 0),
                        "Общий вес брутто": record.get("Общий вес брутто", 0),
                        "Общая сумма": record.get("Общая сумма", 0),
                        "Тип валюты": currency
                    }
                    storage.rows.append(ExcelRow(data=ordered_record, sheet=sheet_name))

    except Exception as e:
        return {"error": str(e)}

    return {"success": True, "storage": storage}
