"""
Модуль для работы с базой данных PostgreSQL
"""
import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import execute_values
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Глобальный пул соединений
connection_pool = None


def init_db_pool():
    """Инициализация пула соединений с БД"""
    global connection_pool
    if connection_pool is None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL не установлен в переменных окружения")
        
        try:
            connection_pool = psycopg2.pool.SimpleConnectionPool(
                1, 20, database_url
            )
            logger.info("Пул соединений с БД успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка при создании пула соединений: {e}")
            raise


def get_db_connection():
    """Получить соединение с БД из пула"""
    if connection_pool is None:
        init_db_pool()
    return connection_pool.getconn()


def return_db_connection(conn):
    """Вернуть соединение в пул"""
    if connection_pool:
        connection_pool.putconn(conn)


def save_data_to_db(data: Dict[str, Any], client_name: str, order_number: str) -> Dict[str, Any]:
    """
    Сохраняет данные в базу данных согласно схеме
    
    Args:
        data: Словарь с подготовленными данными (из DataHandler.prepared_data)
        client_name: Название клиента для сохранения
        order_number: Номер заказа для сохранения
        
    Returns:
        Dict с результатом операции
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            raise Exception("Не удалось получить соединение с БД")
        
        cursor = conn.cursor()
        
        # Начинаем транзакцию с оптимизацией для массовой вставки
        conn.autocommit = False
        
        # КРИТИЧНЫЕ ОПТИМИЗАЦИИ ДЛЯ МАКСИМАЛЬНОЙ СКОРОСТИ:
        # 1. Отключаем синхронизацию на диск (быстрее в 100 раз, но менее надежно при сбое)
        cursor.execute("SET LOCAL synchronous_commit = OFF")
        
        # 2. Увеличиваем work_mem для быстрой сортировки и соединений
        cursor.execute("SET LOCAL work_mem = '256MB'")
        
        # 3. Увеличиваем maintenance_work_mem для более быстрых операций
        cursor.execute("SET LOCAL maintenance_work_mem = '256MB'")
        
        # 1. Сохраняем или получаем клиента
        client_id = save_or_get_client(cursor, client_name)
        
        # 2. Создаем заказ (используем переданный номер заказа)
        order_id = save_or_get_order(cursor, client_id, order_number)
        
        # Собираем все инвойсы и товары для batch-вставки
        invoice_data_batch = []
        
        for container_data in data:
            container = container_data.get("container", "")
            consignor = container_data.get("consignor", "")
            consignee = container_data.get("consignee", "")
            sender_address = container_data.get("sender_address", "")
            recipient_address = container_data.get("recipient_address", "")
            invoice_number = container_data.get("invoice_number", "")
            invoice_date_str = container_data.get("invoice_date", "")
            items = container_data.get("items", [])
            
            # Подготавливаем данные инвойса
            invoice_data_batch.append({
                "order_id": order_id,
                "container": container[:20] if container else "",
                "consignor": consignor,
                "consignee": consignee,
                "sender_address": sender_address,
                "recipient_address": recipient_address,
                "invoice_number": invoice_number[:50] if invoice_number else "",
                "invoice_date_str": invoice_date_str,
                "items": items
            })
        
        # Batch-вставка инвойсов и товаров
        batch_insert_invoices_and_items(cursor, invoice_data_batch)
        
        # Коммитим транзакцию
        conn.commit()
        
        return {
            "success": True,
            "message": f"Данные успешно сохранены в БД. Обработано контейнеров: {len(data)}",
            "containers_saved": len(data)
        }
        
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception as rollback_error:
                logger.error(f"Ошибка при откате транзакции: {rollback_error}")
        
        error_msg = str(e)
        logger.error(f"Ошибка при сохранении данных в БД: {error_msg}")
        print(f"Ошибка при сохранении данных в БД: {error_msg}")
        
        return {
            "success": False,
            "error": f"Ошибка при сохранении в БД: {error_msg}"
        }
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            return_db_connection(conn)


def save_or_get_client(cursor, name: str) -> int:
    """
    Сохраняет клиента или возвращает существующего
    
    Returns:
        ID клиента
    """
    # Проверяем, существует ли клиент
    cursor.execute("SELECT id FROM clients WHERE name = %s", (name,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    
    # Создаем нового клиента
    cursor.execute("INSERT INTO clients (name) VALUES (%s) RETURNING id", (name,))
    return cursor.fetchone()[0]


def save_or_get_order(cursor, client_id: int, order_number: str) -> int:
    """
    Сохраняет заказ или возвращает существующий
    
    Returns:
        ID заказа
    """
    # Обрезаем order_number до 50 символов (лимит VARCHAR(50))
    order_number = (order_number[:50] if order_number else "")
    
    # Проверяем, существует ли заказ
    cursor.execute(
        "SELECT id FROM orders WHERE client_id = %s AND order_number = %s",
        (client_id, order_number)
    )
    result = cursor.fetchone()
    
    if result:
        return result[0]
    
    # Создаем новый заказ
    cursor.execute(
        "INSERT INTO orders (client_id, order_number) VALUES (%s, %s) RETURNING id",
        (client_id, order_number)
    )
    return cursor.fetchone()[0]


def save_invoice(
    cursor,
    order_id: int,
    container: str,
    consignor: str,
    consignee: str,
    sender_address: str,
    recipient_address: str,
    invoice_number: str,
    invoice_date_str: str
) -> int:
    """
    Сохраняет инвойс
    
    Returns:
        ID инвойса
    """
    # Обрезаем значения согласно лимитам БД
    container = (container[:20] if container else "")  # VARCHAR(20)
    invoice_number = (invoice_number[:50] if invoice_number else "")  # VARCHAR(50)
    
    # Парсим дату инвойса
    invoice_date = None
    if invoice_date_str:
        try:
            # Пробуем разные форматы даты
            for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y", "%d/%m/%Y"]:
                try:
                    invoice_date = datetime.strptime(invoice_date_str, fmt)
                    break
                except ValueError:
                    continue
        except Exception:
            pass
    
    cursor.execute(
        """INSERT INTO invoices 
           (order_id, container, consignor, consignee, sender_address, recipient_address, invoice_number, invoice_date)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
        (order_id, container, consignor, consignee, sender_address, recipient_address, invoice_number, invoice_date)
    )
    return cursor.fetchone()[0]


def batch_insert_invoices_and_items(cursor, invoice_data_batch: List[Dict[str, Any]]) -> None:
    """
    ULTRA-FAST Batch-вставка инвойсов и товаров с максимальной производительностью
    Использует execute_values для суперскорости и VALUES с RETURNING для получения ID
    
    Args:
        cursor: Курсор БД
        invoice_data_batch: Список данных инвойсов с товарами
    """
    if not invoice_data_batch:
        return
    
    # 1. Подготовка данных инвойсов
    invoice_records = []
    for inv_data in invoice_data_batch:
        # Парсим дату инвойса
        invoice_date = None
        if inv_data["invoice_date_str"]:
            try:
                for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y", "%d/%m/%Y"]:
                    try:
                        invoice_date = datetime.strptime(inv_data["invoice_date_str"], fmt)
                        break
                    except ValueError:
                        continue
            except Exception:
                pass
        
        invoice_records.append((
            inv_data["order_id"],
            inv_data["container"],
            inv_data["consignor"],
            inv_data["consignee"],
            inv_data["sender_address"],
            inv_data["recipient_address"],
            inv_data["invoice_number"],
            invoice_date
        ))
    
    # Суперскоростная вставка всех инвойсов с RETURNING для получения ID
    invoice_ids = execute_values(
        cursor,
        """INSERT INTO invoices 
           (order_id, container, consignor, consignee, sender_address, recipient_address, invoice_number, invoice_date)
           VALUES %s
           RETURNING id, container, invoice_number""",
        invoice_records,
        fetch=True
    )
    
    # Создаем карту ID инвойсов для быстрого доступа
    invoice_id_map = {}
    for inv_id, container, inv_num in invoice_ids:
        key = f"{container}_{inv_num}"
        invoice_id_map[key] = inv_id
    
    # 2. Подготовка всех товаров для массовой вставки
    items_records = []
    for inv_data in invoice_data_batch:
        key = f"{inv_data['container']}_{inv_data['invoice_number']}"
        invoice_id = invoice_id_map.get(key)
        
        if not invoice_id:
            continue
        
        for item in inv_data["items"]:
            # Обрезаем значения согласно лимитам БД
            code = (item.get("code", "")[:20] if item.get("code") else "")
            package_type = (item.get("package_type", "")[:10] if item.get("package_type") else "")
            currency = (item.get("currency", "")[:10] if item.get("currency") else "")
            
            # Преобразуем в boolean
            restriction_flag = bool(item.get("restriction_flag")) if item.get("restriction_flag") is not None else False
            package_info = bool(item.get("package_info")) if item.get("package_info") is not None else False
            
            items_records.append((
                invoice_id,
                code,
                item.get("goods_name", ""),
                restriction_flag,
                package_info,
                int(item.get("places", 0)),
                int(item.get("package_info_type", 0)),
                package_type,
                int(item.get("package_count", 0)),
                float(item.get("weight", 0.0)),
                currency,
                float(item.get("value_amount", 0.0))
            ))
    
    # Суперскоростная вставка всех товаров одним махом
    if items_records:
        execute_values(
            cursor,
            """INSERT INTO invoice_items 
               (invoice_id, code, goods_name, restriction_flag, package_info, places, 
                package_info_type, package_type, package_count, weight, currency, value_amount)
               VALUES %s""",
            items_records,
            page_size=1000  # Оптимальный размер пакета для PostgreSQL
        )


def save_invoice_item(
    cursor,
    invoice_id: int,
    code: str,
    goods_name: str,
    restriction_flag: Any,
    package_info: Any,
    places: int,
    package_info_type: int,
    package_type: str,
    package_count: int,
    weight: float,
    currency: str,
    value_amount: float
) -> int:
    """
    Сохраняет товар инвойса (использовать для одиночных вставок)
    
    Returns:
        ID товара
    """
    # Обрезаем значения согласно лимитам БД
    code = (code[:20] if code else "")  # VARCHAR(20)
    package_type = (package_type[:10] if package_type else "")  # VARCHAR(10)
    currency = (currency[:10] if currency else "")  # VARCHAR(10)
    
    # Преобразуем restriction_flag и package_info в boolean
    restriction_flag_bool = bool(restriction_flag) if restriction_flag is not None else False
    package_info_bool = bool(package_info) if package_info is not None else False
    
    cursor.execute(
        """INSERT INTO invoice_items 
           (invoice_id, code, goods_name, restriction_flag, package_info, places, 
            package_info_type, package_type, package_count, weight, currency, value_amount)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
        (invoice_id, code, goods_name, restriction_flag_bool, package_info_bool, places,
         package_info_type, package_type, package_count, weight, currency, value_amount)
    )
    return cursor.fetchone()[0]

