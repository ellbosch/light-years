from bs4 import BeautifulSoup
from collections import defaultdict
from datetime import datetime
import matplotlib.pyplot as plt
import requests
import numpy as np
import mappings
import json
import os

# class Player():
# 	def __init__(self, name, data):
# 		self.name = name
# 		self.data = data

# data operations on collected data
def run_player_data(date_predict_raw, days_samplesize=1, is_simulation=False):
    predictions = []
    date_predict = np.datetime64(date_predict_raw)
    date_calc_end = date_predict - np.timedelta64(1, 'D')

    # get links needed for calculation
    links_games_calc = get_links_games(date_calc_end, days_samplesize)
    links_games_predict = get_links_games(date_predict, 1)

    # get boxscore info0
    boxscores_calc, outcomes_calc = get_boxscores(links_games_calc, is_simulation=is_simulation)
    boxscores_predict, outcomes_predict = get_boxscores(links_games_predict, is_simulation=is_simulation)

    # first get player statistics on n number of days
    data_players = get_player_data(boxscores_calc)

    # output data_players to json. file path is /data_players/[days_samplesize]/[season]/[month]/data_Y_m_d.json
    # season = get_season(???)
    date_split = date_predict_raw.split('-')
    file_path = 'data_players/%s/%s/%s/' % (days_samplesize, '2017', date_split[1])
    file_name = 'data_%s_%s_%s.json' % (date_split[0], date_split[1], date_split[2])

    # make folders if they don't exist
    if not os.path.exists(file_path):
        os.makedirs(file_path);

    with open(file_path + file_name, 'w') as file_out:
        json.dump(data_players, file_out)


def run_predictions(days_samplesize):
	pass

	# # predict each boxscore and then update player data
	# for box in boxscores_predict:
	# 	# predict spread for all boxscores
	# 	predictions.append(predict_spreads_games(box, data_players))

	# 	# update player data
	# 	update_player_data(box, data_players)


def get_player_data(boxscores): 
    #     initialize dictionary of player data
    data_players = defaultdict(Player)
    
    for box in boxscores:
        update_player_data(box, data_players)
        
    return data_players


    # queries for basketball-reference

    
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


def get_links_games(date_end_str, days_samplesize, test_mode=False):
    games_all = []
    outcomes = []
    year_season = '2017'
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
        spread = int(scores[0].getText()) - int(scores[1].getText())
        date = link_game.split('/')[2][:8]
        return ([box_away, box_home], (team_away, team_home, date, spread))
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
					player_fga = int(player.find('td', { 'data-stat' : 'fga' }).getText())
					# player_fg_pct = player.find('td', { 'data-stat' : 'fg_pct' }).getText()
					player_fg3 = int(player.find('td', { 'data-stat' : 'fg3' }).getText())
					player_fg3a = int(player.find('td', { 'data-stat' : 'fg3a' }).getText())
					# player_fg3_pct = player.find('td', { 'data-stat' : 'fg3_pct' }).getText()
					player_ft = int(player.find('td', { 'data-stat' : 'ft' }).getText())
					player_fta = int(player.find('td', { 'data-stat' : 'fta' }).getText())
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
                    player_data_arr = [player_secondsplayed, player_gp, player_fg, player_fga, player_fg3, player_fg3a, player_ft, player_fta, player_orb, player_drb, player_ast, player_stl, player_blk, player_tov, player_pf, player_pts]

					if player_id in dataset:
						# dataset[player_id]['data'] = np.vstack((dataset[player_id]['data'], player_data_arr))
                        dataset[player_id]['data'].append(player_data_arr)
					else:
						dataset[player_id] = { 'name' : player_name, 'data' : [player_data_arr] }


# function that calcuates spread for a game
def predict_spreads_games(box, data_players):
    predictions = []
    
    # get rosters
    roster_away = get_roster(box[0])
    roster_home = get_roster(box[1])
    
    # calculate home and away team's expected value
    value_away = calculate_value_team(roster_away, data_players)
    value_home = calculate_value_team(roster_home, data_players)

    return value_away - value_home


# calculates value for a specific roster
def calculate_value_team(roster, data_players):
	score = 0.0

	# sums the statlines for each player given a sample size of days
	for k,v in data_players.items():
		if k in roster:
			# grab the last n statlines
			fg_adjusted = 0.0

			if v.data.shape != (16,):
				data_sum = np.sum(np.copy(v.data), axis=0)
				fg_adjusted = data_sum[2] / data_sum[1]
			else:
				fg_adjusted = v.data[2] / v.data[1]

			score += fg_adjusted

	if score == 0.0:
		for k,v in data_players.items():
			if k in roster:
				print("zero score!")
	return score


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

    spread = float(soup.find('div', {'class' : 'game-meta-odds'}).getText().split()[2])
    return spread