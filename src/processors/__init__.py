from .xinjiang import process_xinjiang
from .mtl import process_mtl
from .astana import process_astana
from .changan import process_changan
from .testoviy import process_testoviy

# Регистрируем доступные алгоритмы отправителей
PROCESSORS = {
    "xinjiang xindudu import and export trading co.,ltd": process_xinjiang,
    "mtl шаблон": process_mtl,
    "changan international corporation": process_changan,
    "astana motors company": process_astana,
    "универсальный шаблон - не готов": process_testoviy,
}

def get_processor(sender: str):
    """
    Вернёт функцию-обработчик для указанного отправителя,
    либо None если нет алгоритма.
    """
    key = sender.strip().lower()
    return PROCESSORS.get(key)
