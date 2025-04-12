import logging
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from typing import List, Dict, Optional, Tuple, Set
import time
import os
import shutil

from sumo_tracker.scrapers.match_scraper import SumoWebsiteScraper
from sumo_tracker.models import init_db, Match

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def store_matches(session, matches: List[Match], tournament_id: int) -> Tuple[int, int]:
    """
    Store matches in database, avoiding duplicates.
    
    Args:
        session: SQLAlchemy session
        matches: List of Match objects to store
        tournament_id: ID of the tournament being processed
        
    Returns:
        Tuple of (total_matches, stored_matches)
    """
    stored_count = 0
    duplicate_count = 0
    
    # Get existing matches for this tournament
    existing_matches = set(
        (m.tournament_id, m.winner_name, m.loser_name, m.match_date)
        for m in session.query(Match).filter(Match.tournament_id == tournament_id).all()
    )
    
    for match in matches:
        match_key = (match.tournament_id, match.winner_name, match.loser_name, match.match_date)
        
        if match_key not in existing_matches:
            try:
                session.add(match)
                session.flush()  # Try to flush each match individually
                stored_count += 1
                existing_matches.add(match_key)  # Add to our tracking set
            except IntegrityError as e:
                session.rollback()  # Roll back the failed match
                logger.debug(f"Duplicate match detected: {match}")
                duplicate_count += 1
                continue
            
    try:
        session.commit()  # Final commit of all successful additions
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Error during final commit: {e}")
    
    if duplicate_count > 0:
        logger.info(f"Skipped {duplicate_count} duplicate matches")
    
    return len(matches), stored_count

def clear_cache():
    """Clear the cache directory."""
    cache_dir = "cache"
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
        os.makedirs(cache_dir)
        logger.info(f"Cleared cache directory: {cache_dir}")

# Call this before creating the scraper if you think the cache is corrupted
# clear_cache()

def get_tournament_info(tournament_id: int) -> Optional[str]:
    """Get tournament name based on ID."""
    # Tournament IDs are sequential, with 628 being March 2025
    # Each year has 6 tournaments: January, March, May, July, September, November
    base_date = date(2025, 3, 1)  # March 2025 tournament (ID: 628)
    months_back = (628 - tournament_id) * 2
    tournament_date = base_date - timedelta(days=months_back * 30)  # Approximate
    return f"{tournament_date.strftime('%B %Y')} Tournament"

def main():
    """Perform initial data dump of tournament matches."""
    try:
        # Initialize database
        engine = init_db()
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Create scraper instance
            scraper = SumoWebsiteScraper(use_cache=True)
            
            # List of recent tournaments to scrape (March 2025 and earlier)
            # Tournament IDs are sequential, with 628 being March 2025
            tournaments_to_scrape = list(range(628, 626, -1))  # Last 3 tournaments
            
            total_matches = 0
            total_stored = 0
            tournament_stats: Dict[int, Dict[str, int]] = {}
            
            for tournament_id in tournaments_to_scrape:
                tournament_name = get_tournament_info(tournament_id)
                logger.info(f"\nScraping {tournament_name} (ID: {tournament_id})")
                
                # Get tournament dates
                dates = scraper.get_tournament_dates(tournament_id)
                if dates:
                    start_date, end_date = dates
                    logger.info(f"Tournament dates: {start_date} to {end_date}")
                    
                    # Get all matches for the tournament
                    matches = scraper.get_all_tournament_results(tournament_id)
                    
                    if matches:
                        # Store matches in database
                        matches_found, stored_count = store_matches(session, matches, tournament_id)
                        total_matches += matches_found
                        total_stored += stored_count
                        
                        # Record statistics
                        tournament_stats[tournament_id] = {
                            'total': matches_found,
                            'stored': stored_count
                        }
                        
                        logger.info(f"Found {matches_found} matches, stored {stored_count} new matches")
                        
                        # Add a small delay between tournaments
                        time.sleep(8)
                    else:
                        logger.warning(f"No matches found for tournament {tournament_id}")
                else:
                    logger.error(f"Could not get dates for tournament {tournament_id}")
            
            # Print final statistics
            logger.info("\nData dump complete!")
            logger.info("Tournament statistics:")
            for tournament_id in tournaments_to_scrape:
                stats = tournament_stats.get(tournament_id, {'total': 0, 'stored': 0})
                tournament_name = get_tournament_info(tournament_id)
                logger.info(f"{tournament_name}: Found {stats['total']} matches, stored {stats['stored']} new matches")
            
            logger.info(f"\nTotal matches found: {total_matches}")
            logger.info(f"Total new matches stored: {total_stored}")
                
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error during data dump: {e}")

if __name__ == "__main__":
    main() 