from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship
from .base import Base


class UserRequest(Base):
    __tablename__ = "user_request"

    ray_id = Column(String, primary_key=True)
    # comment: by default is Nullable. do we really need nullable here?
    timestamp = Column(String)
    # comment: by default is Nullable. do we really need nullable here?
    username = Column(String)
    # comment: by default is Nullable. do we really need nullable here?
    user_id = Column(Integer)

    brain_responses = relationship("BrainResponseData", back_populates="user_request")
    request_outcome = relationship(
        "RequestOutcome", uselist=False, back_populates="user_request"
    )
