def set_config_file_path(path: str):
    global __texts__
    __texts__ = __load_texts__(path)


def message_text_for(id: str, **kwargs) -> str:
    """Return text by its id from config file

    Args:
        id (str): string in format 'hello.firstly'
        *kwargs: arguments for string formatting

    Returns:
        str: text by id
    """
    text: dict | str = __texts__
    for key in id.split("."):
        text = text[key]
    formatted = text.format(**kwargs)
    return formatted


def __load_texts__(filepath: str) -> dict:
    import json
    with open(filepath, "r") as file:
        return json.load(file)