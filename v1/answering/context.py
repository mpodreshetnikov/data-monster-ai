from my_types import Interaction

__context__: dict[str, list[Interaction]] = {}


def add_interaction(user_id: int, interaction: Interaction) -> None:
    global __context__

    if __context__.get(user_id) == None:
        __context__[user_id] = []
    __context__[user_id].append(interaction)


def get_context(user_id: int, deep: int = None) -> list[Interaction]:
    global __context__

    context = __context__.get(user_id)
    if context and deep:
        context = context[-deep:]
    return context