from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class UserRequest(Base):
    __tablename__ = "user_request"

    ray_id = Column(String, primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    username = Column(String, nullable=False)
    user_id = Column(Integer, nullable=False)

    brain_responses = relationship("BrainResponseData", back_populates="user_request")
    request_outcome = relationship(
        "RequestOutcome", uselist=False, back_populates="user_request"
    )
