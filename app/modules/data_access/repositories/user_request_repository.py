import logging
from ..models.user_request import UserRequest
from .i_repository import IRepository

logger = logging.getLogger(__name__)


class UserRequestRepository(IRepository):
    def __init__(self, async_session):
        self.async_session = async_session

    async def add(self, ray_id, timestamp, username, user_id):
        try:
            async with self.async_session() as session:
                user_request = UserRequest(
                    ray_id=ray_id,
                    timestamp=timestamp,
                    username=username,
                    user_id=user_id,
                )
                session.add(user_request)
                await session.commit()
        except Exception as e:
            logger.error(f"An error occurred while adding user request: {e}")

    async def update(self, ray_id, new_data):
        try:
            async with self.async_session() as session:
                user_request = (
                    session.query(UserRequest).filter_by(ray_id=ray_id).first()
                )
                if user_request:
                    for attr, value in new_data.items():
                        setattr(user_request, attr, value)
                    await session.commit()
        except Exception as e:
            logger.error(f"An error occurred while updating user request: {e}")

    async def get(self, ray_id):
        try:
            async with self.async_session() as session:
                user_request = (
                    await session.query(UserRequest).filter_by(ray_id=ray_id).first()
                )
                return user_request
        except Exception as e:
            logger.error(f"An error occurred while retrieving user request: {e}")

    async def delete(self, ray_id):
        try:
            async with self.async_session() as session:
                user_request = (
                    await session.query(UserRequest).filter_by(ray_id=ray_id).first()
                )
                session.delete(user_request)
                await session.commit()
        except Exception as e:
            logger.error(f"An error occurred while deleting user request: {e}")
