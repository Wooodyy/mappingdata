from typing import Callable, Optional
from .test_handler import COMPARE_HANDLERS  # existing handlers registry


def get_compare_handler(sender: str) -> Optional[Callable]:
    """
    Вернёт функцию сравнения для указанного отправителя,
    либо None если нет алгоритма.
    """
    if not sender:
        return None
    key = sender.strip().lower()
    return COMPARE_HANDLERS.get(key)

