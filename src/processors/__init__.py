from .unified import process_unified

# Регистрируем доступные алгоритмы отправителей
PROCESSORS = {
    "единый шаблон": process_unified,
}

def get_processor(sender: str):
    """
    Вернёт функцию-обработчик для указанного отправителя,
    либо None если нет алгоритма.
    """
    key = sender.strip().lower()
    return PROCESSORS.get(key)
