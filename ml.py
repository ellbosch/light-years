import pandas as pd
from pandas.plotting import scatter_matrix

def get_dataframe(dataset):
	cols = ['fg',
	        'fga',
	        'fg3',
	        'fg3a',
	        'ft',
	        'fta',
	        'orb',
	        'drb',
	        'ast',
	        'stl',
	        'blk',
	        'tov',
	        'pf',
	        'pts']

	outcomes_all, predictions_all = [], []

	for game in dataset:
	    outcomes_all.extend(game[1][3])
	    predictions_all.append(game[0][0])
	    predictions_all.append(game[0][1])

	df = pd.DataFrame(predictions_all, columns=cols)
	df['is_home'] = pd.Series([1 if i % 2 != 0 else 0 for i in range(len(predictions_all))])
	df['outcome'] = pd.Series(outcomes_all, index=df.index)
	return df


# def matrix_feature_correlations(df):
# 	return df.corr()