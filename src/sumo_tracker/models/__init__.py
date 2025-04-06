from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

# Import models after Base is defined
from .match import Match

def init_db(db_path: str = 'sumo_matches.db') -> None:
    """Initialize the database."""
    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)
    return engine

__all__ = ['Match', 'init_db', 'Base']
