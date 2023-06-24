import logging
from ..models.user_request import UserRequest
from sqlalchemy import select
from modules.common.timeout_execution import execute_with_timeout


logger = logging.getLogger(__name__)


class UserRequestRepository():
    def __init__(self, async_session, timeout_seconds):
        self.async_session = async_session
        self.timeout_seconds = timeout_seconds

    async def add(
        self, ray_id: str, username: str, user_id: int, question: str
    ) -> UserRequest:
        async with self.async_session() as session:
            user_request = UserRequest(
                ray_id=ray_id,
                username=username,
                user_id=user_id,
                question=question,
            )
            session.add(user_request)
            await execute_with_timeout(session.commit(), self.timeout_seconds)
            await execute_with_timeout(
                session.refresh(user_request), self.timeout_seconds
            )
            return user_request

    async def update(self, user_request: UserRequest):
        async with self.async_session() as session:
            await execute_with_timeout(
                session.merge(user_request), self.timeout_seconds
            )
            await execute_with_timeout(session.commit(), self.timeout_seconds)

    async def get(self, ray_id: str) -> UserRequest | None:
        async with self.async_session() as session:
            result = await execute_with_timeout(
                session.execute(
                    select(UserRequest).where(UserRequest.ray_id == ray_id)
                ),
                self.timeout_seconds,
            )
            user_request = result.scalar_one_or_none()
            return user_request
