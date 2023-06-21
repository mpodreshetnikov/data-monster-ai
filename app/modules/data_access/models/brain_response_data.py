import enum
from sqlalchemy import Column, String, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .base import Base


class BrainResponseType(enum.Enum):
    SQL = "sql"
    CHART = "chart"
    CLARIFYING_QUESTION = "clarifying_question"

class BrainResponseData(Base):
    __tablename__ = "brain_response_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_request_ray_id = Column(String, ForeignKey("user_request.ray_id"), nullable=False)
    type = Column(Enum(BrainResponseType), nullable=False, default=BrainResponseType.SQL, name="type")
    question = Column(String, nullable=False)
    answer = Column(String, nullable=False)
    sql_script = Column(String, nullable=True)

    user_request = relationship("UserRequest", back_populates="brain_responses")
