# Sumo Match Tracker

A Python-based tool for tracking sumo wrestling matches from the Japan Sumo Association website. This tool scrapes match data and stores it in a SQLite database for analysis and tracking.

## Features

- Scrapes match data from the Japan Sumo Association website
- Stores match information in a SQLite database
- Tracks wrestler names, divisions, winning techniques, and match results
- Prevents duplicate match entries
- Supports multiple tournament data collection

## Requirements

- Python 3.9+
- SQLAlchemy
- Requests
- BeautifulSoup4
- aiohttp

## Installation

1. Clone the repository:
```bash
git clone https://github.com/suineg/SumoTracker.git
cd SumoTracker
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e .
```

## Usage

### Initial Data Collection

To perform an initial data collection of recent tournaments:

```bash
PYTHONPATH=src python -m sumo_tracker.initial_data_dump
```

### Testing the Scraper

To test the scraper with a single day of matches:

```bash
PYTHONPATH=src python -m sumo_tracker.test_scrape
```

## Database Schema

The SQLite database contains a single table `matches` with the following schema:

- `id`: Primary key
- `tournament_id`: Tournament identifier
- `wrestler_name`: Name of the wrestler
- `division`: Division name
- `winning_technique`: Technique used to win (if applicable)
- `win_loss`: Result of the match ('win' or 'loss')
- `match_date`: Date of the match
- `opponent_name`: Name of the opponent

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for educational purposes only. Please respect the Japan Sumo Association's website terms of service and implement appropriate rate limiting in production use. 