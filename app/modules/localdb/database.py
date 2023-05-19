from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect

DATABASE_NAME = 'sql.sqlite'

engine = create_engine(f'sqlite:///{DATABASE_NAME}')

Session = sessionmaker(bind=engine)

Base = declarative_base()

def create_db():
    inspector = inspect(engine)
    if not inspector.get_table_names():
        Base.metadata.create_all(engine)



