"""
FIXED: Auto-detects your Chrome version
Install: pip install undetected-chromedriver selenium pandas beautifulsoup4 lxml
"""
import pandas as pd

import time
from bs4 import BeautifulSoup, Comment
import re
import random

class theScraperUndetected:
    def __init__(self):
        self.base_url = "https://fbref.com"
        self.driver = None
    
    def init_driver(self):
        """Initialize undetected Chrome driver with auto version detection"""
        options = uc.ChromeOptions()
        
        # Optional: run headless (but works better visible for Cloudflare)
        # options.add_argument('--headless=new')
        
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # FIXED: Let it auto-detect version instead of specifying version_main
        print("Initializing Chrome driver (auto-detecting version)...")
        self.driver = uc.Chrome(options=options)  # Removed version_main parameter
        
        # Set page load timeout
        self.driver.set_page_load_timeout(60)
        
        print("✓ Chrome driver initialized successfully")
        return self.driver
    
    def scrape_setup(self, team_url):
        """Scrape a single URL"""
        if not self.driver:
            self.init_driver()
        
        print(f"  Navigating to URL...")
        self.driver.get(team_url)
        
        # Wait for Cloudflare to pass and tables to load
        try:
            wait = WebDriverWait(self.driver, 20)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
            print("  ✓ Page loaded, tables found")
        except:
            print("  ⚠ No tables detected immediately, waiting longer...")
            time.sleep(10)
        
        # Human-like random delay
        time.sleep(random.uniform(3, 6))
        
        html = self.driver.page_source
        return html
    
    def close_driver(self):
        """Close the driver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass  # Ignore errors on close
            self.driver = None
    
    def extract_ids(self, soup, table_id):
        team_ids = {}
        team_cells = soup.find_all('td', {'data-stat': 'team'})
        
        for cell in team_cells:
            link = cell.find('a', href=re.compile(r'/en/squads'))
            if link:
                team_name = link.get_text(strip=True)
                href = link.get("href")
                match = re.search(r'/en/squads/([a-f0-9]{8})/', href)
                if match and team_name:
                    team_id = match.group(1)
                    team_ids[team_name] = team_id
        
        return team_ids

    def check_comments(self, soup, table_id):
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        
        for comment in comments:
            if f'id="{table_id}"' in comment:
                comment_soup = BeautifulSoup(comment, 'html.parser')
                try:
                    tables = pd.read_html(str(comment_soup))
                    if tables:
                        print(f"  ✓ Found table in comments: {table_id}")
                        return tables[0]
                except Exception as e:
                    continue
        return None
    
    def check_columns(self, html, required_columns, debug=False):
        try:
            tables = pd.read_html(html)
            
            if debug:
                print(f"\n  --- Found {len(tables)} tables with pandas ---")
            
            for i, table in enumerate(tables):
                if debug:
                    if isinstance(table.columns, pd.MultiIndex):
                        cols = ['_'.join(str(c) for c in col).strip('_') for col in table.columns.values]
                    else:
                        cols = list(table.columns)
                    print(f"  Table {i}: shape={table.shape}, cols={cols[:10]}")
                
                col_str = str(table.columns)
                matches = [col for col in required_columns if col in col_str]
                
                if matches:
                    print(f"  ✓ Found table {i} with columns: {matches}")
                    return table
        except Exception as e:
            print(f"  Error: {e}")
        
        return None

    def scrape_matches(self, html, debug=False):
        soup = BeautifulSoup(html, "html.parser")
        match_logs_df = self.check_comments(soup, "matchlogs_for")
        
        if match_logs_df is None:
            required_columns = ["Date", "Time", "Comp", "Round", "Venue", "Result", "Opponent"]
            match_logs_df = self.check_columns(html, required_columns, debug=debug)
        
        if match_logs_df is not None:
            match_logs_df = self._clean_match_logs(match_logs_df)
            return match_logs_df
        else:
            raise Exception("Could not find match logs table")
    
    def scrape_players(self, html, debug=False):
        soup = BeautifulSoup(html, "html.parser")
        player_logs_df = self.check_comments(soup, "stats_standard")
        
        if player_logs_df is None:
            required_columns = ["Player", "Nation", "Pos", "Age", "MP", "Starts", "Min"]
            player_logs_df = self.check_columns(html, required_columns, debug=debug)
        
        if player_logs_df is not None:
            player_logs_df = self._clean_match_logs(player_logs_df)
            return player_logs_df
        else:
            raise Exception("Could not find player table")
    
    def scrape_all_matches_all_teams(self, max_teams=None, debug_first=True):
        df_prem = pd.read_csv("team_urls_mapping.csv")
        
        if max_teams:
            df_prem = df_prem.head(max_teams)
            print(f"⚠ Testing mode: Only scraping first {max_teams} teams\n")
        
        all_matches = []
        failed_teams = []
        
        # Initialize driver once
        self.init_driver()
        
        try:
            for i, row in df_prem.iterrows():
                link = row["url"]
                name = row["team_name"]
                id_val = row["team_id"]
                
                try:
                    print(f"\n{'='*70}")
                    print(f"[{i+1}/{len(df_prem)}] Scraping: {name}")
                    print(f"{'='*70}")
                    
                    html = self.scrape_setup(link)
                    
                    is_debug = debug_first and i == 0
                    match_logs_df = self.scrape_matches(html, debug=is_debug)
                    
                    match_logs_df["team"] = name
                    match_logs_df["team_id"] = id_val
                    
                    all_matches.append(match_logs_df)
                    print(f"  ✓ Successfully scraped {len(match_logs_df)} matches")
                    
                    # Random delay between requests
                    if i < len(df_prem) - 1:
                        sleep_time = random.uniform(10, 15)
                        print(f"  Waiting {sleep_time:.1f}s before next request...")
                        time.sleep(sleep_time)
                    
                except Exception as e:
                    print(f"  ❌ Failed: {e}")
                    failed_teams.append(name)
                    time.sleep(random.uniform(8, 12))
                    continue
        
        finally:
            # Always close driver
            self.close_driver()
        
        if all_matches:
            combined_df = pd.concat(all_matches, ignore_index=True)
            if failed_teams:
                print(f"\n⚠ Failed teams ({len(failed_teams)}): {failed_teams}")
            return combined_df
        else:
            raise Exception("No matches scraped!")
    
    def scrape_all_players(self, max_teams=None, debug_first=True):
        df_prem = pd.read_csv("team_urls_mapping.csv")
        
        if max_teams:
            df_prem = df_prem.head(max_teams)
            print(f"⚠ Testing mode: Only scraping first {max_teams} teams\n")
        
        all_players = []
        failed_teams = []
        
        # Initialize driver once
        self.init_driver()
        
        try:
            for i, row in df_prem.iterrows():
                link = row["url"]
                name = row["team_name"]
                id_val = row["team_id"]
                
                try:
                    print(f"\n{'='*70}")
                    print(f"[{i+1}/{len(df_prem)}] Scraping players: {name}")
                    print(f"{'='*70}")
                    
                    html = self.scrape_setup(link)
                    
                    is_debug = debug_first and i == 0
                    player_logs_df = self.scrape_players(html, debug=is_debug)
                    
                    player_logs_df["team"] = name
                    player_logs_df["team_id"] = id_val
                    
                    all_players.append(player_logs_df)
                    print(f"  ✓ Successfully scraped {len(player_logs_df)} players")
                    
                    # Random delay between requests
                    if i < len(df_prem) - 1:
                        sleep_time = random.uniform(10, 15)
                        print(f"  Waiting {sleep_time:.1f}s before next request...")
                        time.sleep(sleep_time)
                    
                except Exception as e:
                    print(f"  ❌ Failed: {e}")
                    failed_teams.append(name)
                    time.sleep(random.uniform(8, 12))
                    continue
        
        finally:
            # Always close driver
            self.close_driver()
        
        if all_players:
            combined_df = pd.concat(all_players, ignore_index=True)
            if failed_teams:
                print(f"\n⚠ Failed teams ({len(failed_teams)}): {failed_teams}")
            return combined_df
        else:
            raise Exception("No players scraped!")
    
    def _clean_match_logs(self, df):
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join(col).strip('_') for col in df.columns.values]
        
        df = df.dropna(how="all")
        
        for col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].astype(str).str.strip()
        
        return df

if __name__ == "__main__":
    print("="*70)
    print("FBREF SCRAPER - Undetected ChromeDriver")
    print("="*70)
    
    scraper = theScraperUndetected()
    
    try:
        # OPTION 1: Test with just 1 team first
        print("\n🔍 Testing with 1 team first...")
        test_matches = scraper.scrape_all_matches_all_teams(max_teams=1, debug_first=True)
        
        print(f"\n{'='*70}")
        print(f"✓ TEST SUCCESSFUL!")
        print(f"{'='*70}")
        print(f"Matches scraped: {len(test_matches)}")
        print(f"\nFirst few rows:")
        print(test_matches.head())
        
        test_matches.to_csv("test_buraz.csv", index=False)
        print(f"\n✓ Saved to test_buraz.csv")
        
        # OPTION 2: If test works, uncomment below to scrape all teams
        # print("\n\n🔄 Now scraping ALL teams...")
        # all_matches = scraper.scrape_all_matches_all_teams(debug_first=False)
        # all_matches.to_csv("all_fixtures.csv", index=False)
        # print(f"\n✓ Saved {len(all_matches)} matches to all_fixtures.csv")
        
        # OPTION 3: Scrape players
        # print("\n\n👥 Scraping players...")
        # all_players = scraper.scrape_all_players(max_teams=1, debug_first=True)
        # all_players.to_csv("test_players.csv", index=False)
        # print(f"\n✓ Saved {len(all_players)} players to test_players.csv")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close_driver()