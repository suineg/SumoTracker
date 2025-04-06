import logging
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sumo_tracker.models import Match

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
                    logger.info(f"{match.wrestler_name} {result} against {match.opponent_name} {technique}")
            
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

if __name__ == "__main__":
    main() 