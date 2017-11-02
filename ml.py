import pandas as pd
from pandas.plotting import scatter_matrix
from sklearn.linear_model import Lasso, LinearRegression
from sklearn.feature_selection import SelectFromModel, VarianceThreshold
import math

def get_dataframe(dataset):
	cols = ['fg2',
	        'fg2m',
	        'fg3',
	        'fg3m',
	        'ft',
	        'ftm',
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
	# df['is_home'] = pd.Series([1 if i % 2 != 0 else 0 for i in range(len(predictions_all))])
	df['outcome'] = pd.Series(outcomes_all, index=df.index)
	return df


def train_model(train, target):
	df_train = get_dataframe(train)
	df_predict = get_dataframe(target)
	outcomes_train = df_train['outcome']
	outcomes_predict = df_predict['outcome']

	# drop columns from train/predict df
	df_train = df_train.drop(['outcome', 'pts'], axis=1)
	df_predict = df_predict.drop(['outcome', 'pts'], axis=1)

	X, y = df_train, outcomes_train
	lasso = Lasso().fit(X, y)
	linearreg = LinearRegression().fit(X, y)

	model = linearreg

	print(model.coef_)

	X_predict, y_predict = df_predict, outcomes_predict
	predictions = model.predict(X_predict)

	return (predictions, outcomes_predict)


def test_model(predictions_away, predictions_home, outcomes_away, outcomes_home, vegas):
	correct_guesses = 0
	profit = 0

	for i in range(len(vegas)):
		predict_away, predict_home = predictions_away[i], predictions_home[i]
		outcome_away, outcome_home = outcomes_away[i], outcomes_home[i]

		spread_predicted = predict_away - predict_home
		spread_actual = outcome_away - outcome_home
		spread_vegas = vegas[i]

		if math.fabs(spread_actual - spread_predicted) < math.fabs(spread_actual - spread_vegas):
			correct_guesses += 1
			profit += 100
		#             print("CORRECT")
		else:
			profit -= 110

		#         print("outcome: %s\t predicted: %s \t vegas: %s" % (spread_actual, spread_predicted, spread_vegas))

	print(correct_guesses / len(vegas))
	print(profit)