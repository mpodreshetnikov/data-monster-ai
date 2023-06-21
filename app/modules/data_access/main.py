import logging
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from .repositories.user_request_repository import UserRequestRepository
from .repositories.brain_response_repository import BrainResponseRepository
from .repositories.request_outcome_repository import RequestOutcomeRepository
from sqlalchemy import URL, create_engine

logger = logging.getLogger(__name__)

class InternalDB:
    def __init__(self, url: URL, aurl: URL):
        self.url = url
        self.aurl = aurl
        self.sync_engine = create_engine(self.url, echo=True)
        self.async_engine = create_async_engine(self.aurl, echo=True)
        self.async_session = async_sessionmaker(self.async_engine)

        self.user_request_repository = UserRequestRepository(self.async_session)
        self.brain_response_repository = BrainResponseRepository(self.async_session)
        self.request_outcome_repository = RequestOutcomeRepository(self.async_session)
