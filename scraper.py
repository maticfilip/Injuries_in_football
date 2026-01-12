import pandas as pd
from playwright.sync_api import sync_playwright
import time
from bs4 import BeautifulSoup, Comment
import json

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
    
    def scrape_matches(self,html, season="2024-2025"):
        soup=BeautifulSoup(html, "html.parser")
        match_logs_df=None
        
        match_logs_df=self.check_comments(soup,"match_logs_df")

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
    
    def scrape_multiple(self, team_urls, season, delay=4):
        pass

if __name__=="__main__":
    scraper=theScraper()

    url=f"https://fbref.com/en/squads/8602292d/2024-2025/Aston-Villa-Stats#all_matchlogs"
    html=scraper.scrape_setup(url)

    try:
        df_matches=scraper.scrape_matches(html)
        df_players=scraper.scrape_players(html)

        print(f"Successfully scraped {len(df_matches)} matches")
        print(f"Successfully scraped {len(df_players)} matches")

        df_matches.to_csv("villa.csv", index=False)
        df_players.to_csv("villa_players.csv", index=False)
    except Exception as e:
        print(f"Error {e}")
