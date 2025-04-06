# Sumo Match Tracker

A Python-based tool for tracking sumo wrestling matches from the Japan Sumo Association website. This tool scrapes match data and stores it in a SQLite database for analysis and tracking.

## Features

- Scrapes match data from the Japan Sumo Association website
- Stores match information in a SQLite database
- Tracks wrestler names, divisions, winning techniques, and match results
- Prevents duplicate match entries
- Supports multiple tournament data collection
- Daily updates for current tournament matches

## Requirements

- Python 3.9 or higher
- pip (Python package installer)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/suineg/SumoTracker.git
cd SumoTracker
```

2. Create and activate a virtual environment:

On Windows:
```cmd
python -m venv venv
venv\Scripts\activate
```

On macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install the package:
```bash
pip install -e .
```

## Usage

After installation, the following commands will be available in your terminal:

### Initial Data Collection

To collect data from recent tournaments:
```bash
sumo-scrape
```

### Daily Updates

To update matches for the current tournament day:
```bash
sumo-daily
```

For automated daily updates, you can set up a cron job (Linux/macOS) or Task Scheduler (Windows).

#### Setting up a Cron Job (Linux/macOS)

1. Find the path to your virtual environment's Python:
```bash
which python
```

2. Create a shell script (e.g., `update_sumo.sh`):
```bash
#!/bin/bash
cd /path/to/SumoTracker
source venv/bin/activate
sumo-daily
deactivate
```

3. Make the script executable:
```bash
chmod +x update_sumo.sh
```

4. Add a cron job (runs at 19:00 local time):
```bash
crontab -e
0 19 * * * /path/to/update_sumo.sh >> /path/to/sumo_updates.log 2>&1
```

#### Setting up Task Scheduler (Windows)

1. Create a batch script (e.g., `update_sumo.bat`):
```batch
@echo off
cd C:\path\to\SumoTracker
call venv\Scripts\activate
sumo-daily
deactivate
```

2. Open Task Scheduler:
   - Create a new task
   - Set the trigger to daily at 7:00 PM
   - Action: Start a program
   - Program: `C:\path\to\update_sumo.bat`

### Test the Scraper

To test the scraper with a single day of matches:
```bash
sumo-test
```

### Query Match Data

To view stored match data and statistics:
```bash
sumo-query
```

## Database Location

By default, the SQLite database (`sumo_matches.db`) is created in your current working directory. You can specify a different location by setting the `SUMO_DB_PATH` environment variable:

On Windows:
```cmd
set SUMO_DB_PATH=C:\path\to\your\database.db
```

On macOS/Linux:
```bash
export SUMO_DB_PATH=/path/to/your/database.db
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

## Troubleshooting

### Common Issues

1. **Command not found**: If the commands aren't available after installation:
   - Make sure your virtual environment is activated
   - Try reinstalling the package: `pip install -e .`
   - Check if your Python scripts directory is in PATH

2. **Database errors**:
   - Ensure you have write permissions in the directory
   - Try specifying a different database path using `SUMO_DB_PATH`

3. **Import errors**:
   - Make sure you've installed the package with `pip install -e .`
   - Verify that all dependencies were installed correctly

### Getting Help

If you encounter any issues:
1. Check the error message and the troubleshooting section above
2. Look for similar issues in the GitHub Issues
3. Create a new issue with details about your problem

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for educational purposes only. Please respect the Japan Sumo Association's website terms of service and implement appropriate rate limiting in production use. 