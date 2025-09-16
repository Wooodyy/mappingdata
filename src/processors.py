from .processors.xinjiang import process_xinjiang
from .processors.mtl import process_mtl
from .processors.changan import process_changan

# Регистрируем доступные алгоритмы отправителей
PROCESSORS = {
    "xinjiang xindudu import and export trading co.,ltd": process_xinjiang,
    "mtl шаблон": process_mtl,
    "changan international corporation": process_changan,
}

def get_processor(sender: str):
    """
    Вернёт функцию-обработчик для указанного отправителя,
    либо None если нет алгоритма.
    """
    key = sender.strip().lower()
    return PROCESSORS.get(key)
