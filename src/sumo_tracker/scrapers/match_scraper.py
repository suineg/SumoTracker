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

logger = logging.getLogger(__name__)

class SumoWebsiteScraper:
    """Scraper for the Japan Sumo Association website."""
    
    BASE_URL = "https://www.sumo.or.jp"
    
    def __init__(self):
        """Initialize the scraper with base URL and session."""
        self.base_url = "https://sumo.or.jp"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.cookies = {}
        self.form_data = {}

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

    def get_tournament_dates(self, tournament_id: int) -> Optional[Tuple[date, date]]:
        """Get the start and end dates of a tournament."""
        url = f"{self.base_url}/EnHonbashoMain/torikumi/1/1/"
        params = {'basho_id': str(tournament_id)}
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the tournament date header (format: "Day 1  March 9, 2025")
            day_header = soup.find('div', string=re.compile(r'Day\s+1.*\d{4}'))
            if not day_header:
                # Try finding it in the dayHead div
                day_head = soup.find('div', {'class': 'dayHead'})
                if day_head:
                    day_header = day_head.get_text()
            
            if day_header:
                # Extract the date from the header
                date_match = re.search(r'([A-Za-z]+\s+\d+,\s+\d{4})', str(day_header))
                if date_match:
                    start_date = datetime.strptime(date_match.group(1), '%B %d, %Y').date()
                    end_date = start_date + timedelta(days=14)  # Tournaments are 15 days
                    logger.info(f"Tournament dates: {start_date} to {end_date}")
                    return start_date, end_date
            
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
            
            ajax_url = f"{self.base_url}/EnHonbashoMain/torikumiAjax/1/1/"
            response = self.session.post(ajax_url, headers=headers, data=data)
            response.raise_for_status()
            
            try:
                json_data = response.json()
                day_head = json_data.get('dayHead', '')
                date_match = re.search(r'([A-Za-z]+\s+\d+,\s+\d{4})', day_head)
                if date_match:
                    start_date = datetime.strptime(date_match.group(1), '%B %d, %Y').date()
                    end_date = start_date + timedelta(days=14)
                    logger.info(f"Tournament dates from AJAX: {start_date} to {end_date}")
                    return start_date, end_date
            except (json.JSONDecodeError, AttributeError) as e:
                logger.error(f"Error parsing AJAX response: {e}")
            
            logger.error("Could not find tournament dates")
            return None
            
        except Exception as e:
            logger.error(f"Error getting tournament dates: {e}")
            return None

    def parse_match_data(self, json_data: dict, match_date: date, tournament_id: int) -> List[Match]:
        """Parse the JSON response and create Match objects."""
        matches = []
        torikumi_data = json_data.get('TorikumiData', [])
        
        for match in torikumi_data:
            # Get match details
            technique = match.get('technic_name_eng', '')
            east = match.get('east', {})
            west = match.get('west', {})
            
            # Create match for east wrestler (if they won)
            if match.get('judge') == 1:  # East wrestler won
                matches.append(Match(
                    tournament_id=tournament_id,
                    wrestler_name=east.get('shikona_eng', ''),
                    division=east.get('banzuke_name_eng', ''),
                    winning_technique=technique,
                    win_loss='win',
                    match_date=match_date,
                    opponent_name=west.get('shikona_eng', '')
                ))
                # Add the corresponding loss for west wrestler
                matches.append(Match(
                    tournament_id=tournament_id,
                    wrestler_name=west.get('shikona_eng', ''),
                    division=west.get('banzuke_name_eng', ''),
                    winning_technique=technique,
                    win_loss='loss',
                    match_date=match_date,
                    opponent_name=east.get('shikona_eng', '')
                ))
            elif match.get('judge') == 2:  # West wrestler won
                matches.append(Match(
                    tournament_id=tournament_id,
                    wrestler_name=west.get('shikona_eng', ''),
                    division=west.get('banzuke_name_eng', ''),
                    winning_technique=technique,
                    win_loss='win',
                    match_date=match_date,
                    opponent_name=east.get('shikona_eng', '')
                ))
                # Add the corresponding loss for east wrestler
                matches.append(Match(
                    tournament_id=tournament_id,
                    wrestler_name=east.get('shikona_eng', ''),
                    division=east.get('banzuke_name_eng', ''),
                    winning_technique=technique,
                    win_loss='loss',
                    match_date=match_date,
                    opponent_name=west.get('shikona_eng', '')
                ))
        
        return matches

    def fetch_matches(self, tournament_id: int, division: str = '1', day: int = 1) -> List[Match]:
        """Fetch matches for a specific tournament day."""
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
        
        try:
            # First get the page to set up proper cookies
            page_url = f"{self.base_url}/EnHonbashoMain/torikumi/{division}/{day}/"
            self.session.get(page_url)
            
            # Now make the AJAX request
            response = self.session.post(url, headers=headers, data=data)
            response.raise_for_status()
            
            try:
                json_data = response.json()
                # Get tournament dates to set correct match date
                tournament_dates = self.get_tournament_dates(tournament_id)
                if tournament_dates:
                    start_date, _ = tournament_dates
                    match_date = start_date + timedelta(days=day - 1)
                    return self.parse_match_data(json_data, match_date, tournament_id)
                else:
                    return []
            except json.JSONDecodeError:
                # Try to extract JSON from text response
                json_match = re.search(r'\{.*\}', response.text)
                if json_match:
                    json_data = json.loads(json_match.group(0))
                    return self.parse_match_data(json_data, datetime.now().date(), tournament_id)
                else:
                    logger.error("Could not find JSON in response")
                    return []
                    
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching matches: {e}")
            return []
        except Exception as e:
            logger.error(f"Error processing response: {e}")
            return []

    def get_tournament_day_results(self, tournament_id: int, day: int = 1) -> List[Match]:
        """Get all matches for a specific tournament day."""
        # For now, we're only focusing on Makuuchi division (division='1')
        matches = self.fetch_matches(tournament_id, division='1', day=day)
        return matches

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
        
        # Calculate how many days of the tournament have passed
        days_to_scrape = min(15, (today - start_date).days + 1) if today >= start_date else 0
        
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

    async def test_scrape_day(self, tournament_id: int = 628, day: int = 1) -> None:
        """
        Test function to scrape and print results for a specific day.
        This is useful for debugging and verifying the scraper works.
        """
        matches = await self.get_tournament_day_results(tournament_id, day)
        if matches:
            print(f"\nFound {len(matches)} matches for Day {day}:")
            for match in matches:
                print(f"\n{match.wrestler_name} vs {match.opponent_name}")
                print(f"Winner: {'Yes' if match.is_winner else 'No'}")
                print(f"Technique: {match.winning_technique or 'N/A'}")
        else:
            print(f"\nNo matches found for Day {day}")
            
        # Print the raw response for debugging
        data = await self.fetch_matches(tournament_id, 1, day)
        if data:
            print("\nRaw response structure:")
            print(json.dumps(data, indent=2)[:1000])  # Print first 1000 characters for inspection 