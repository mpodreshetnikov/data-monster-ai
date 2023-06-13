from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class BrainResponseData(Base):
    __tablename__ = "brain_response_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_request_ray_id = Column(String, ForeignKey("user_request.ray_id"), nullable=False)
    question = Column(String, nullable=False)
    sql_script = Column(String, nullable=False)
    answer = Column(String, nullable=False)

    user_request = relationship("UserRequest", back_populates="brain_responses")
