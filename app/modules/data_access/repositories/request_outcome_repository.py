import logging
from ..models.request_outcome import RequestOutcome
from sqlalchemy import select
from modules.common.timeout_execution import execute_with_timeout

logger = logging.getLogger(__name__)


class RequestOutcomeRepository():
    def __init__(self, async_session, timeout_seconds):
        self.async_session = async_session
        self.timeout_seconds = timeout_seconds

    async def add(self, ray_id: str, successful: bool, error: str) -> RequestOutcome:
        async with self.async_session() as session:
            request_outcome = RequestOutcome(
                ray_id=ray_id, successful=successful, error=error
            )
            session.add(request_outcome)
            await execute_with_timeout(session.commit(), self.timeout_seconds)
            await execute_with_timeout(
                session.refresh(request_outcome), self.timeout_seconds
            )
            return request_outcome

    async def update(self, request_outcome: RequestOutcome):
        async with self.async_session() as session:
            await execute_with_timeout(
                session.merge(request_outcome), self.timeout_seconds
            )
            await execute_with_timeout(session.commit(), self.timeout_seconds)

    async def get(self, ray_id: str) -> RequestOutcome | None:
        async with self.async_session() as session:
            result = await execute_with_timeout(
                session.execute(
                    select(RequestOutcome).where(RequestOutcome.ray_id == ray_id)
                ),
                self.timeout_seconds,
            )
            request_outcome = result.scalar_one_or_none()
            return request_outcome
