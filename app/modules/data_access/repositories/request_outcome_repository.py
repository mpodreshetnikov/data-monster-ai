import logging
from ..models.request_outcome import RequestOutcome
from .i_repository import IRepository
from sqlalchemy import select
from modules.common.timeout_execution import execute_with_timeout

logger = logging.getLogger(__name__)

class RequestOutcomeRepository(IRepository):
    def __init__(self, async_session, timeout_seconds):
        self.async_session = async_session
        self.timeout_seconds = timeout_seconds

    async def add(self, request_outcome):
        async with self.async_session() as session:
            session.add(request_outcome)
            await execute_with_timeout(session.commit(), self.timeout_seconds)

    async def update(self, ray_id, new_data):
        async with self.async_session() as session:
            result = await execute_with_timeout(
                session.execute(
                    select(RequestOutcome)
                    .where(RequestOutcome.ray_id == ray_id)
                ),
                self.timeout_seconds
            )
            request_outcome = result.scalar_one_or_none()

            if request_outcome:
                for attr, value in new_data.items():
                    setattr(request_outcome, attr, value)
                await session.commit()

    async def get(self, ray_id):
        async with self.async_session() as session:
            result = await execute_with_timeout(
                session.execute(
                    select(RequestOutcome)
                    .where(RequestOutcome.ray_id == ray_id)
                ),
                self.timeout_seconds
            )
            request_outcome = result.scalar_one_or_none()
            return request_outcome

    async def delete(self, ray_id):
        async with self.async_session() as session:
            result = await execute_with_timeout(
                session.execute(
                    select(RequestOutcome)
                    .where(RequestOutcome.ray_id == ray_id)
                ),
                self.timeout_seconds
            )
            request_outcome = result.scalar_one_or_none()
            if request_outcome:
                session.delete(request_outcome)
                await execute_with_timeout(session.commit(), self.timeout_seconds)
