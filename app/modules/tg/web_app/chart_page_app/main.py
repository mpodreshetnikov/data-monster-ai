import os

DIR_DIR = os.path.realpath(os.path.dirname(__file__))

def build_chart_page(data: list[dict], labels_column: str, chart_type: str, chart_title: str) -> str:
    if not data or len(data) == 0:
        raise ValueError('data is empty')
    if not chart_type:
        raise ValueError('chart_type is empty')
    chart_title = chart_title or ""

    labels = __row_for_key(labels_column, data)

    datasets_keys = set(data[0].keys())
    datasets_keys.remove(labels_column)
    datasets = list(map(lambda key: { "label": key, "data": __row_for_key(key, data) }, datasets_keys))

    with open(os.path.join(DIR_DIR, 'source', 'index.template.html'), 'r', encoding='UTF-8') as file:
        data = file\
            .read()\
            .replace("[/*[LABELS_INSERTION]*/]", str(labels))\
            .replace("[/*[DATASETS_INSERTION]*/]", str(datasets))\
            .replace("CHART_TYPE_INSERTION", chart_type)\
            .replace("CHART_TITLE_INSERTION", chart_title)
    return data

def __row_for_key(key: str, data: list[dict]) -> list:
    return list(map(lambda x: x[key], data))
