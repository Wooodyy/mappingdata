from .xinjiang import process_xinjiang

# Регистрируем доступные алгоритмы отправителей
PROCESSORS = {
    "xinjiang": process_xinjiang,
    "15": process_xinjiang,
    "18": process_xinjiang,
}

def get_processor(sender: str):
    """
    Вернёт функцию-обработчик для указанного отправителя,
    либо None если нет алгоритма.
    """
    key = sender.strip().lower()
    return PROCESSORS.get(key)
