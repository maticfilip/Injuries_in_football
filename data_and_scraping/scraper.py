import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from bs4 import BeautifulSoup, Comment
import json
import re
import random

class theScraper:
    def __init__(self):
        self.base_url="https://fbref.com"
        self.driver=None

    def init_driver(self):
        options=uc.ChromeOptions()

        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')

        self.driver=uc.Chrome(options=options)
        self.driver.set_page_load_timeout(60)

        return self.driver


    def scrape_setup(self, team_url):
        if not self.driver:
            self.init_driver()
        
        self.driver.get(team_url)

        try:
            wait=WebDriverWait(self.driver, 20)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        except:
            time.sleep(10)

        time.sleep(random.uniform(3,6))

        html=self.driver.page_source
        return html
    
    def close_driver(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver=None
        
    def extract_ids(self, soup, table_id):
        team_ids={}

        team_cells=soup.find_all('td',{'data-stat':'team'})
        for cell in team_cells:
            link=cell.find('a',href=re.compile(r'/en/squads'))

            if link:
                team_name=link.get_text(strip=True)
                href=link.get("href")

                match=re.search(r'/en/squads/([a-f0-9]{8})/',href)

                if match and team_name:
                    team_id=match.group(1)
                    team_ids[team_name]=team_id

        return team_ids


    def check_comments(self, soup, table_id, debug=False):
        comments=soup.find_all(string=lambda text: isinstance(text, Comment))

        for comment in comments:
            if f'id="{table_id}"' in comment:
                comment_soup=BeautifulSoup(comment, 'html.parser') 

                try:
                    tables=pd.read_html(str(comment_soup))
                    if tables:
                        table=tables[0]
                        print("Found match logs in HTML comments")
                        return table
                except Exception as e:
                    print(f"Error parsing table from comment {e}")
                    continue
            
        return None
        
    def check_columns(self, html, required_columns, debug=False):
        try:
            tables=pd.read_html(html)

            for i, table in enumerate(tables):
                if debug:
                    if isinstance(table.columns, pd.MultiIndex):
                        cols=['_'.join(str(c) for c in col).strip('_') for col in table.columns.values]        
                    else:
                        cols=list(table.columns)

                col_str=str(table.columns)
                matches=[col for col in required_columns if col in col_str]

                if matches:
                    return table
        except Exception as e:
            print(f"Error: {e}")

        return None      

    def scrape_league(self, html):
        soup=BeautifulSoup(html, "html.parser")
        table=None
        team_ids={}
        table_id = "results2024-202591_overall"

        team_ids = self.extract_ids(soup, table_id)
        table=self.check_comments(soup,"results2024-202591_overall", debug=debug)

        if table is None:
            required_columns=["Rk","Squad","Attendance","Top Team Scorer","Goalkeeper"]
            table=self.check_columns(html, required_columns)
        
        if table is not None:
            table=self._clean_match_logs(table)
            if 'Squad' in table.columns:
                table['team_id'] = table['Squad'].map(team_ids)
                print(f"✓ Added team_id column to DataFrame")
            
            return table, team_ids
        else:
            raise Exception("Could not find match logs table on page.")
        

    
    def scrape_matches(self,html, debug=False):
        soup=BeautifulSoup(html, "html.parser")
        match_logs_df=None
        
        match_logs_df=self.check_comments(soup,"matchlogs_for", debug=debug)

        if match_logs_df is None:
            required_columns=["Date", "Comp", "Round", "Venue", "Result"]
            match_logs_df=self.check_columns(html, required_columns, debug=debug)

        if match_logs_df is not None:
            match_logs_df=self._clean_match_logs(match_logs_df)
            return match_logs_df
        else:
            raise Exception("Could not find match logs table on page.")
        
    def scrape_all_matches_all_teams(self, debug_first=True):
        df_prem=pd.read_csv("team_urls_mapping.csv")

        all_matches=[]
        failed_teams=[]

        self.init_driver()

        try:
            for i, row in df_prem.iterrows():
                link=row["url"]
                name=row["team_name"]
                id=row["team_id"]

                try:
                    html=self.scrape_setup(link)
                    is_debug=debug_first and i==0

                    match_logs_df=self.scrape_matches(html, debug=is_debug)

                    match_logs_df["team"]=name
                    match_logs_df["team_id"]=id

                    all_matches.append(match_logs_df)
                    if i<len(df_prem)-1:
                        sleep_time=random.uniform(10,15)
                        time.sleep(sleep_time)

                except Exception as e:
                    print(f"Failed to scrape {name}: {e}")
                    failed_teams.append(name)
                    time.sleep(random.uniform(8,12))
                    continue
        finally:
            self.close_driver()
            
        if all_matches:
            combined_df=pd.concat(all_matches, ignore_index=True)
            if failed_teams:
                print(f"\n Failed teams ({len(failed_teams)}): {failed_teams}")
            return combined_df
        else:
            raise Exception("No matches were scrapped!")

        
    def scrape_players(self, html, debug=False):
        soup=BeautifulSoup(html, "html.parser")

        player_logs_df=self.check_comments(soup,"stats_standard", debug=debug)

        if player_logs_df is None:
            required_columns=["Player","Nation","Pos","Age","Starts"]
            player_logs_df=self.check_columns(html, required_columns, debug=debug)
        
        if player_logs_df is not None:
            player_logs_df=self._clean_match_logs(player_logs_df)
            return player_logs_df
        else:
            raise Exception("Could not find match logs table on page.")

    def scrape_all_players(self, debug_first=True):
        df_prem=pd.read_csv("team_urls_mapping.csv")

        all_players=[]
        failed_teams=[]

        self.init_driver()

        try:
            for i, row in df_prem.iterrows():
                link=row["url"]
                name=row["team_name"]
                id=row["team_id"]

                try:
                    html=self.scrape_setup(link)

                    is_debug=debug_first and i==0
                    player_logs_df=self.scrape_players(html, debug=is_debug)

                    player_logs_df["team"]=name
                    player_logs_df["team_id"]=id

                    all_players.append(player_logs_df)
                    if i < len(df_prem) - 1:
                        sleep_time = random.uniform(10, 15)
                        print(f"  Waiting {sleep_time:.1f}s before next request...")
                        time.sleep(sleep_time)

                except Exception as e:
                    print(f"Failed to scrape {name}: {e}")
                    failed_teams.append(name)
                    time.sleep(random.uniform(8,12))
                    continue
        finally:
            self.close_driver()
            
        if all_players:
            combined_df=pd.concat(all_players, ignore_index=True)
            return combined_df
        else:
            raise Exception("No players were scrapped!")
    
    def _clean_match_logs(self, df):
        if isinstance(df.columns, pd.MultiIndex):
            df.columns=['_'.join(col).strip('_') for col in df.columns.values]

        df=df.dropna(how="all")

        for col in df.columns:
            if df[col].dtype=="object":
                df[col]=df[col].astype(str).str.strip()
            
        return df
    
    def build_team_urls(self, team_ids, season="2024-2025"):
        team_urls={}

        for team_name, team_id in team_ids.items():
            team_slug=team_name.replace(' ','-')
            url=f"https://fbref.com/en/squads/{team_id}/{season}/{team_slug}-Stats"
            team_urls[team_name]=url

        return team_urls
    
    def scrape_multiple(self, team_urls, season, delay=4):
        pass

if __name__=="__main__":
    scraper=theScraper()

    url_prem=f"https://fbref.com/en/comps/9/2024-2025/2024-2025-Premier-League-Stats"
    html_prem=scraper.scrape_setup(url_prem)

    try:
        # df_teams,team_ids=scraper.scrape_league(html_prem)
        # df_teams.to_csv("prem.csv",index=False)
        

        # team_urls=scraper.build_team_urls(team_ids, "2024-2025")
        # team_mapping=pd.DataFrame([
        #     {'team_name':name, 'team_id':id, 'url':team_urls[name]}
        #     for name, id in team_ids.items()
        # ])
        # team_mapping.to_csv("team_urls_mapping.csv",index=False)
        all_matches_df=scraper.scrape_all_matches_all_teams(debug_first=True)
        print(len(all_matches_df))
        all_matches_df.to_csv("test_bro.csv",index=False)



        # all_players_df=scraper.scrape_all_players()
        # print(len(all_players_df))

        # all_players_df.to_csv("prem_all_players.csv", index=False)

        # print(f"\n{'='*70}")
        # print(f"FINAL RESULTS")
        # print(f"{'='*70}")
        # print(f"✓ Total matches scraped: {len(all_matches_df)}")
        # print(f"✓ Unique teams: {all_matches_df['team'].nunique()}")
        # print(f"\nSample data (first 10 rows):")
        # print(all_matches_df[['team', 'Date', 'Comp', 'Venue', 'Opponent', 'Result']].head(10))


        # df_matches=scraper.scrape_matches(html)
        # df_players=scraper.scrape_players(html)

        # print(f"Successfully scraped {len(df_matches)} matches")
        # print(f"Successfully scraped {len(df_players)} matches")

        # df_matches.to_csv("villa.csv", index=False)
        # df_players.to_csv("villa_players.csv", index=False)

        

    except Exception as e:
        print(f"Error {e}")