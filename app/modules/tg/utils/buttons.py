from enum import Enum


class ButtonId(Enum):
    ID_SQL_BUTTON = "SQL"
    ID_CHART_BUTTON = "CHART"


def build_keybord(reply_markup_cls, buttons: list, columns: int = 1):
    keyboard = []

    buttons = list(filter(None, buttons))
    rows = [buttons[i:i + columns] for i in range(0, len(buttons), columns)] 
    keyboard = rows

    return reply_markup_cls(keyboard)