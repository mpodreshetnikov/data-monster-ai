from .repository_sql import SQLRepository
from .database import Session
from models.sql import SQLModel


class SQLService: 
    def __init__(self) -> None:
        self.sql_repr = SQLRepository()
    def get_sql_strs_by_ray_id(self, ray_id:str):
        return self.sql_repr.get_by_id(ray_id)
    def save_sql_str(self, sql_str:SQLModel):
        return self.sql_repr.add(sql_str)