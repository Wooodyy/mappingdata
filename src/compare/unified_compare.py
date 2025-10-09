from typing import Dict, List
import xml.etree.ElementTree as ET
from src.models import ExcelData, Totals, Calc, DocumentInfo
from src.processors.unified import process_unified


def sort_records_by_criteria(records: List[dict]) -> List[dict]:
    """
    Сортирует записи по четырём критериям:
    1. Количество грузовых мест (по убыванию)
    2. Сумма (по убыванию)
    3. Вес брутто (по убыванию)
    4. Коммерческое описание товара (по алфавиту, без учёта регистра)
    """
    def sort_key(record):
        cargo_quantity = float(record.get("Количество грузовых мест") or 0)
        sum_value = float(record.get("Сумма") or 0)
        gross_weight = float(record.get("Вес брутто") or 0)
        description = str(record.get("Коммерческое описание товара") or "").strip().lower()
        return (-cargo_quantity, -sum_value, -gross_weight, description)

    return sorted(records, key=sort_key)


def extract_xml_data_and_documents(xml_bytes: bytes, invoice_data=None) -> tuple[ExcelData, List[DocumentInfo]]:
    """Извлекает данные из XML в формате ExcelData и отдельно документы."""
    try:
        root = ET.fromstring(xml_bytes)

        # Находим все блоки с деталями товарных позиций
        goods_items = []
        for elem in root.iter():
            if elem.tag.endswith("TransitGoodsItemDetails") or elem.tag.endswith("GoodsItemDetails"):
                goods_items.append(elem)

        if not goods_items:
            return ExcelData(containers={}, totals=Totals(), calc=Calc(), sender_name="", sender_address="", recipient_name="", recipient_address=""), []

        # Извлекаем данные отправителя из XML
        sender_name = ""
        sender_address_parts = []
        
        # Ищем данные отправителя в XML - ищем блок ns3:ConsignorDetails
        for elem in root.iter():
            if elem.tag.endswith("ConsignorDetails"):
                # Находим название отправителя внутри ConsignorDetails
                for child in elem:
                    if child.tag.endswith("SubjectName") and (child.text or "").strip():
                        sender_name = (child.text or "").strip()
                    
                    # Находим блок адреса внутри ConsignorDetails
                    if child.tag.endswith("SubjectAddressDetails"):
                        # Проходим по всем дочерним элементам адреса
                        for address_child in child:
                            # Пропускаем AddressKindCode
                            if not address_child.tag.endswith("AddressKindCode") and (address_child.text or "").strip():
                                sender_address_parts.append((address_child.text or "").strip())
        
        # Объединяем компоненты адреса в одну строку
        sender_address = ", ".join(sender_address_parts) if sender_address_parts else ""
        
        # Извлекаем данные получателя из XML
        recipient_name = ""
        recipient_address_parts = []
        
        # Ищем данные получателя в XML - ищем блок ns3:ConsigneeDetails
        for elem in root.iter():
            if elem.tag.endswith("ConsigneeDetails"):
                # Находим название получателя внутри ConsigneeDetails
                for child in elem:
                    if child.tag.endswith("SubjectName") and (child.text or "").strip():
                        recipient_name = (child.text or "").strip()
                    
                    # Находим блок адреса внутри ConsigneeDetails
                    if child.tag.endswith("SubjectAddressDetails"):
                        # Проходим по всем дочерним элементам адреса
                        for address_child in child:
                            # Пропускаем AddressKindCode
                            if not address_child.tag.endswith("AddressKindCode") and (address_child.text or "").strip():
                                recipient_address_parts.append((address_child.text or "").strip())
        
        # Объединяем компоненты адреса получателя в одну строку
        recipient_address = ", ".join(recipient_address_parts) if recipient_address_parts else ""
        
        # Определяем коды стран отправления и назначения
        departure_country_code = ""
        destination_country_code = ""
        for elem in root.iter():
            if elem.tag.endswith("DepartureCountryCode") and (elem.text or "").strip():
                departure_country_code = (elem.text or "").strip()
            if elem.tag.endswith("DestinationCountryCode") and (elem.text or "").strip():
                destination_country_code = (elem.text or "").strip()

        # Пломбы (количество и номера)
        seal_quantity = 0
        seal_ids: List[str] = []
        for elem in root.iter():
            if elem.tag.endswith("SealQuantity") and (elem.text or "").strip():
                try:
                    seal_quantity = int((elem.text or "").strip())
                except Exception:
                    pass
            if elem.tag.endswith("CustomsIdentificationMeansId") and (elem.text or "").strip():
                seal_ids.append((elem.text or "").strip())

        # Создаем ExcelData
        excel_data = ExcelData(
            containers={},
            totals=Totals(),
            calc=Calc(),
            sender_name=sender_name,
            sender_address=sender_address,
            recipient_name=recipient_name,
            recipient_address=recipient_address,
            departure_country_code=departure_country_code,
            destination_country_code=destination_country_code,
            seal_quantity=seal_quantity,
            seal_ids=seal_ids,
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
                                "31.05.2011",
                                "2011-05-31",
                                "2011/05/31",
                                "31/05/2011",
                                "2011-05-31T00:00:00",
                                "2011-05-31T00:00:00Z"
                            ]
                            
                            # Нормализуем дату для сравнения
                            normalized_date = doc_date.strip() if doc_date else ""
                            
                            # Проверяем соответствие ожидаемой дате
                            if normalized_date not in expected_date_formats:
                                has_error = True
                                error_message = f"Ошибка: Документ с кодом 09034 должен иметь дату 31.05.2011, но получена дата: {normalized_date}"
                        
                        # Проверяем документы с кодами 04021 и 04131 на соответствие данным инвойса
                        elif doc_kind in ["04021", "04131"] and invoice_data:
                            # Нормализуем номера инвойсов для сравнения (убираем ведущие нули)
                            def normalize_invoice_number(invoice_num):
                                """Нормализует номер инвойса, убирая ведущие нули"""
                                if not invoice_num:
                                    return ""
                                
                                # Преобразуем в строку, если это не строка
                                invoice_str = str(invoice_num).strip()
                                
                                # Если это число, убираем ведущие нули
                                if invoice_str.isdigit():
                                    return str(int(invoice_str))
                                
                                return invoice_str
                            
                            normalized_doc_id = normalize_invoice_number(doc_id)
                            normalized_invoice_id = normalize_invoice_number(invoice_data.invoice)
                            
                            # Проверяем соответствие DocId с invoice_data.invoice
                            if normalized_doc_id != normalized_invoice_id:
                                has_error = True
                                error_message = f"Ошибка: Документ с кодом {doc_kind} должен иметь DocId равный номеру инвойса ({invoice_data.invoice}), но получен: {doc_id}. Типы: DocId={type(doc_id)}, Invoice={type(invoice_data.invoice)}"
                            # Проверяем соответствие DocCreationDate с invoice_data.date_invoice
                            else:
                                # Преобразуем даты в формат YYYY-MM-DD для сравнения
                                def convert_to_yyyy_mm_dd(date_str):
                                    """Преобразует дату в формат YYYY-MM-DD"""
                                    if not date_str or date_str.strip() == "":
                                        return ""
                                    
                                    date_str = date_str.strip()
                                    
                                    # Если дата уже в формате YYYY-MM-DD, возвращаем как есть
                                    if len(date_str) == 10 and date_str.count('-') == 2:
                                        return date_str
                                    
                                    # Если дата в формате DD.MM.YYYY, конвертируем в YYYY-MM-DD
                                    if len(date_str) == 10 and date_str.count('.') == 2:
                                        try:
                                            parts = date_str.split('.')
                                            if len(parts) == 3:
                                                return f"{parts[2]}-{parts[1]}-{parts[0]}"
                                        except:
                                            pass
                                    
                                    # Если дата в формате YYYY/MM/DD, конвертируем в YYYY-MM-DD
                                    if len(date_str) == 10 and date_str.count('/') == 2:
                                        try:
                                            parts = date_str.split('/')
                                            if len(parts) == 3:
                                                return f"{parts[0]}-{parts[1]}-{parts[2]}"
                                        except:
                                            pass
                                    
                                    # Если дата содержит время (ISO формат), извлекаем только дату
                                    if 'T' in date_str:
                                        date_part = date_str.split('T')[0]
                                        return convert_to_yyyy_mm_dd(date_part)
                                    
                                    # Если дата содержит пробел и время (формат YYYY-MM-DD HH:MM:SS), извлекаем только дату
                                    if ' ' in date_str:
                                        date_part = date_str.split(' ')[0]
                                        return convert_to_yyyy_mm_dd(date_part)
                                    
                                    # Если ничего не подошло, возвращаем исходную строку
                                    return date_str
                                
                                doc_date_formatted = convert_to_yyyy_mm_dd(doc_date)
                                invoice_date_formatted = convert_to_yyyy_mm_dd(invoice_data.date_invoice)
                                
                                if doc_date_formatted != invoice_date_formatted:
                                    has_error = True
                                    error_message = f"Ошибка: Документ с кодом {doc_kind} должен иметь дату равную дате инвойса ({invoice_date_formatted}), но получена дата: {doc_date_formatted}"
                        
                        # Устанавливаем специальное название для документов с кодом 02013
                        final_doc_name = doc_name
                        if doc_kind == "02013" and doc_name == "":
                            final_doc_name = "ЖД НАКЛАДНАЯ"
                        
                        doc = DocumentInfo(
                            DocKindCode=doc_kind,
                            DocName=final_doc_name,
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
            package_availability_code = find_first_text(item, "PackageAvailabilityCode")
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
                "Информация об упаковке (0-БЕЗ, 1 С)": package_availability_code,
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
        return ExcelData(containers={}, totals=Totals(), calc=Calc(), sender_name="", sender_address="", recipient_name="", recipient_address=""), []


def unified_compare_handler(invoice_bytes: bytes, decl_bytes: bytes, invoice_name: str, decl_name: str) -> Dict:
    """Обработчик сравнения для Testoviy: извлекает данные из XML и обрабатывает инвойс через testoviy алгоритм."""
    # Получаем номер первого контейнера из XML данных (предварительно)
    temp_xml_data, _ = extract_xml_data_and_documents(decl_bytes)
    first_container_number = None
    if temp_xml_data.containers:
        first_container_number = next(iter(temp_xml_data.containers.keys()))
    
    # Обрабатываем инвойс через алгоритм testoviy
    try:
        invoice_result = process_unified(invoice_bytes, first_container_number)
        invoice_data = None
        if invoice_result.get("success") and "storage" in invoice_result:
            invoice_data = invoice_result["storage"]
    except Exception as e:
        invoice_result = {"error": str(e)}
        invoice_data = None
    
    # Обрабатываем XML декларацию с данными инвойса для валидации документов
    xml_data, xml_documents = extract_xml_data_and_documents(decl_bytes, invoice_data)
    
    # Сортируем записи в каждом контейнере по трем критериям
    for container_id, records in xml_data.containers.items():
        xml_data.containers[container_id] = sort_records_by_criteria(records)
    
    # Создаем результат согласно требуемой структуре
        result_data = {
        "success": True,
        "data": {
            "xml_data": {
                "containers": xml_data.containers,
                "calc": xml_data.calc.dict(),
                "sender_name": xml_data.sender_name,
                "sender_address": xml_data.sender_address,
                "recipient_name": xml_data.recipient_name,
                    "recipient_address": xml_data.recipient_address,
                    "departure_country_code": xml_data.departure_country_code,
                    "destination_country_code": xml_data.destination_country_code,
                    "seal_quantity": xml_data.seal_quantity,
                    "seal_ids": xml_data.seal_ids,
            },
            "xml_documents": [doc.dict() for doc in xml_documents],
            "invoice_data": None
        }
    }
    # Сортируем записи в каждом контейнере по трем критериям
    if invoice_data:
        for container_id, records in invoice_data.containers.items():
            invoice_data.containers[container_id] = sort_records_by_criteria(records)
    
    # Добавляем данные инвойса, если они есть
    if invoice_data:
        result_data["data"]["invoice_data"] = {
            "containers": invoice_data.containers,
            "calc": invoice_data.calc.dict(),
            "invoice": invoice_data.invoice,
            "date_invoice": invoice_data.date_invoice,
            "sender_name": invoice_data.sender_name,
            "sender_address": invoice_data.sender_address,
            "recipient_name": invoice_data.recipient_name,
            "recipient_address": invoice_data.recipient_address,
        }
       
    
    return result_data
