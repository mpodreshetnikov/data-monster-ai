from sqlalchemy import Column, String, ForeignKey
from modules.localdb.database import Base

class SQLModel(Base):
    __tablename__ = 'sql_dictionary'
    
    id = Column(String, primary_key=True)
    value = Column(String)
    
    