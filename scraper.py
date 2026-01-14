import pandas as pd
from playwright.sync_api import sync_playwright
import time
from bs4 import BeautifulSoup, Comment
import json
import re

class theScraper:
    def __init__(self):
        self.base_url="https://fbref.com"

    # def scrape_matches(self, team_url, season="2024-2025"):



    def scrape_setup(self, team_url):
        with sync_playwright() as p:
            browser=p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )

            context=browser.new_context(
                viewport={'width':1920, 'height':1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='en-US',        
            )

            context.add_init_script("""
                Object.defineProperty(navigator, "webdriver",{
                                    get:()=> undefined
                                    });
            """)

            page=context.new_page()

            page.goto(team_url, wait_until="domcontentloaded", timeout=60000)

            try:
                page.wait_for_selector("table",timeout=10000)
            except:
                pass

            time.sleep(5)
            html=page.content()
            browser.close()

            return html
        
    def extract_ids(self, soup, table_id):
        team_ids={}

        comments=soup.find_all(string=lambda text: isinstance(text, Comment))

        for comment in comments:
            if f'id="{table_id}"' in comment:
                comment_soup=BeautifulSoup(comment, "html.parser")
                table=comment_soup.find("table",{"id":table_id})

                if table:
                    for row in table.find_all("tr"):
                        squad_cell = row.find('th', {'data-stat': 'team'}) or row.find('td', {'data-stat': 'team'})

                        if squad_cell:
                            link=squad_cell.find("a")
                            if link and link.get("href"):
                                team_name=link.get_text(strip=True)
                                href=link.get("href")

                                match=re.search(r"/en/squads/([a-f0-9]{8})/", href)
                                if match and team_name:
                                    team_id=match.group(1)
                                    team_ids[team_name]=team_id
                        break
            return team_ids
                        
    def check_comments(self, soup, table_id):
        comments=soup.find_all(string=lambda text: isinstance(text, Comment))

        for comment in comments:
            if f'id="{table_id}"' in comment:
                comment_soup=BeautifulSoup(comment, 'html.parser') 

                try:
                    tables=pd.read_html(str(comment_soup))
                    if tables:
                        table=tables[0]
                        print("Found match logs in HTML comments")
                        break
                except Exception as e:
                    print(f"Error parsing table from comment {e}")
                    continue
            
            return None
        
    def check_columns(self, html, required_columns):
        try:
            tables=pd.read_html(html)
            for i, table in enumerate(tables):
                if any(col in str(table.columns) for col in required_columns):
                    print(f"Found match logs in table {i}")
                    return table
        except Exception as e:
            print(f"Error parsing tables: {e}")

        return None 

    def scrape_league(self, html):
        soup=BeautifulSoup(html, "html.parser")
        table=None
        team_ids={}
        table_id = "results2024-202591_overall"

        team_ids = self.extract_ids(soup, table_id)
        table=self.check_comments(soup,"results2024-202591_overall")

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
        

    
    def scrape_matches(self,html, season="2024-2025"):
        soup=BeautifulSoup(html, "html.parser")
        match_logs_df=None
        
        match_logs_df=self.check_comments(soup,"matchlogs_for")

        if match_logs_df is None:
            required_columns=["Date", "Comp", "Round", "Venue", "Result"]
            match_logs_df=self.check_columns(html, required_columns)

        if match_logs_df is not None:
            match_logs_df=self._clean_match_logs(match_logs_df)
            return match_logs_df
        else:
            raise Exception("Could not find match logs table on page.")
        
    def scrape_players(self, html):
        soup=BeautifulSoup(html, "html.parser")
        player_logs_df=None

        player_logs_df=self.check_comments(soup,"player_logs_df")

        if player_logs_df is None:
            required_columns=["Player","Nation","Pos","Age","Starts"]
            player_logs_df=self.check_columns(html, required_columns)
        
        if player_logs_df is not None:
            player_logs_df=self._clean_match_logs(player_logs_df)
            return player_logs_df
        else:
            raise Exception("Could not find match logs table on page.")

    
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
        df_teams,team_ids=scraper.scrape_league(html_prem)
        df_teams.to_csv("prem.csv",index=False)

        team_urls=scraper.build_team_urls(team_ids, "2024-2025")
        print(team_urls)

        # df_matches=scraper.scrape_matches(html)
        # df_players=scraper.scrape_players(html)

        # print(f"Successfully scraped {len(df_matches)} matches")
        # print(f"Successfully scraped {len(df_players)} matches")

        # df_matches.to_csv("villa.csv", index=False)
        # df_players.to_csv("villa_players.csv", index=False)

        

    except Exception as e:
        print(f"Error {e}")
