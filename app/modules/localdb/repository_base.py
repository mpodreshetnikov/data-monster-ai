from sqlalchemy import and_
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import false

class TableRepository:
    entity:object = NotImplementedError
    db:Session = NotImplementedError

    def __init__(self, db:Session, entity:object):
        self.db = db
        self.entity = entity

    def get_all(self):
        return self.db.query(self.entity)
           
    def get_by_id(self, id:str):
        with self.db() as session:
            return session.query(self.entity).filter(self.entity.id==id).one()

    def add(self, entity):
        with self.db() as session:
            session.add(entity)
            session.commit()      
        
    def delete(self, entity):
        entity.is_active = False
        self.update(entity)