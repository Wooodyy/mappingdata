from .xinjiang import process_xinjiang
from .mtl import process_mtl
from .mtl2 import process_mtl2
from .changan import process_changan
from .testoviy import process_testoviy

# Регистрируем доступные алгоритмы отправителей
PROCESSORS = {
    "xinjiang xindudu import and export trading co.,ltd": process_xinjiang,
    "mtl шаблон": process_mtl,
    "changan international corporation": process_changan,
    "mtl 2 - не готов": process_mtl2,
    "универсальный шаблон": process_testoviy,
}

def get_processor(sender: str):
    """
    Вернёт функцию-обработчик для указанного отправителя,
    либо None если нет алгоритма.
    """
    key = sender.strip().lower()
    return PROCESSORS.get(key)
