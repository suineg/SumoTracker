import logging
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sumo_tracker.scrapers.match_scraper import SumoWebsiteScraper
from sumo_tracker.models import init_db, Match, Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def store_test_matches(session, matches: list[Match], tournament_id: int) -> tuple[int, int]:
    """Store test matches with duplicate detection."""
    stored_count = 0
    duplicate_count = 0
    
    # Get existing matches for this tournament
    existing_matches = set(
        (m.tournament_id, m.wrestler_name, m.opponent_name, m.match_date)
        for m in session.query(Match).filter(Match.tournament_id == tournament_id).all()
    )
    
    for match in matches:
        match_key = (match.tournament_id, match.wrestler_name, match.opponent_name, match.match_date)
        
        if match_key not in existing_matches:
            try:
                session.add(match)
                session.flush()
                stored_count += 1
                existing_matches.add(match_key)
            except IntegrityError:
                session.rollback()
                logger.debug(f"Duplicate match detected: {match}")
                duplicate_count += 1
                continue
    
    try:
        session.commit()
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Error during final commit: {e}")
    
    if duplicate_count > 0:
        logger.info(f"Skipped {duplicate_count} duplicate matches")
    
    return len(matches), stored_count

def main():
    """Test the sumo match scraper and store results in database."""
    try:
        # Initialize database
        engine = init_db()
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Create scraper instance
            scraper = SumoWebsiteScraper()
            
            # Test scraping Day 1 of March 2025 tournament (ID: 628)
            tournament_id = 628
            day = 1
            
            logger.info(f"Testing scraper for tournament {tournament_id}, Day {day}")
            matches = scraper.get_tournament_day_results(tournament_id, day)
            
            if not matches:
                logger.warning("No matches found")
                return
            
            logger.info(f"Found {len(matches)} match records")
            
            # Store matches in database
            matches_found, stored_count = store_test_matches(session, matches, tournament_id)
            logger.info(f"Found {matches_found} matches, stored {stored_count} new matches")
            
            # Display match results by division
            divisions = sorted(set(match.division for match in matches))
            for division in divisions:
                logger.info(f"\nMatches in {division}:")
                div_matches = [m for m in matches if m.division == division]
                for match in div_matches:
                    result = "won" if match.win_loss == "win" else "lost"
                    technique = f"by {match.winning_technique}" if match.win_loss == "win" else ""
                    logger.info(f"{match.wrestler_name} {result} against {match.opponent_name} {technique}")
                
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error during scraping test: {e}")

if __name__ == "__main__":
    main() 