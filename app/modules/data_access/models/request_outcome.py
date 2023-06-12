from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class RequestOutcome(Base):
    __tablename__ = "request_outcome"

    ray_id = Column(String, ForeignKey("user_request.ray_id"), primary_key=True)
    successful = Column(Boolean, nullable=False)
    error = Column(String, nullable=False)

    user_request = relationship("UserRequest", back_populates="request_outcome")
