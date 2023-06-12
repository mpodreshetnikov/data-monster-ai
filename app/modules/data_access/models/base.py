from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData


metadata_obj = MetaData(schema="bot_interaction_stats")
Base = declarative_base(metadata=metadata_obj)
