from .repository_base import TableRepository
from .database import Session
from models.sql import SQLModel

class SQLRepository(TableRepository):
    def __init__(self): 
        super().__init__(db=Session, entity=SQLModel)