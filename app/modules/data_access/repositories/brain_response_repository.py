import logging
from ..models.brain_response_data import BrainResponseData
from .i_repository import IRepository

logger = logging.getLogger(__name__)


class BrainResponseRepository(IRepository):
    def __init__(self, async_session):
        self.async_session = async_session

    async def add(self, ray_id, question, sql_script, answer):
        try:
            async with self.async_session() as session:
                brain_response_data = BrainResponseData(
                    user_request_ray_id=ray_id,
                    question=question,
                    sql_script=sql_script,
                    answer=answer,
                )
                session.add(brain_response_data)
                await session.commit()
        except Exception as e:
            logger.error(f"An error occurred while adding brain response data: {e}")

    async def update(self, ray_id, new_data):
        try:
            async with self.async_session() as session:
                brain_response_data = (
                    session.query(BrainResponseData).filter_by(ray_id=ray_id).first()
                )
                if brain_response_data:
                    for attr, value in new_data.items():
                        setattr(brain_response_data, attr, value)
                    await session.commit()
        except Exception as e:
            logger.error(f"An error occurred while updating brain response data: {e}")

    async def get(self, ray_id):
        try:
            async with self.async_session() as session:
                brain_response_data = (
                    await session.query(BrainResponseData)
                    .filter_by(ray_id=ray_id)
                    .first()
                )
                return brain_response_data
        except Exception as e:
            logger.error(f"An error occurred while retrieving brain response data: {e}")

    async def get_all(self, ray_id):
        try:
            async with self.async_session() as session:
                brain_responses_data = (
                    await session.query(BrainResponseData)
                    .filter_by(ray_id=ray_id)
                    .all()
                )
                return brain_responses_data
        except Exception as e:
            logger.error(
                f"An error occurred while retrieving all brain response data: {e}"
            )

    async def delete(self, ray_id):
        try:
            async with self.async_session() as session:
                brain_response_data = (
                    await session.query(BrainResponseData)
                    .filter_by(ray_id=ray_id)
                    .first()
                )
                session.delete(brain_response_data)
                await session.commit()
        except Exception as e:
            logger.error(f"An error occurred while deleting brain response data: {e}")
