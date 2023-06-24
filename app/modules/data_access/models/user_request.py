from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class UserRequest(Base):
    """
    Represents a user request made to our system.

    Attributes:
        ray_id (str): The unique identifier for the user request (primary key).
        created_at (datetime): The timestamp of when the user request was created.
        username (str): The username of the user making the request.
        user_id (int): The user ID of the user making the request.
        question (str): The initial question or input provided by the user.

        brain_responses (List[BrainResponseData]): A list of brain response data associated with the user request.
        request_outcome (RequestOutcome): The outcome of the user request.
    """

    __tablename__ = "user_request"

    ray_id = Column(String, primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    username = Column(String, nullable=False)
    user_id = Column(Integer, nullable=False)
    question = Column(String, nullable=True)

    brain_responses = relationship("BrainResponseData", back_populates="user_request")
    request_outcome = relationship(
        "RequestOutcome", uselist=False, back_populates="user_request"
    )
