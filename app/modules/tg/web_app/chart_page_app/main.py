import os

DIR_DIR = os.path.realpath(os.path.dirname(__file__))

def build_chart_page(data: list[dict], labels_column: str, chart_type: str, chart_title: str) -> str:
    if not data:
        raise ValueError('data is empty')
    if not chart_type:
        raise ValueError('chart_type is empty')
    chart_title = chart_title or ""

    labels = [str(x) for x in __row_for_key(labels_column, data)]

    datasets_keys = set(data[0].keys())
    if labels_column in datasets_keys:
        datasets_keys.remove(labels_column)
    datasets = [
        { "label": key, "data": __row_for_key(key, data) }
        for key in datasets_keys
    ]

    page_str = None
    with open(os.path.join(DIR_DIR, 'source', 'index.template.html'), 'r', encoding='UTF-8') as file:
        page_str = file.read()
        page_str = page_str.replace("[/*[LABELS_INSERTION]*/]", str(labels))
        page_str = page_str.replace("[/*[DATASETS_INSERTION]*/]", str(datasets))
        page_str = page_str.replace("CHART_TYPE_INSERTION", chart_type)
        page_str = page_str.replace("CHART_TITLE_INSERTION", chart_title)
    return page_str

def __row_for_key(key: str, data: list[dict]) -> list:
    return [x.get(key, None) for x in data]
