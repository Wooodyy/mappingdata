from .unified_compare import unified_compare_handler

# Регистрируем доступные алгоритмы сравнения для отправителей
COMPARE_HANDLERS = {
    "единый шаблон": unified_compare_handler,
}

def get_compare_handler(sender: str):
    """
    Вернёт функцию сравнения для указанного отправителя,
    либо None если нет алгоритма.
    """
    key = sender.strip().lower()
    return COMPARE_HANDLERS.get(key)

