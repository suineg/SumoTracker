import asyncio
import logging
from datetime import datetime, date, timedelta
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models.match import init_db
from .scrapers.match_scraper import MatchScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sumo_tracker.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def get_db_session():
    """Create and return a database session."""
    db_path = os.getenv('SUMO_DB_PATH', 'sumo_matches.db')
    db_url = f'sqlite:///{db_path}'
    
    # Ensure the database directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    engine = create_engine(db_url)
    init_db(db_path)
    
    Session = sessionmaker(bind=engine)
    return Session()

async def main():
    """Main function to run the scraper."""
    try:
        # Initialize database session
        session = get_db_session()
        
        # Configure scraper
        base_url = os.getenv('SUMO_BASE_URL', 'http://example-sumo-site.com')
        scraper = MatchScraper(base_url, session)
        
        # Calculate date range
        # By default, check the last 7 days to catch any updates
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        # Update matches
        await scraper.update_matches(start_date, end_date)
        
        logger.info(f"Successfully completed scraping from {start_date} to {end_date}")
        
    except Exception as e:
        logger.error(f"Error in main scraper execution: {str(e)}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    asyncio.run(main()) 