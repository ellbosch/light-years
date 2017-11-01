from bs4 import BeautifulSoup
from collections import defaultdict
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import requests
import mappings
import json
import os
import calendar


# generate data from new sample
def run(date_start, date_end, days_samplesize):
    download_boxscores(date_start, date_end, is_simulation=True)
    generate_player_data(date_start, date_end, days_samplesize)

# data operations on collected data
def download_boxscores(date_start, date_end, is_simulation=False):
    # get one month past date_end (because dates_season_months falls one short)
    date_end_plus1month = np.datetime64('-'.join(date_end.split('-')[:2])) + np.timedelta64(1, 'M')

    # generate array of months based on regular season schedule for the input year_season
    dates_season_months = np.arange(date_start, date_end_plus1month, dtype='datetime64[M]')

    for month in dates_season_months:
        date_end_reached = False
        month_num =  int(str(month).split('-')[1])
        month_name = calendar.month_name[month_num].lower()

        dict_links_games_month = get_links_games_month(date_end.split('-')[0], month_name)

        for day, links in dict_links_games_month.items():
            # exit if after last requested day
            if np.datetime64(day) > np.datetime64(date_end):
                date_end_reached = True
                break

            print(day)

            # output data_players to json. file path is /data_players/[days_samplesize]/[season]/[month]/data_Y_m_d.json
            date_split = str(day).split('-')
            file_path_boxscore = 'boxscores/%s/%s/%s/' % (date_split[0], date_split[1], date_split[2])

            # make folders for data players if they don't exist. if they do, skip everything else because we already computed
            if os.path.exists(file_path_boxscore):
                continue

            for link in links:
                file_name = '%s.json' % link.split('/')[2]

                # get boxscore info
                if is_simulation:
                    boxscores_calc, outcomes_calc, vegas_spread = get_boxscore(link, is_simulation=is_simulation)
                else:
                    boxscores_calc = get_boxscore(link, is_simulation=is_simulation)

                # write results to cache
                if not os.path.exists(file_path_boxscore):
                    os.makedirs(file_path_boxscore)

                # save boxscore as well
                boxes_html = [box.prettify() for box in boxscores_calc]

                with open(file_path_boxscore + file_name, 'w') as file_out:
                    if is_simulation:
                        json.dump({ 'boxscores' : boxes_html, 'outcome' : outcomes_calc, 'vegas_spread' : vegas_spread }, file_out)
                    else:
                        json.dump({ 'boxscores' : boxes_html }, file_out)

        if date_end_reached:
            break


def generate_player_data(date_start, date_end, days_samplesize):
    # generate array of days based on regular season schedule for the input year_season
    date_end_plusone = np.datetime64(date_end) + np.timedelta64(1, 'D')
    dates_season_days = np.arange(date_start, date_end_plusone, dtype='datetime64[D]')

    # for each date, we want to get the last days_samplesize of data
    for date in dates_season_days:
        print (date)

        # output data_players to json. file path is /data_players/[days_samplesize]/[season]/[month]/data_Y_m_d.json
        date_split = str(date).split('-')
        file_path_dataplayer = 'data_players/%s/%s/%s' % (days_samplesize, date_split[0], date_split[1])
        file_name = '/data_%s_%s_%s.json' % (date_split[0], date_split[1], date_split[2])

        # make folders (if they don't exist) and output data
        if not os.path.exists(file_path_dataplayer):
            os.makedirs(file_path_dataplayer)

        # get cached json files from last days_samplesize days
        date_datetime = np.datetime64(date)

        # dates_samplesize = np.arange(date_datetime - np.timedelta64(days_samplesize, 'D'), date_datetime, dtype='datetime64[D]')
        boxscores_files = get_boxscores_from_sample(date, days_samplesize)

        # don't output anything if there are no games in this sample size for this date
        if len(boxscores_files) == 0:
            continue

        # convert json files to beautifulsoup classes
        boxscores_sample = []
        outcomes_sample = []

        for file in boxscores_files:
            with open(file, 'r') as file_out:
                json_file = json.load(file_out)
                box = [BeautifulSoup(b, "html.parser") for b in json_file["boxscores"]]
                outcome = json_file["outcome"]
                boxscores_sample.append(box)
                outcomes_sample.append(outcome)

        # get statlines for each player in this sample size and save to json file
        data_players = get_player_data(boxscores_sample)
        if data_players != {}:
            with open(file_path_dataplayer + file_name, 'w') as file_out:
                json.dump(data_players, file_out)



def run_predictions_simulation(date_start, date_end, days_samplesize, unadjusted=False):
    predictions = []

	# generate array of files we will read
    date_end_plusone = np.datetime64(date_end) + np.timedelta64(1, 'D')
    dates_all = np.arange(date_start, date_end_plusone, dtype='datetime64[D]')

    for date in dates_all:
        predictions.extend(run_predictions_day(str(date), days_samplesize, is_simulation=True, unadjusted=unadjusted))

    return predictions


def run_predictions_day(date, days_samplesize, is_simulation=False, unadjusted=False):
    predictions = []
    data_players = {}
    date_split = date.split('-')
    file_path_dataplayers = 'data_players/%s/%s/%s/' % (days_samplesize, date_split[0], date_split[1])
    file_path_boxscores = 'boxscores/%s/%s/%s/' % (date_split[0], date_split[1], date_split[2])
    file_name_dataplayers = 'data_%s_%s_%s.json' % (date_split[0], date_split[1], date_split[2])

    # get player data from sample size of our choosing as well as boxscore for game we want to analyze
    try:
        with open(file_path_dataplayers + file_name_dataplayers, 'r') as file_in:
            data_players = json.load(file_in)
    except Exception as e:
        return []

    if os.path.exists(file_path_boxscores):
        files = os.listdir(file_path_boxscores)
    
        for file_name in files:
            predictions.append(predict_spreads_games(file_path_boxscores + file_name, data_players, is_simulation, unadjusted))

    return predictions


def get_player_data(boxscores): 
    #     initialize dictionary of player data
    data_players = {}
    
    for box in boxscores:
        update_player_data(box, data_players)
        
    return data_players



"""

QUERIES FOR BASKETBALL REFERENCE

"""

# returns the last n games from a requested sample
def get_boxscores_from_sample(date, days_samplesize):
    boxscores_files = []
    pointer = 0
    date_pointer = np.datetime64(date)
    date_breakpoint = date_pointer - np.timedelta64(60, 'D')

    while pointer < days_samplesize:
        # return empty set if no games in last two months
        if date_pointer == date_breakpoint:
            return []

        date_pointer = date_pointer - np.timedelta64(1, 'D')
        date_pointer_split = str(date_pointer).split("-")
        file_path_boxscore = "boxscores/%s/%s/%s/" % (date_pointer_split[0], date_pointer_split[1], date_pointer_split[2])

        # if date is a match, increase pointer 
        if os.path.exists(file_path_boxscore):
            files = os.listdir(file_path_boxscore)
            boxscores_files.extend([file_path_boxscore + file_name for file_name in files])
            pointer += 1
        else:
            print("no games for %s" % date_pointer)

    return boxscores_files


# returns a dict with the following format: { date : [ array of links ] }
def get_links_games_month(year_season, month):
    dict_links_games = defaultdict(list)
    link_query = "https://www.basketball-reference.com/leagues/NBA_%s_games-%s.html" % (year_season, month)

    page = requests.get(link_query)
    soup = BeautifulSoup(page.content, "html.parser")
    headers_game = soup.find_all(attrs={"data-stat":"box_score_text"})
    links_games = [header.find_all('a')[0].get('href') for header in headers_game if len(header.find_all('a')) > 0]
    
    # only add links that are within the sample
    for link in links_games:
        date_boxscore_raw = link[11:19]
        date_boxscore = datetime.strftime((datetime.strptime(date_boxscore_raw, '%Y%m%d')), "%Y-%m-%d")

        # add game to dict
        dict_links_games[date_boxscore].append(link)

    return dict_links_games


def get_links_games(year_season, date_end_str, days_samplesize, test_mode=False):
    games_all = []
    outcomes = []
    date_end = np.datetime64(date_end_str) + np.timedelta64(1, 'D') # to include the end date
    date_start = date_end - np.timedelta64(days_samplesize, 'D')
    
    months_links = get_list_months(year_season)
    if not test_mode:
        data_days = np.arange(date_start, date_end, dtype='datetime64[D]')  # returns array of all days we want
    else:        
        data_days = np.arange(datetime.strptime('06-09-2017', "%m-%d-%Y"), datetime.strptime('06-14-2017', "%m-%d-%Y"), dtype='datetime64[D]')  # returns array of all days we want

    data_days_str = [str(day) for day in data_days]
    
    for month in months_links:
        page = requests.get("https://www.basketball-reference.com%s" % month)
        soup = BeautifulSoup(page.content, "html.parser")
        headers_game = soup.find_all(attrs={"data-stat":"box_score_text"})
        links_games = [header.find_all('a')[0].get('href') for header in headers_game if len(header.find_all('a')) > 0]
        
        # only add links that are within the sample
        for link in links_games:
            date_boxscore_raw = link[11:19]
            date_boxscore = datetime.strftime((datetime.strptime(date_boxscore_raw, '%Y%m%d')), "%Y-%m-%d")

            # only add game to array if it's in the sample size we want
            if date_boxscore in data_days_str:
                games_all.append(link)
        
    # return [game for game in reversed(games_all)]
    return games_all


def get_list_months(year): 
    page = requests.get("https://www.basketball-reference.com/leagues/NBA_%s_games.html" % year)
    soup = BeautifulSoup(page.content, "html.parser")
    
    #     get each link for each month in a season
    links_month = [link.get('href') for link in soup.find_all("div", class_="filter")[0].find_all('a')]
    
    return links_month


def get_list_games_month(link_month):
    page = requests.get("https://www.basketball-reference.com%s" % link_month)
    soup = BeautifulSoup(page.content, "html.parser")
    headers_game = soup.find_all(attrs={"data-stat":"box_score_text"})
    links_games = [header.find_all('a')[0].get('href') for header in headers_game if len(header.find_all('a')) > 0]
    
    return  links_games
        
    
def get_boxscores(links_games, is_simulation=False):
    boxscores = []
    outcomes = []
     
    for game in links_games:
        if is_simulation:
            boxscore, outcome = get_boxscore(game, is_simulation=True)
            boxscores.append(get_boxscore(game))
            outcomes.append(outcome)
        else:
            boxscores.append(get_boxscore(game))
            
    if is_simulation:
        return (boxscores, outcomes)
    else:
        return boxscores


def get_boxscore(link_game, is_simulation=False):
    page = requests.get("https://www.basketball-reference.com%s" % link_game)
    soup = BeautifulSoup(page.content, "html.parser")
    
    div_teams = soup.find('div', {'class':'scorebox'})
    links_teams = [link.get('href') for link in div_teams.find_all('a', {'itemprop':'name'})]
    
    team_away = links_teams[0].split('/')[2]
    team_home = links_teams[1].split('/')[2]
    
    box_away = soup.find('table', {'id':'box_%s_basic' % team_away.lower()})
    box_home = soup.find('table', {'id':'box_%s_basic' % team_home.lower()})
    
    if is_simulation:
        scorebox = soup.find('div', {'class' : 'scorebox'})
        scores = scorebox.find_all('div', {'class' : 'score'})
        score_away, score_home = int(scores[0].getText()), int(scores[1].getText())
        date = link_game.split('/')[2][:8]

        # get vegas spread
        vegas_spread = get_vegas_spread(team_away, team_home, date)

        return ([box_away, box_home], (team_away, team_home, date, (score_away, score_home)), vegas_spread)
    else:
        return [box_away, box_home]
        

# extracts player data from a home and away boxscore for one game
def update_player_data(boxscores, dataset):
    for box in boxscores:
        rows_players = [row for row in box.find_all("tr") if row != None]

        # we take the last entry off the array b/c it's team totals
        for player in rows_players[:len(rows_players) - 1]:
            player_header = player.find('th', {'data-stat':'player'})

            # ensures we have valid player data by checking for the existence of one stat
            is_valid_player = True if player.find('td', { 'data-stat' : 'mp' }) != None else False

            if is_valid_player:                
                player_id = player_header.get('data-append-csv')
                player_name = player_header.get('csk')
                player_secondsplayed = int(convert_time_to_seconds(player.find('td', { 'data-stat' : 'mp' }).getText()))

                if player_secondsplayed > 0:
                    player_gp = 1   # counter for games played
                    player_fg = int(player.find('td', { 'data-stat' : 'fg' }).getText())
                    player_fgm = int(player.find('td', { 'data-stat' : 'fga' }).getText()) - player_fg
                    # player_fg_pct = player.find('td', { 'data-stat' : 'fg_pct' }).getText()
                    player_fg3 = int(player.find('td', { 'data-stat' : 'fg3' }).getText())
                    player_fg3m = int(player.find('td', { 'data-stat' : 'fg3a' }).getText()) - player_fg3
                    # player_fg3_pct = player.find('td', { 'data-stat' : 'fg3_pct' }).getText()
                    player_ft = int(player.find('td', { 'data-stat' : 'ft' }).getText())
                    player_ftm = int(player.find('td', { 'data-stat' : 'fta' }).getText()) - player_ft
                    # player_ft_pct = player.find('td', { 'data-stat' : 'ft_pct' }).getText()
                    player_orb = int(player.find('td', { 'data-stat' : 'orb' }).getText())
                    player_drb = int(player.find('td', { 'data-stat' : 'drb' }).getText())
                    # player_trb = player.find('td', { 'data-stat' : 'trb' }).getText()
                    player_ast = int(player.find('td', { 'data-stat' : 'ast' }).getText())
                    player_stl = int(player.find('td', { 'data-stat' : 'stl' }).getText())
                    player_blk = int(player.find('td', { 'data-stat' : 'blk' }).getText())
                    player_tov = int(player.find('td', { 'data-stat' : 'tov' }).getText())
                    player_pf = int(player.find('td', { 'data-stat' : 'pf' }).getText())
                    player_pts = int(player.find('td', { 'data-stat' : 'pts' }).getText())

                    # player_data_arr = np.array([player_secondsplayed, player_gp, player_fg, player_fga, player_fg3, player_fg3a, player_ft, player_fta, player_orb, player_drb, player_ast, player_stl, player_blk, player_tov, player_pf, player_pts])
                    player_data_arr = [player_secondsplayed, player_gp, player_fg, player_fgm, player_fg3, player_fg3m, player_ft, player_ftm, player_orb, player_drb, player_ast, player_stl, player_blk, player_tov, player_pf, player_pts]

                    if player_id in dataset:
                        # dataset[player_id]['data'] = np.vstack((dataset[player_id]['data'], player_data_arr))
                        dataset[player_id]['data'].append(player_data_arr)
                    else:
                        dataset[player_id] = { 'name' : player_name, 'data' : [player_data_arr] }


# function that calcuates spread for a game
def predict_spreads_games(file_box, data_players, is_simulation=False, unadjusted=False):
    predictions = []
    box = []

    # get boxscore from cache
    with open(file_box, 'r') as file_in:
        json_file = json.load(file_in)
        boxes = [ BeautifulSoup(box, 'html.parser') for box in json_file['boxscores'] ]

    # get rosters
    roster_away = get_roster(boxes[0])
    roster_home = get_roster(boxes[1])
    
    # calculate home and away team's expected value
    features_predicted_away = predict_features_team(roster_away, data_players, unadjusted)
    features_predicted_home = predict_features_team(roster_home, data_players, unadjusted)


    if is_simulation:    
        return ([features_predicted_away, features_predicted_home], json_file["outcome"], json_file["vegas_spread"])
    else:
        return (features_predicted_away, features_predicted_home)


# calculates value for a specific roster
def predict_features_team(roster, data_players, unadjusted):
    # score = 0.0
    features_predicted = []
    players_seconds_played = []
    players_games_played = []
    # players_fg_scored = []
    players_features_all = []

    # sums the statlines for each player given a sample size of days
    # for k,v in data_players.items():
    #     if k in roster:

    for player in roster:
        if player not in data_players.keys():
            continue

        statline_player = np.array(data_players[player]['data'])
        # grab the last n statlines
        # statline_player = np.array(v['data'])

        if statline_player.shape != (16,):
            data_player = np.sum(np.copy(statline_player), axis=0)
        else:
            data_player = statline_player
        
        players_seconds_played.append(data_player[0])
        players_games_played.append(data_player[1])    
        # players_fg_scored.append(data_player[15])
        players_features_all.append(np.array(data_player[2:]))

    """
    Expected FG per player = Expected seconds player will play * field goals per second
    = (sec/g * multiplyer) * (fg/sec)
    = (sec * fg * multiplyer) / (sec * g)
    = (fg * multiplyer) / g

    """
    sum_seconds_per_game = 0.0
    for i in range(len(players_seconds_played)):
        sum_seconds_per_game += float(players_seconds_played[i] / players_games_played[i])

    seconds_multiplyer = 14400 / sum_seconds_per_game if not unadjusted else 1  # adjusts active roster seconds per game to account for 14,400 active minutes on floor
    for i in range(len(players_features_all)):
        player_games_played = players_games_played[i]
        player_features_predicted = players_features_all[i]
        features_predicted.append((seconds_multiplyer / player_games_played) * player_features_predicted)


    features_predicted_sum = np.sum(features_predicted, axis=0)
    return features_predicted_sum


# returns tuple of (roster_away, roster_home) from boxscore
def get_roster(box):
    roster = []

    rows_players = [row for row in box.find_all("tr") if row != None]

    # we take the last entry off the array b/c it's team totals
    for player in rows_players[:len(rows_players) - 1]:
        player_header = player.find('th', {'data-stat':'player'})

        # ensures we have valid player data by checking for the existence of one stat
        is_valid_player = True if player.find('td', { 'data-stat' : 'mp' }) != None else False

        if is_valid_player:                
            player_id = player_header.get('data-append-csv')
            roster.append(player_id)
            
    return roster


def convert_time_to_seconds(str_time):
    time_split = str_time.split(':')
    if len(time_split) < 2:
        return 0
    else:
        return int(time_split[0]) * 60 + int(time_split[1])
    
def get_vegas_spread(team_away, team_home, date):
    page = requests.get("https://www.cbssports.com/nba/gametracker/boxscore/NBA_%s_%s@%s/" % (date, mappings.team_name_cbs[team_away], mappings.team_name_cbs[team_home]))
    soup = BeautifulSoup(page.content, "html.parser")

    try:
        spread = float(soup.find('div', {'class' : 'game-meta-odds'}).getText().split()[2])
        print("%s: %s, %s = %s" % (date, team_away, team_home, spread))
        return spread
    except Exception as e:
        print(e)
        print("DIDN'T WORK FOR: %s: %s, %s" % (date, team_away, team_home))
        return float("inf")
