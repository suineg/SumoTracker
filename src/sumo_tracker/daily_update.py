import logging
from datetime import datetime, date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Optional

from sumo_tracker.scrapers.match_scraper import SumoWebsiteScraper
from sumo_tracker.models import init_db, Match

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_current_tournament_day() -> Optional[int]:
    """Calculate the current tournament day if a tournament is in progress."""
    # Tournament starts on day 1 and ends on day 15
    # Each tournament day starts at 10:00 JST and ends around 18:00 JST
    # We'll consider the day complete after 19:00 JST
    
    today = date.today()
    
    # Get the current hour in JST (you might want to use pytz for production)
    current_hour = datetime.now().hour
    
    # If it's before 19:00, we're still on the current day
    # If it's after 19:00, we'll get tomorrow's matches
    return (today.day % 15) + 1 if current_hour < 19 else ((today.day + 1) % 15) + 1

def store_daily_matches(session, matches: list[Match], tournament_id: int) -> tuple[int, int]:
    """Store matches in database, avoiding duplicates."""
    stored_count = 0
    duplicate_count = 0
    
    # Get existing matches for this tournament day
    existing_matches = set(
        (m.tournament_id, m.wrestler_name, m.opponent_name, m.match_date)
        for m in session.query(Match).filter(
            Match.tournament_id == tournament_id,
            Match.match_date == matches[0].match_date if matches else None
        ).all()
    )
    
    for match in matches:
        match_key = (match.tournament_id, match.wrestler_name, match.opponent_name, match.match_date)
        
        if match_key not in existing_matches:
            try:
                session.add(match)
                session.flush()
                stored_count += 1
                existing_matches.add(match_key)
            except Exception as e:
                session.rollback()
                logger.debug(f"Error storing match: {e}")
                duplicate_count += 1
                continue
    
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error during final commit: {e}")
    
    if duplicate_count > 0:
        logger.info(f"Skipped {duplicate_count} duplicate matches")
    
    return len(matches), stored_count

def main():
    """Update matches for the current tournament day."""
    try:
        # Initialize database
        engine = init_db()
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Create scraper instance
            scraper = SumoWebsiteScraper()
            
            # Current tournament is always the highest ID (628 for March 2025)
            current_tournament_id = 628
            current_day = get_current_tournament_day()
            
            if not current_day:
                logger.info("No tournament day found for current date")
                return
            
            logger.info(f"Fetching matches for tournament {current_tournament_id}, Day {current_day}")
            
            # Get tournament dates to verify we're in a tournament period
            dates = scraper.get_tournament_dates(current_tournament_id)
            if dates:
                start_date, end_date = dates
                today = date.today()
                
                if start_date <= today <= end_date:
                    # Get matches for the current day
                    matches = scraper.get_tournament_day_results(current_tournament_id, current_day)
                    
                    if matches:
                        # Store matches in database
                        matches_found, stored_count = store_daily_matches(session, matches, current_tournament_id)
                        logger.info(f"Found {matches_found} matches, stored {stored_count} new matches for Day {current_day}")
                        
                        # Display matches by division
                        divisions = sorted(set(match.division for match in matches))
                        for division in divisions:
                            logger.info(f"\nMatches in {division}:")
                            div_matches = [m for m in matches if m.division == division]
                            for match in div_matches:
                                result = "won" if match.win_loss == "win" else "lost"
                                technique = f"by {match.winning_technique}" if match.win_loss == "win" else ""
                                logger.info(f"{match.wrestler_name} {result} against {match.opponent_name} {technique}")
                    else:
                        logger.warning(f"No matches found for Day {current_day}")
                else:
                    logger.info("No tournament is currently in progress")
            else:
                logger.error("Could not get tournament dates")
                
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error during daily update: {e}")

if __name__ == "__main__":
    main() 