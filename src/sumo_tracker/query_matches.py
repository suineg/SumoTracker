import logging
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sumo_tracker.models import Match
from ..models.rikishi import Rikishi
from sqlalchemy.orm import Session
from sqlalchemy import func

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Query and display matches from the database."""
    try:
        # Connect to database
        engine = create_engine('sqlite:///sumo_matches.db')
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Get all matches
            matches = session.query(Match).all()
            logger.info(f"Found {len(matches)} matches in database")
            
            # Display matches by division
            divisions = sorted(set(match.division for match in matches))
            for division in divisions:
                logger.info(f"\nMatches in {division}:")
                div_matches = [m for m in matches if m.division == division]
                for match in div_matches:
                    result = "won" if match.win_loss == "win" else "lost"
                    technique = f"by {match.winning_technique}" if match.win_loss == "win" else ""
                    logger.info(f"{match.winner_name} {result} against {match.loser_name} {technique}")
            
            # Display winning techniques used
            techniques = {}
            for match in matches:
                if match.win_loss == "win" and match.winning_technique:
                    techniques[match.winning_technique] = techniques.get(match.winning_technique, 0) + 1
            
            logger.info("\nWinning techniques used:")
            for technique, count in sorted(techniques.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"{technique}: {count} times")
                
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error querying database: {e}")

def get_rikishi_career_stats(db: Session, rikishi_id: int) -> dict:
    """Get career statistics for a rikishi."""
    # Get basic info
    rikishi = db.query(Rikishi).filter(Rikishi.id == rikishi_id).first()
    if not rikishi:
        return None
    
    # Count wins
    wins = db.query(func.count(Match.id)).filter(Match.winner_id == rikishi_id).scalar()
    
    # Count losses
    losses = db.query(func.count(Match.id)).filter(Match.loser_id == rikishi_id).scalar()
    
    # Get stats by division
    division_stats = {}
    for division in ['Makuuchi', 'Juryo', 'Makushita', 'Sandanme', 'Jonidan', 'Jonokuchi']:
        div_wins = db.query(func.count(Match.id)).filter(
            Match.winner_id == rikishi_id,
            Match.division == division
        ).scalar()
        
        div_losses = db.query(func.count(Match.id)).filter(
            Match.loser_id == rikishi_id,
            Match.division == division
        ).scalar()
        
        if div_wins > 0 or div_losses > 0:
            division_stats[division] = {
                'wins': div_wins,
                'losses': div_losses,
                'total': div_wins + div_losses
            }
    
    return {
        'rikishi': rikishi.shikona,
        'id': rikishi_id,
        'total_wins': wins,
        'total_losses': losses,
        'total_matches': wins + losses,
        'win_percentage': round(wins / (wins + losses) * 100, 1) if wins + losses > 0 else 0,
        'division_stats': division_stats
    }

if __name__ == "__main__":
    main() 