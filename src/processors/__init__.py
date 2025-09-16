from .xinjiang import process_xinjiang
from .mtl import process_mtl
from .mtl2 import process_mtl2
from .changan import process_changan

# Регистрируем доступные алгоритмы отправителей
PROCESSORS = {
    "xinjiang xindudu import and export trading co.,ltd": process_xinjiang,
    "hyundai motor company - 1": process_mtl,
    "hyundai motor company - 2": process_mtl2,
    "changan international corporation": process_changan,
}

def get_processor(sender: str):
    """
    Вернёт функцию-обработчик для указанного отправителя,
    либо None если нет алгоритма.
    """
    key = sender.strip().lower()
    return PROCESSORS.get(key)
