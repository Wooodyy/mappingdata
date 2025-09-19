from typing import Dict, List
import xml.etree.ElementTree as ET
from src.models import ExcelData, Totals, Calc, DocumentInfo
from src.processors.changan import process_changan
from src.gemini_api import sort_containers_data


def extract_xml_data_and_documents(xml_bytes: bytes) -> tuple[ExcelData, List[DocumentInfo]]:
    """Извлекает данные из XML в формате ExcelData и отдельно документы."""
    try:
        root = ET.fromstring(xml_bytes)

        # Находим все блоки с деталями товарных позиций
        goods_items = []
        for elem in root.iter():
            if elem.tag.endswith("TransitGoodsItemDetails") or elem.tag.endswith("GoodsItemDetails"):
                goods_items.append(elem)

        if not goods_items:
            return ExcelData(containers={}, totals=Totals(), calc=Calc(), sender="", truck="", recipient="", buyer=""), []

        # Создаем ExcelData
        excel_data = ExcelData(
            containers={},
            totals=Totals(),
            calc=Calc(),
        )
        
        documents = []
        total_quantity = 0
        total_weight = 0
        total_amount = 0

        def find_first_text(parent: ET.Element, local_name: str) -> str:
            for ch in parent.iter():
                if ch.tag.endswith(local_name) and (ch.text or "").strip():
                    return (ch.text or "").strip()
            return ""
        
        def find_first_attribute(parent: ET.Element, local_name: str, attr_name: str) -> str:
            for ch in parent.iter():
                if ch.tag.endswith(local_name) and attr_name in ch.attrib:
                    return ch.attrib[attr_name]
            return ""

        # Извлекаем все документы из всего XML (один раз, без дубликатов)
        for elem in root.iter():
            if elem.tag.endswith("TDPresentedDocDetails"):
                doc_kind = find_first_text(elem, "DocKindCode")
                doc_name = find_first_text(elem, "DocName")
                doc_id = find_first_text(elem, "DocId")
                doc_date = find_first_text(elem, "DocCreationDate")
                
                # Добавляем документ если есть данные и код не в списке исключений
                if doc_kind or doc_name or doc_id or doc_date:
                    # Исключаем документы с кодами 02013, 11002, 09021
                    if doc_kind not in [""]:
                        # Проверяем документы с кодом 09034 на соответствие дате 31.05.2011
                        has_error = False
                        error_message = ""
                        
                        if doc_kind == "09034":
                            # Проверяем различные форматы даты
                            expected_date_formats = [
                                "30.05.2011",
                                "2011-05-30",
                                "2011/05/30",
                                "30/05/2011",
                                "2011-05-30T00:00:00",
                                "2011-05-30T00:00:00Z"
                            ]
                            
                            # Нормализуем дату для сравнения
                            normalized_date = doc_date.strip() if doc_date else ""
                            
                            # Проверяем соответствие ожидаемой дате
                            if normalized_date not in expected_date_formats:
                                has_error = True
                                error_message = f"Ошибка: Документ с кодом 09034 должен иметь дату 31.05.2011, но получена дата: {normalized_date}"
                        
                        doc = DocumentInfo(
                            DocKindCode=doc_kind,
                            DocName=doc_name,
                            DocId=doc_id,
                            DocCreationDate=doc_date,
                            has_error=has_error,
                            error_message=error_message
                        )
                        # Проверяем на дубликаты перед добавлением
                        doc_exists = False
                        for existing_doc in documents:
                            if (existing_doc.DocKindCode == doc.DocKindCode and
                                existing_doc.DocName == doc.DocName and
                                existing_doc.DocId == doc.DocId and
                                existing_doc.DocCreationDate == doc.DocCreationDate):
                                doc_exists = True
                                break
                        
                        if not doc_exists:
                            documents.append(doc)

        # Извлекаем данные из каждого товарного блока
        for item in goods_items:
            # Извлекаем основные данные
            commodity_code = find_first_text(item, "CommodityCode")
            goods_description = find_first_text(item, "GoodsDescriptionText")
            gross_mass = find_first_text(item, "UnifiedGrossMassMeasure")
            goods_prohibition_free_code = find_first_text(item, "GoodsProhibitionFreeCode")
            cargo_quantity = find_first_text(item, "CargoQuantity")
            package_quantity = find_first_text(item, "PackageQuantity")
            container_id = find_first_text(item, "ContainerId")
            value_amount = find_first_text(item, "CAValueAmount")
            currency = find_first_attribute(item, "CAValueAmount", "currencyCode")
            package_kind = find_first_text(item, "PackageKindCode")
            
            # Создаем запись товара
            if not container_id:
                container_id = "Без номера контейнера"
            
            record = {
                "Код ТН ВЭД": int(commodity_code) if commodity_code and commodity_code.isdigit() else 0,
                "Коммерческое описание товара": goods_description,
                "Признак товара, свободного от применения запретов и ограничений (всегда 1)": 1 if goods_prohibition_free_code == "C" else 0,
                "Информация об упаковке (0-БЕЗ, 1 С)": 1,
                "Количество грузовых мест": float(cargo_quantity) if cargo_quantity else 0,
                "Вид информации об упаковке (всегда 0)": 0,
                "Вид упаковки ": package_kind if package_kind else "PK",
                "Количество упаковок": float(package_quantity) if package_quantity else 0,
                "Номер контейнера": container_id,
                "Вес брутто": float(gross_mass) if gross_mass else 0,
                "Валюта": currency if currency else "USD",
                "Сумма": float(value_amount) if value_amount else 0
            }
            
            # Добавляем в контейнер
            if container_id not in excel_data.containers:
                excel_data.containers[container_id] = []
            excel_data.containers[container_id].append(record)
            
            # Считаем итоги
            total_quantity += record["Количество грузовых мест"]
            total_weight += record["Вес брутто"]
            total_amount += record["Сумма"]
        
        # Устанавливаем итоги
        excel_data.totals = Totals(
            total_quantity=total_quantity,
            total_weight=total_weight,
            total_amount=total_amount
        )
        excel_data.calc = Calc(
            calc_quantity=total_quantity,
            calc_weight=total_weight,
            calc_amount=total_amount
        )
        
        return excel_data, documents

    except Exception as e:
        return ExcelData(containers={}, totals=Totals(), calc=Calc(), sender="", truck="", recipient="", buyer=""), []


def changan_compare_handler(invoice_bytes: bytes, decl_bytes: bytes, invoice_name: str, decl_name: str) -> Dict:
    """Обработчик сравнения: извлекает данные из XML и обрабатывает инвойс через changan алгоритм."""
    # Обрабатываем XML декларацию
    xml_data, xml_documents = extract_xml_data_and_documents(decl_bytes)
    
    # Обрабатываем инвойс через алгоритм changan
    try:
        invoice_result = process_changan(invoice_bytes)
        invoice_data = None
        if invoice_result.get("success") and "storage" in invoice_result:
            invoice_data = invoice_result["storage"]
    except Exception as e:
        invoice_result = {"error": str(e)}
        invoice_data = None
    # Создаем результат согласно требуемой структуре
    result_data = {
        "success": True,
        "data": {
            "xml_data": {
                "containers": xml_data.containers,
                "calc": xml_data.calc.dict()
            },
            "xml_documents": [doc.dict() for doc in xml_documents],
            "invoice_data": None
        }
    }
    
    # Добавляем данные инвойса, если они есть
    if invoice_data:
        result_data["data"]["invoice_data"] = {
            "containers": invoice_data.containers,
            "calc": invoice_data.calc.dict()
        }
        print(result_data)
        # Отправляем данные контейнеров в Gemini API для сортировки
        try:
            sorted_data = sort_containers_data(
                invoice_containers=invoice_data.containers,
                xml_containers=xml_data.containers
            )
            
            if sorted_data:
                # Заменяем данные на отсортированные
                result_data["data"]["invoice_data"]["containers"] = sorted_data["sorted_invoice_containers"]
                result_data["data"]["xml_data"]["containers"] = sorted_data["sorted_xml_containers"]
                result_data["data"]["gemini_analysis"] = "Данные успешно отсортированы"
            else:
                result_data["data"]["gemini_analysis"] = "Ошибка: Не удалось отсортировать данные"
        except Exception as e:
            result_data["data"]["gemini_analysis"] = f"Ошибка при сортировке через Gemini: {str(e)}"
    
    return result_data