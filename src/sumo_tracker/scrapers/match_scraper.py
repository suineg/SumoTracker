import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import json
import re
from sqlalchemy.orm import Session
from ..models import Match
import requests
import time
import os
import pickle
import hashlib

logger = logging.getLogger(__name__)

class SumoWebsiteScraper:
    """Scraper for the Japan Sumo Association website."""
    
    BASE_URL = "https://www.sumo.or.jp"
    
    def __init__(self, use_cache=True, cache_dir="cache"):
        """Initialize the scraper with base URL and session."""
        self.base_url = "https://sumo.or.jp"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0'
        })
        self.cookies = {}
        self.form_data = {}
        self._tournament_dates_cache = {}

        self.use_cache = use_cache
        self.cache_dir = cache_dir

        # Create cache directory if it doesn't exist
        if self.use_cache and not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            
        # Load cached tournament dates if available
        self._tournament_dates_cache = {}
        self._load_tournament_dates_cache()

    def _load_tournament_dates_cache(self):
        """Load tournament dates cache from disk."""
        cache_path = os.path.join(self.cache_dir, "tournament_dates.pickle")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    self._tournament_dates_cache = pickle.load(f)
                logger.info(f"Loaded {len(self._tournament_dates_cache)} tournament dates from cache")
            except Exception as e:
                logger.error(f"Error loading tournament dates cache: {e}")

    def _save_tournament_dates_cache(self):
        """Save tournament dates cache to disk."""
        cache_path = os.path.join(self.cache_dir, "tournament_dates.pickle")
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(self._tournament_dates_cache, f)
            logger.info(f"Saved {len(self._tournament_dates_cache)} tournament dates to cache")
        except Exception as e:
            logger.error(f"Error saving tournament dates cache: {e}")
    
    def _get_cache_key(self, method, url, **kwargs):
        """Generate a unique cache key for a request."""
        # Create a string with all parameters
        key_parts = [method, url]
        
        # Add query params
        if 'params' in kwargs:
            for k, v in sorted(kwargs['params'].items()):
                key_parts.append(f"{k}={v}")
                
        # Add body data
        if 'data' in kwargs:
            for k, v in sorted(kwargs['data'].items()):
                key_parts.append(f"{k}={v}")
                
        # Create a hash of all parameters
        key_string = '|'.join(key_parts)
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()

    def _cached_request(self, method, url, **kwargs):
        """Make a request with caching."""
        if not self.use_cache:
            return self._throttled_request(method, url, **kwargs)
            
        # Generate cache key and path
        cache_key = self._get_cache_key(method, url, **kwargs)
        cache_path = os.path.join(self.cache_dir, f"response_{cache_key}.pickle")
        
        # Check if response is cached
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    cached_data = pickle.load(f)
                    logger.debug(f"Using cached response for {method} {url}")
                    # Create a response-like object
                    response = type('CachedResponse', (), {})()
                    response.status_code = 200
                    response.text = cached_data.get('text', '')
                    response.content = cached_data.get('content', b'')
                    response._json = cached_data.get('json', None)
                    response.json = lambda: response._json
                    response.raise_for_status = lambda: None
                    return response
            except Exception as e:
                logger.error(f"Error loading cached response: {e}")
        
        # If not cached or error, make the actual request
        response = self._throttled_request(method, url, **kwargs)
        
        # Cache the response if successful
        if response.status_code == 200:
            try:
                cached_data = {
                    'text': response.text,
                    'content': response.content,
                    'json': response.json() if 'application/json' in response.headers.get('Content-Type', '') else None
                }
                with open(cache_path, 'wb') as f:
                    pickle.dump(cached_data, f)
                logger.debug(f"Cached response for {method} {url}")
            except Exception as e:
                logger.error(f"Error caching response: {e}")
        
        return response

    async def _get_initial_data(self) -> bool:
        """Get initial page data and form tokens."""
        try:
            async with aiohttp.ClientSession(headers=self.session.headers) as session:
                async with session.get(f"{self.BASE_URL}/EnHonbashoMain/torikumi/1/1/") as response:
                    if response.status == 200:
                        self.cookies = {k: v.value for k, v in response.cookies.items()}
                        html = await response.text()
                        
                        # Parse the HTML to get form data
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Find the form inputs
                        basho_id = soup.find('input', {'id': 'basho_id'})
                        kakuzuke_id = soup.find('input', {'id': 'kakuzuke_id'})
                        day = soup.find('input', {'id': 'day'})
                        
                        if basho_id and kakuzuke_id and day:
                            self.form_data = {
                                'basho_id': basho_id.get('value'),
                                'kakuzuke_id': kakuzuke_id.get('value'),
                                'day': day.get('value')
                            }
                            logger.debug(f"Got form data: {self.form_data}")
                            return True
                        else:
                            logger.error("Could not find required form inputs")
                            return False
                    else:
                        logger.error(f"Failed to get initial data. Status: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Error getting initial data: {str(e)}")
            return False
    
    def _throttled_request(self, method, url, **kwargs):
        """Make a throttled request to avoid overloading the server."""
        # Wait 1 second between requests
        time.sleep(1)
        if method.lower() == 'get':
            return self.session.get(url, **kwargs)
        else:  # post
            return self.session.post(url, **kwargs)

    def set_cache_only_mode(self, cache_only=True):
        """Set the scraper to use only cached data (no web requests)."""
        self.use_cache = True
        self._original_throttled_request = self._throttled_request
        
        if cache_only:
            # Replace the throttled request with a method that only uses cache
            self._throttled_request = lambda method, url, **kwargs: self._cached_request_only(method, url, **kwargs)
        else:
            # Restore normal behavior
            self._throttled_request = self._original_throttled_request
            
    def _cached_request_only(self, method, url, **kwargs):
        """Get data only from cache, never from the network."""
        cache_key = self._get_cache_key(method, url, **kwargs)
        cache_path = os.path.join(self.cache_dir, f"response_{cache_key}.pickle")
        
        if not os.path.exists(cache_path):
            raise Exception(f"No cached data available for {method} {url}")
            
        with open(cache_path, 'rb') as f:
            cached_data = pickle.load(f)
            
        # Create a response-like object
        response = type('CachedResponse', (), {})()
        response.status_code = 200
        response.text = cached_data.get('text', '')
        response.content = cached_data.get('content', b'')
        response._json = cached_data.get('json', None)
        response.json = lambda: response._json
        response.raise_for_status = lambda: None
        return response

    def get_tournament_dates(self, tournament_id: int) -> Optional[Tuple[date, date]]:
        """Get the start and end dates of a tournament with caching."""
        # Check memory cache first
        if tournament_id in self._tournament_dates_cache:
            logger.debug(f"Using cached dates for tournament {tournament_id}")
            return self._tournament_dates_cache[tournament_id]
        
        # Try to get dates from manual mapping
        try:
            from tournament_dates_mapping import TOURNAMENT_DATES
            if tournament_id in TOURNAMENT_DATES:
                self._tournament_dates_cache[tournament_id] = TOURNAMENT_DATES[tournament_id]
                logger.info(f"Using mapped dates for tournament {tournament_id}: {TOURNAMENT_DATES[tournament_id][0]} to {TOURNAMENT_DATES[tournament_id][1]}")
                return TOURNAMENT_DATES[tournament_id]
        except ImportError:
            logger.debug("Tournament dates mapping not available")
            
            # If we couldn't find the date in the header, try the AJAX request
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            data = {
                'basho_id': str(tournament_id),
                'day': '1',
                'kakuzuke_id': '1'
            }
            
            ajax_url = f"{self.base_url}/EnHonbashoMain/torikumiAjax/1/1"
            response = self._throttled_request('post', ajax_url, headers=headers, data=data)
            response.raise_for_status()
            
            try:
                json_data = response.json()
                day_head = json_data.get('dayHead', '')
                date_match = re.search(r'([A-Za-z]+\s+\d+,\s+\d{4})', day_head)
                if date_match:
                    start_date = datetime.strptime(date_match.group(1), '%B %d, %Y').date()
                    end_date = start_date + timedelta(days=14)
                    logger.info(f"Tournament {tournament_id} dates from AJAX: {start_date} to {end_date}")
                    # Save to cache
                    self._tournament_dates_cache[tournament_id] = (start_date, end_date)
                    return start_date, end_date
            except (json.JSONDecodeError, AttributeError) as e:
                logger.error(f"Error parsing AJAX response for tournament {tournament_id}: {e}")
            
            logger.error(f"Could not find dates for tournament {tournament_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting tournament dates for ID {tournament_id}: {e}")
            return None

    def parse_match_data(self, json_data: dict, match_date: date, tournament_id: int, day: int) -> List[Match]:
        """Parse the JSON response and create Match objects."""
        matches = []
        
        # Safety check - verify json_data is not None
        if json_data is None:
            logger.error("Cannot parse None json_data")
            return []
            
        torikumi_data = json_data.get('TorikumiData', [])
        
        # Safety check - verify torikumi_data is not None
        if torikumi_data is None:
            logger.error("TorikumiData is None in response")
            return []
        
        for match in torikumi_data:
            try:
                # Get match details
                technique = match.get('technic_name_eng', '')
                east = match.get('east', {}) or {}  # Use empty dict if None
                west = match.get('west', {}) or {}  # Use empty dict if None
                
                # Safely get IDs
                east_id = east.get('rikishi_id')
                west_id = west.get('rikishi_id')
                
                # Get the division - both wrestlers should be in same division
                division = east.get('banzuke_name_eng', '') or west.get('banzuke_name_eng', '')
                
                # Create a single match record
                if match.get('judge') == 1:  # East wrestler won
                    matches.append(Match(
                        tournament_id=tournament_id,
                        tournament_day=day,
                        match_date=match_date,
                        division=division,
                        winner_name=east.get('shikona_eng', ''),
                        loser_name=west.get('shikona_eng', ''),
                        winner_id=east_id,
                        loser_id=west_id,
                        winning_technique=technique
                    ))
                elif match.get('judge') == 2:  # West wrestler won
                    matches.append(Match(
                        tournament_id=tournament_id,
                        tournament_day=day,
                        match_date=match_date,
                        division=division,
                        winner_name=west.get('shikona_eng', ''),
                        loser_name=east.get('shikona_eng', ''),
                        winner_id=west_id,
                        loser_id=east_id,
                        winning_technique=technique
                    ))
            except Exception as e:
                logger.error(f"Error parsing match data: {e}")
                continue
        
        return matches

    def fetch_matches(self, tournament_id: int, division: str = '1', day: int = 1) -> List[Match]:
        """Fetch matches for a specific tournament day with retry logic."""
        url = f"{self.base_url}/EnHonbashoMain/torikumiAjax/{division}/{day}/"
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        data = {
            'basho_id': str(tournament_id),
            'day': str(day),
            'kakuzuke_id': division
        }
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # First get the page to set up proper cookies
                page_url = f"{self.base_url}/EnHonbashoMain/torikumi/{division}/{day}/"
                self._cached_request('get', page_url, params={'basho_id': str(tournament_id)})
                
                # Now make the AJAX request
                response = self._cached_request('post', url, headers=headers, data=data)
                response.raise_for_status()
                
                try:
                    json_data = response.json()
                    
                    # Debug logging to see the response structure
                    if json_data is None:
                        logger.error(f"JSON response is None for tournament {tournament_id}, division {division}, day {day}")
                        return []
                        
                    # Check if we got a valid response with TorikumiData
                    if 'TorikumiData' not in json_data:
                        logger.warning(f"Response doesn't contain TorikumiData for tournament {tournament_id}, division {division}, day {day}")
                        logger.debug(f"Response keys: {list(json_data.keys())}")
                        return []
                    
                    # Get tournament dates to set correct match date
                    tournament_dates = self.get_tournament_dates(tournament_id)
                    if tournament_dates:
                        start_date, _ = tournament_dates
                        match_date = start_date + timedelta(days=day - 1)
                        return self.parse_match_data(json_data, match_date, tournament_id, day)
                    else:
                        logger.error(f"Could not get tournament dates for {tournament_id}")
                        return []
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON response: {e}")
                    logger.debug(f"Response content: {response.text[:200]}...")  # Log first 200 chars
                    retry_count += 1
                    time.sleep(2)
                    continue
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {retry_count+1}/{max_retries}): {e}")
                retry_count += 1
                time.sleep(5)  # Wait longer between retries
                continue
            except Exception as e:
                logger.error(f"Error processing response: {e}")
                return []
            
        logger.error(f"Failed to fetch matches after {max_retries} attempts")
        return []

    def get_tournament_day_results(self, tournament_id: int, day: int = 1) -> List[Match]:
        """Get all matches for a specific tournament day across all divisions."""
        all_matches = []
        
        # Fetch matches for all 6 divisions
        # 1: Makuuchi, 2: Juryo, 3: Makushita, 4: Sandanme, 5: Jonidan, 6: Jonokuchi
        for division in range(1, 7):
            division_str = str(division)
            logger.info(f"Fetching matches for tournament {tournament_id}, day {day}, division {division_str}")
            matches = self.fetch_matches(tournament_id, division=division_str, day=day)
            if matches:
                all_matches.extend(matches)
                logger.info(f"Found {len(matches)} matches in division {division_str}")
            else:
                logger.warning(f"No matches found for division {division_str} on day {day}")
                
        return all_matches

    def get_all_tournament_results(self, tournament_id: int) -> List[Match]:
        """Get all matches for an entire tournament."""
        all_matches = []
        
        # Get tournament dates to determine if we have data
        tournament_dates = self.get_tournament_dates(tournament_id)
        if not tournament_dates:
            logger.error(f"Could not get dates for tournament {tournament_id}")
            return []
            
        start_date, end_date = tournament_dates
        today = date.today()
        
        # Log the tournament dates for debugging
        logger.info(f"Tournament {tournament_id} dates: {start_date} to {end_date}")
        
        # Calculate how many days of the tournament have passed
        # If tournament is in the past, scrape all 15 days
        if end_date < today:
            days_to_scrape = 15
        # If tournament is ongoing, scrape up to today
        elif start_date <= today <= end_date:
            days_to_scrape = (today - start_date).days + 1
        # If tournament hasn't started yet
        else:
            days_to_scrape = 0
        
        if days_to_scrape > 0:
            logger.info(f"Scraping {days_to_scrape} days of tournament {tournament_id}")
            for day in range(1, days_to_scrape + 1):
                matches = self.get_tournament_day_results(tournament_id, day)
                if matches:
                    all_matches.extend(matches)
                    logger.info(f"Found {len(matches)} matches for Day {day}")
                else:
                    logger.warning(f"No matches found for Day {day}")
        else:
            logger.info(f"Tournament {tournament_id} has not started yet")
            
        return all_matches
    
    def save_tournament_to_db(self, tournament_id: int, db: Session) -> None:
        """Scrape and save a tournament to the database."""
        matches = self.get_all_tournament_results(tournament_id)
        if matches:
            # First ensure all wrestlers exist
            self.ensure_rikishi_exist(db, matches)
            
            # Then save matches
            db.add_all(matches)
            db.commit()
            logger.info(f"Successfully saved tournament {tournament_id} with {len(matches)} matches")
        else:
            logger.warning(f"No matches found for tournament {tournament_id}")

    def import_historical_tournaments(self, start_id: int, end_id: int, db: Session) -> None:
        """Import data for a range of historical tournaments."""
        total = end_id - start_id + 1
        
        for i, tournament_id in enumerate(range(start_id, end_id + 1)):
            logger.info(f"Processing tournament {tournament_id} ({i+1}/{total})")
            try:
                self.save_tournament_to_db(tournament_id, db)
            except Exception as e:
                logger.error(f"Error importing tournament {tournament_id}: {e}")
                # Continue with next tournament instead of stopping completely
    
    def ensure_rikishi_exist(self, db: Session, matches: List[Match]) -> None:
        """Ensure all wrestlers in the matches exist in the database."""
        from ..models.rikishi import Rikishi
        
        # Collect all unique wrestler IDs and names
        rikishi_data = {}
        for match in matches:
            if match.winner_id:
                rikishi_data[match.winner_id] = match.winner_name
            if match.loser_id:
                rikishi_data[match.loser_id] = match.loser_name
        
        # Check which ones already exist
        existing_ids = {r.id for r in db.query(Rikishi.id).filter(Rikishi.id.in_(rikishi_data.keys())).all()}
        
        # Create any that don't exist
        for rikishi_id, shikona in rikishi_data.items():
            if rikishi_id and rikishi_id not in existing_ids:
                db.add(Rikishi(id=rikishi_id, shikona=shikona))
                logger.info(f"Created new rikishi record: {shikona} (ID: {rikishi_id})")
        
        db.commit()

    async def test_scrape_day(self, tournament_id: int = 628, day: int = 1) -> None:
        """
        Test function to scrape and print results for a specific day.
        This is useful for debugging and verifying the scraper works.
        """
        matches = await self.get_tournament_day_results(tournament_id, day)
        if matches:
            print(f"\nFound {len(matches)} matches for Day {day}:")
            for match in matches:
                print(f"\n{match.winner_name} (Winner) vs {match.loser_name} (Loser)")
                print(f"Division: {match.division}")
                print(f"Technique: {match.winning_technique or 'N/A'}")
        else:
            print(f"\nNo matches found for Day {day}")
            
        # Print the raw response for debugging
        # Note: This won't work anymore as fetch_matches returns Match objects now, not raw JSON
        # You might want to add a separate debug method if you need to inspect the raw JSON
        print("\nNote: Raw response debugging is disabled")