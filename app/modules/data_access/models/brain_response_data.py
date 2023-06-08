from sqlalchemy import Column, String, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from .base import Base


class BrainResponseData(Base):
    __tablename__ = "brain_response_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_request_ray_id = Column(String, ForeignKey("user_request.ray_id"))
    question = Column(String)
    sql_script = Column(String)
    answer = Column(String)

    user_request = relationship("UserRequest", back_populates="brain_responses")
