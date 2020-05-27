from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
import json
import datetime
from time import sleep
import pandas as pd
import numpy as np
import traceback
import requests
from bs4 import BeautifulSoup


# Crawls through all the historical games and pulls game info from each team's history chart
# Will result in a good deal of duplicates, but it's easier to just collect them all and drop duplicates later
def scrape_old_games(game_name='counterstrike', initial_page=1):
    today = str(datetime.date.today())

    opts = Options()
    opts.headless = False

    # Points to an ad blocker, which prevented all sorts of javascript refreshes that were interfering with the scrape
    path_to_extension = r'C:\Users\gannon\Desktop\Python\3.8.4_0'
    opts.add_argument('load-extension=' + path_to_extension)
    driver = Chrome(r"C:\Users\Gannon\Desktop\Python\chromedriver.exe", options=opts)

    df_columns = ['date', 't1', 'rating', 't2', 'rating_change', 'result']
    old_games = pd.DataFrame(columns=df_columns)

    page = initial_page
    try:
        while True:
            page += 1
            driver.get(f"https://www.gosugamers.net/{game_name}/matches/results?maxResults=18&page={page}")
            sleep(3)
            print(driver.current_url)

            for i in range(18):
                 # Handles both the regular page we expect and the one that loads without css whenever that happens
                try:
                    table = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "#matches > div"))
                    )
                except TimeoutException:
                    table = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "body > div"))
                    )

                games = table.find_elements_by_tag_name('a')
                driver.execute_script('arguments[0].click();', games[i])
                sleep(3)
                print('Page:', page, 'Index:', i, driver.current_url)

                try:
                    t1_name = driver.find_element_by_xpath("/html/body/div[2]/main/div[3]/div[1]/div/div[3]/div/div[1]/h2/a").text
                    t2_name = driver.find_element_by_xpath("/html/body/div[2]/main/div[3]/div[1]/div/div[3]/div/div[2]/h2/a").text

                    scripts = driver.find_elements_by_tag_name('script')

                    # Finds the appropriate javascript then parses the useful information out of them.
                    for s in scripts:
                        if "window.opponent1GraphData" in s.get_attribute('innerHTML'):

                            script_info = s.get_attribute('innerHTML').split(';')
                            try:
                                t1_dict = script_info[0].strip().replace('window.opponent1GraphData = ', '').replace('null', '0')
                                json_junk = json.loads(t1_dict)
                                games = json_junk['tooltips']

                                histories = []
                                for game in games:
                                    print(game)

                                    try:
                                        date = game['dateTime']
                                        rating = game['rating']
                                        opponent = game['opponent']
                                        rating_change = game['ratingChange']
                                        result = game['result']
                                        histories.append(
                                            {'date': date, 't1': t1_name, 'rating': rating, 't2': opponent,
                                             'rating_change': rating_change, 'result': result})

                                    except KeyError:
                                        histories.append(
                                            {'date': np.NaN, 't1': t1_name, 'rating': np.NaN, 't2': np.NaN,
                                             'rating_change': -game['decay'], 'result': 'decay'})

                                old_games = pd.concat([old_games, pd.DataFrame(histories, columns=df_columns)], axis=0)

                            except IndexError:
                                print('No t1 history')

                            try:
                                t2_dict = script_info[1].strip().replace('window.opponent2GraphData = ', '').replace('null', '0')
                                json_junk = json.loads(t2_dict)
                                games = json_junk['tooltips']

                                histories = []
                                for game in games:
                                    print(game)

                                    try:
                                        date = game['dateTime']
                                        rating = game['rating']
                                        opponent = game['opponent']
                                        rating_change = game['ratingChange']
                                        result = game['result']
                                        histories.append(
                                            {'date': date, 't1': t2_name, 'rating': rating, 't2': opponent,
                                             'rating_change': rating_change, 'result': result})

                                    except KeyError:
                                        histories.append(
                                            {'date': np.NaN, 't1': t2_name, 'rating': np.NaN, 't2': np.NaN,
                                             'rating_change': -game['decay'], 'result': 'decay'})

                                old_games = pd.concat([old_games, pd.DataFrame(histories, columns=df_columns)], axis=0)

                            except IndexError:
                                print('No t2 history')

                except NoSuchElementException:
                    print('no such element')
                    traceback.print_exc()

                driver.execute_script("window.history.go(-1);")
                sleep(3)

            old_games.to_csv(f'{game_name}_old_games_{today}_page{initial_page}.csv', index=False)

    finally:
        print('driver quit')
        driver.quit()
        old_games.to_csv(f'{game_name}_old_games_{today}_page{initial_page}.csv', index=False)


# Scrapes each team's current rank from the rankings list at www.gosugamers.net
def scrape_team_rankings(game_name='counterstrike'):
    today = str(datetime.date.today())

    rankings_details = []
    page = 1
    while page < 13:
        url = f"https://www.gosugamers.net/{game_name}/rankings/list?maxResults=50&page={page}"
        r = requests.get(url)
        soup = BeautifulSoup(r.content, 'html.parser')
        rankings = soup.find('ul', {'class': 'ranking-list'})
        rankings_list = rankings.find_all('li')

        for i, team in enumerate(rankings_list):
            rank = team.find('span', {'class': 'ranking'}).text.strip()
            points = team.find('span', {'class': 'elo'}).text.strip()
            team = team.find('a').contents[4].strip()

            rankings_details.append([team, rank, points])

        page += 1
        sleep(1)

    rankings_details = pd.DataFrame(rankings_details, columns=['team', 'rank', 'points'])
    rankings_details.to_csv(f'{game_name}_rankings_{today}.csv', index=False)
