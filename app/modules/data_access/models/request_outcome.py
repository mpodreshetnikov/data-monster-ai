from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class RequestOutcome(Base):
    """
    Represents the outcome of a request, which is the result of all processing chains.

    Attributes:
        ray_id (str): The ray ID of the associated user request (primary key).
        successful (bool): A flag indicating whether the request was successful or not.
        error (str): A string containing information about the error if the request was unsuccessful.
        user_request (UserRequest): The associated user request object.
    """

    __tablename__ = "request_outcome"

    ray_id = Column(String, ForeignKey("user_request.ray_id"), primary_key=True)
    successful = Column(Boolean, nullable=False)
    error = Column(String, nullable=True)

    user_request = relationship("UserRequest", back_populates="request_outcome")
