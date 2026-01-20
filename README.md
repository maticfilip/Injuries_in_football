# Football injury data science projcet

A data science project that is trying to create a full data pipeline for exploring recent epidemic of injuries in top flight European football.
The scraper is based around the injuries dataset from Kaggle, included in the data folder (https://www.kaggle.com/datasets/sananmuzaffarov/european-football-injuries-2020-2025).

## Features

-  Scrape match logs for all Premier League teams
-  Extract player statistics and squad information
-  Automatic team ID extraction and URL generation
-  Anti-bot detection bypass using undetected-chromedriver
-  Export data to CSV files
-  Built-in rate limiting and random delays to avoid blocking


## Project Structure

```
fbref-scraper/
├── scraper_fixed.py              # Main scraper with anti-detection
├── scraper_improved_delays.py    # Alternative version with better delays
├── scraper_stealth.py            # Playwright stealth version
├── check_blocking.py             # Diagnostic tool to check if blocked
├── team_urls_mapping.csv         # Team URLs and IDs (generated)
├── all_fixtures.csv              # Match data output
└── prem_all_players.csv          # Player data output
```

## Output Data

### Match Data
- Date, Time, Competition
- Venue (Home/Away)
- Opponent
- Result, Goals For/Against
- Attendance
- Team name and ID

### Player Data
- Player name, Nation, Position
- Age, Matches Played, Starts
- Minutes played
- Goals, Assists, Cards
- Team name and ID

## Ethical Usage

⚠️ **Please use responsibly:**
- Respect FBref's `robots.txt`
- Don't overload their servers (use appropriate delays)
- Consider supporting FBref if you use their data extensively
- Check FBref's Terms of Service before scraping
- This tool is for educational/personal use only

## Legal Disclaimer

This scraper is provided for educational purposes only. Users are responsible for complying with FBref's Terms of Service and applicable laws. The author is not responsible for misuse of this tool.

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

