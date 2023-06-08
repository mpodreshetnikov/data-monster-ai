import logging
from ..models.request_outcome import RequestOutcome
from .i_repository import IRepository

logger = logging.getLogger(__name__)


class RequestOutcomeRepository(IRepository):
    def __init__(self, async_session):
        self.async_session = async_session

    async def add(self, ray_id, successful, error):
        try:
            async with self.async_session() as session:
                request_outcome = RequestOutcome(
                    ray_id=ray_id, successful=successful, error=error
                )
                session.add(request_outcome)
                await session.commit()
        except Exception as e:
            logger.error(f"An error occurred while adding request outcome: {e}")

    async def update(self, ray_id, new_data):
        try:
            async with self.async_session() as session:
                request_outcome = (
                    session.query(RequestOutcome).filter_by(ray_id=ray_id).first()
                )
                if request_outcome:
                    for attr, value in new_data.items():
                        setattr(request_outcome, attr, value)
                    await session.commit()
        except Exception as e:
            logger.error(f"An error occurred while updating request outcome: {e}")

    async def get(self, ray_id):
        try:
            async with self.async_session() as session:
                request_outcome = (
                    await session.query(RequestOutcome).filter_by(ray_id=ray_id).first()
                )
                return request_outcome
        except Exception as e:
            logger.error(f"An error occurred while retrieving request outcome: {e}")

    async def delete(self, ray_id):
        try:
            async with self.async_session() as session:
                request_outcome = (
                    await session.query(RequestOutcome).filter_by(ray_id=ray_id).first()
                )
                session.delete(request_outcome)
                await session.commit()
        except Exception as e:
            logger.error(f"An error occurred while deleting request outcome: {e}")
