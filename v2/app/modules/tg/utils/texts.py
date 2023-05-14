import logging


logger = logging.getLogger(__name__)


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
    text: dict | str = __texts__ or {}
    for key in id.split("."):
        try:
            text = text[key]
        except:
            logger.info(f"Tg text not found for id: {id}")
            return id
    try:
        formatted = text.format(**kwargs)
    except:
        logger.error(f"Not all arguments provided for text with id: {id}", exc_info=True)
        return text
    return formatted


def __load_texts__(filepath: str) -> dict:
    import json
    with open(filepath, "r", encoding='utf-8') as file:
        return json.load(file)