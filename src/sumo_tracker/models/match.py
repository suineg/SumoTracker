from datetime import date
from sqlalchemy import Column, Integer, String, Date, create_engine, UniqueConstraint
from . import Base

class Match(Base):
    """Model representing a sumo match."""
    __tablename__ = 'matches'

    id = Column(Integer, primary_key=True)
    tournament_id = Column(Integer, nullable=False)
    wrestler_name = Column(String, nullable=False)
    division = Column(String, nullable=False)
    winning_technique = Column(String)
    win_loss = Column(String, nullable=False)  # 'win' or 'loss'
    match_date = Column(Date, nullable=False)
    opponent_name = Column(String, nullable=False)

    # Create a unique constraint to prevent duplicate matches
    __table_args__ = (
        UniqueConstraint('tournament_id', 'wrestler_name', 'opponent_name', 'match_date', name='uix_tournament_match'),
    )

    def __repr__(self):
        return f"<Match(tournament={self.tournament_id}, wrestler='{self.wrestler_name}', opponent='{self.opponent_name}', result='{self.win_loss}')>"

def init_db(db_path: str = 'sumo_matches.db') -> None:
    """Initialize the database and create all tables."""
    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)
    return engine 