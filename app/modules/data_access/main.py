from configparser import ConfigParser
from sqlalchemy import URL
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database


class Engine:
    def __init__(self, url):

        self.url = url
        self.engine = create_engine(self.url, echo=True)
        self.Session = sessionmaker(bind=self.engine)
        self.create_db()

    def create_db(self):
        if not database_exists(self.engine.url):
            create_database(self.engine.url)
            Base.metadata.create_all(self.engine)
        else:
            self.engine.connect()


Base = declarative_base()
