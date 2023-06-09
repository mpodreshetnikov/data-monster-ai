from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData


# comment: why you assign schema here and also in settings.ini? where is the truth?
metadata_obj = MetaData(schema="bot_interaction_stats")
Base = declarative_base(metadata=metadata_obj)
