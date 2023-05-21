import os

from .chart_page_app.main import build_chart_page

class WebAppTypes:
    ChartPage = 'chart_page'

class WebApp:
    type: WebAppTypes
    base_url: str

    def __init__(self, type: WebAppTypes, base_url: str) -> None:
        self.type = type
        self.base_url = base_url
    
    def create_and_save(self, **kwargs) -> str:
        page = self.__build_page__(**kwargs)
        url = self.__save_page__(page)
        return url

    def __build_page__(self, question: str, js_code_insertion: str) -> str:
        if self.type == WebAppTypes.ChartPage:
            return build_chart_page(question, js_code_insertion)
        raise NotImplementedError(f"WebApp type {self.type} is not implemented")
    
    def __save_page__(self, page: str) -> str:
        # TODO: now is a fake method, to implement
        return os.path.join(self.base_url, "test.html")