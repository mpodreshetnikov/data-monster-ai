import logging
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy_utils import database_exists, create_database
from .repositories.user_request_repository import UserRequestRepository
from .repositories.brain_response_repository import BrainResponseRepository
from .repositories.request_outcome_repository import RequestOutcomeRepository
from sqlalchemy import create_engine
from .models.base import Base


logger = logging.getLogger(__name__)


class InternalDB:
    def __init__(self, url, aurl, **kwargs):
        self.url = url
        self.aurl = aurl
        self.sync_engine = create_engine(self.url, echo=True)
        self.async_engine = create_async_engine(self.aurl, echo=True)
        self.async_session = async_sessionmaker(self.async_engine)
        self.timeout_seconds = kwargs.get("timeout_seconds", None)

        self.user_request_repository = UserRequestRepository(self.async_session,  self.timeout_seconds)
        self.brain_response_repository = BrainResponseRepository(self.async_session,  self.timeout_seconds)
        self.request_outcome_repository = RequestOutcomeRepository(self.async_session,  self.timeout_seconds)

    def create_db(self):
        if not database_exists(self.sync_engine.url):
            create_database(self.sync_engine.url)

        Base.metadata.create_all(self.sync_engine, checkfirst=True)
