from datetime import date
from sqlalchemy import Column, Integer, String, Date, ForeignKey, create_engine, UniqueConstraint
from sqlalchemy.orm import relationship
from . import Base

class Match(Base):
    """Model representing a sumo match."""
    __tablename__ = 'matches'

    id = Column(Integer, primary_key=True)
    tournament_id = Column(Integer, nullable=False)
    tournament_day = Column(Integer)
    match_date = Column(Date, nullable=False)
    division = Column(String, nullable=False)
    
    # Keep names for backward compatibility
    winner_name = Column(String, nullable=False)
    loser_name = Column(String, nullable=False)
    
    # Add foreign keys to Rikishi table
    winner_id = Column(Integer, ForeignKey('rikishi.id'), nullable=True)
    loser_id = Column(Integer, ForeignKey('rikishi.id'), nullable=True)
    
    # Add relationships
    winner = relationship("Rikishi", foreign_keys=[winner_id])
    loser = relationship("Rikishi", foreign_keys=[loser_id])
    
    winning_technique = Column(String)

    # Create a unique constraint to prevent duplicate matches
    __table_args__ = (
        UniqueConstraint('tournament_id', 'winner_name', 'loser_name', 'match_date', name='uix_tournament_match'),
    )

    def __repr__(self):
        return f"<Match(tournament={self.tournament_id}, winner='{self.winner_name}', loser='{self.loser_name}')>"

def init_db(db_path: str = 'sumo_matches.db') -> None:
    """Initialize the database and create all tables."""
    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)
    return engine

class Rikishi(Base):
    """Model representing a sumo wrestler (rikishi)."""
    __tablename__ = 'rikishi'

    id = Column(Integer, primary_key=True)  # ID from the website
    shikona = Column(String, nullable=False, index=True)  # Wrestler name
    
    # We can add additional fields as we expand the data collection
    birth_date = Column(Date, nullable=True)
    height = Column(Integer, nullable=True)  # in cm
    weight = Column(Integer, nullable=True)  # in kg
    
    def __repr__(self):
        return f"<Rikishi(id={self.id}, shikona='{self.shikona}')>"