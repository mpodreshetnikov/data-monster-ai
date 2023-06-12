import logging
from ..models.request_outcome import RequestOutcome
from .i_repository import IRepository
from sqlalchemy import select

logger = logging.getLogger(__name__)


class RequestOutcomeRepository(IRepository):
    def __init__(self, async_session):
        self.async_session = async_session

    async def add(self, ray_id, successful, error):
        async with self.async_session() as session:
            request_outcome = RequestOutcome(
                ray_id=ray_id, successful=successful, error=error
            )
            session.add(request_outcome)
            await session.commit()

    async def update(self, ray_id, new_data):
        async with self.async_session() as session:
            result = await session.execute(
                    select(RequestOutcome)
                    .where(RequestOutcome.ray_id == ray_id)
                )
            request_outcome = result.scalar_one_or_none()

            if request_outcome:
                for attr, value in new_data.items():
                    setattr(request_outcome, attr, value)
                await session.commit()

    async def get(self, ray_id):
        async with self.async_session() as session:
            result = await session.execute(
                    select(RequestOutcome)
                    .where(RequestOutcome.ray_id == ray_id)
                )
            request_outcome = result.scalar_one_or_none()
            return request_outcome

    async def delete(self, ray_id):
        async with self.async_session() as session:
            result = await session.execute(
                    select(RequestOutcome)
                    .where(RequestOutcome.ray_id == ray_id)
                )
            request_outcome = result.scalar_one_or_none()
            if request_outcome:
                session.delete(request_outcome)
                await session.commit()
