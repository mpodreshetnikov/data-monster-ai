def set_config_file_path(path: str):
    global __texts__
    __texts__ = __load_texts__(path)


def get_message_text(id: str) -> str:
    """Return text by its id from config file

    Args:
        id (str): string in format 'hello.firstly'

    Returns:
        str: text by id
    """
    text = __texts__
    for key in id.split("."):
        text = text[key]
    return text


def __load_texts__(filepath: str) -> dict:
    import json
    with open(filepath, "r") as file:
        return json.load(file)