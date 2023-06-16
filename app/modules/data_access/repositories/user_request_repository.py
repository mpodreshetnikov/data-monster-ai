import logging
from ..models.user_request import UserRequest
from .i_repository import IRepository
from sqlalchemy import select
from modules.common.timeout_execution import execute_with_timeout


logger = logging.getLogger(__name__)


class UserRequestRepository(IRepository):
    def __init__(self, async_session, timeout_seconds):
        self.async_session = async_session
        self.timeout_seconds = timeout_seconds

    async def add(self, user_request):
        async with self.async_session() as session:
            session.add(user_request)
            await execute_with_timeout(session.commit(), self.timeout_seconds)

    async def update(self, ray_id, new_data):
        async with self.async_session() as session:
            result = await execute_with_timeout(
                session.execute(
                    select(UserRequest)
                    .where(UserRequest.ray_id == ray_id)
                ),
                self.timeout_seconds
            )
            user_request = result.scalar_one_or_none()
            if user_request:
                for attr, value in new_data.items():
                    setattr(user_request, attr, value)
                await execute_with_timeout(session.commit(), self.timeout_seconds)

    async def get(self, ray_id):
        async with self.async_session() as session:
            result = await execute_with_timeout(
                session.execute(
                    select(UserRequest)
                    .where(UserRequest.ray_id == ray_id)
                ),
                self.timeout_seconds
            )
            user_request = result.scalar_one_or_none()
            return user_request

    async def delete(self, ray_id):
        async with self.async_session() as session:
            result = await execute_with_timeout(
                session.execute(
                    select(UserRequest)
                    .where(UserRequest.ray_id == ray_id)
                ),
                self.timeout_seconds
            )
            user_request = result.scalar_one_or_none()
            session.delete(user_request)
            await execute_with_timeout(session.commit(), self.timeout_seconds)
