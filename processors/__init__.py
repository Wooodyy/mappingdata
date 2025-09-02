from .xinjiang import process_xinjiang
from .mtl import process_mtl

# Регистрируем доступные алгоритмы отправителей
PROCESSORS = {
    "xinjiang xindudu import and export trading co.,ltd": process_xinjiang,
    "mtl шаблон": process_mtl,
}

def get_processor(sender: str):
    """
    Вернёт функцию-обработчик для указанного отправителя,
    либо None если нет алгоритма.
    """
    key = sender.strip().lower()
    return PROCESSORS.get(key)
