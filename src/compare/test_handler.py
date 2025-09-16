from typing import Callable, Dict
import xml.etree.ElementTree as ET


def extract_xml_table_data(xml_bytes: bytes):
    """Извлекает товары из транзитной декларации XML."""
    try:
        root = ET.fromstring(xml_bytes)
        
        # Ищем все элементы TransitGoodsItemDetails
        goods_items = []
        for elem in root.iter():
            if elem.tag.endswith('TransitGoodsItemDetails'):
                goods_items.append(elem)
        
        if not goods_items:
            return {"headers": [], "rows": [], "total_rows": 0, "error": "Товары не найдены"}
        
        # Ключевые поля для отображения
        key_fields = [
            'ConsignmentItemOrdinal', 'CommodityCode', 'GoodsDescriptionText',
            'UnifiedGrossMassMeasure', 'CargoQuantity', 'CAValueAmount'
        ]
        
        rows = []
        for item in goods_items:
            row = {}
            for field in key_fields:
                # Ищем поле в дочерних элементах
                for child in item.iter():
                    if child.tag.endswith(field) and child.text:
                        row[field] = child.text.strip()
                        break
                if field not in row:
                    row[field] = ''
            rows.append(row)
        
        return {
            "headers": key_fields,
            "rows": rows,
            "total_rows": len(rows)
        }
        
    except Exception as e:
        return {"headers": [], "rows": [], "total_rows": 0, "error": f"Ошибка: {str(e)}"}


def test_compare_handler(invoice_bytes: bytes, decl_bytes: bytes, invoice_name: str, decl_name: str):
    """
    Обработчик сравнения: извлекает табличные данные из XML и возвращает имена файлов.
    """
    # Извлекаем данные из XML
    xml_data = extract_xml_table_data(decl_bytes)
    
    return {
        "success": True,
        "data": {
            "invoice_file": invoice_name,
            "declaration_file": decl_name,
            "xml_table": xml_data
        }
    }


COMPARE_HANDLERS: Dict[str, Callable] = {
    "тестовый": test_compare_handler,
}


