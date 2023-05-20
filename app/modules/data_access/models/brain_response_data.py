from sqlalchemy import Column, String, ForeignKey
from modules.data_access.main import Base


class BrainResponseData(Base):
    __tablename__ = 'brain_response_data'

    ray_id = Column(String, primary_key=True)
    sql_script = Column(String)
