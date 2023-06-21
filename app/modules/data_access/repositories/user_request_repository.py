import logging
from ..models.user_request import UserRequest
from .i_repository import IRepository
from sqlalchemy import select


logger = logging.getLogger(__name__)


class UserRequestRepository(IRepository):
    def __init__(self, async_session):
        self.async_session = async_session

    async def add(self, ray_id: str, username, user_id, question):
        async with self.async_session() as session:
            user_request = UserRequest(
                ray_id=ray_id,
                username=username,
                user_id=user_id,
                question=question,
            )
            session.add(user_request)
            await session.commit()

    async def update(self, ray_id, new_data):
        async with self.async_session() as session:
            result = await session.execute(
                    select(UserRequest)
                    .where(UserRequest.ray_id == ray_id)
            )
            user_request = result.scalar_one_or_none()
            if user_request:
                for attr, value in new_data.items():
                    setattr(user_request, attr, value)
                await session.commit()


    async def get(self, ray_id) -> UserRequest | None:
        async with self.async_session() as session:
            result = await session.execute(
                    select(UserRequest)
                    .where(UserRequest.ray_id == ray_id)
                )
            user_request = result.scalar_one_or_none()
            return user_request

    async def delete(self, ray_id):
        async with self.async_session() as session:
            result = await session.execute(
                    select(UserRequest)
                    .where(UserRequest.ray_id == ray_id)
                )
            user_request = result.scalar_one_or_none()
            session.delete(user_request)
            await session.commit()