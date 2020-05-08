# ----------------------------------------------------------------------------------------------------
# DraftKings NBA Showdown, Lineup Optimization Algorithm v6
# OPRK weighted std dev adjustment to fppg
# by John Lee
# ----------------------------------------------------------------------------------------------------

import urllib
import json
import pandas as pd
import math
import os
import csv
import time
import numpy as np

from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog

os.chdir('C:\\Users\\jogel\\Desktop\\draftkings\\showdown\\nba')

# ----------------------------------------------------------------------------------------------------
# update DRAFT_GROUP_ID from https://api.draftkings.com/draftgroups/v1/
# ----------------------------------------------------------------------------------------------------

DRAFT_GROUP_ID = 33800
CONTEST_ID = 'OKC_NOP'

salary = 50000
min_sal = 40000

# number of entries to output (top projected fppg)
entries = 20

# last x games to weight with lxg_wt
last_x = 5

# weights for: last x games, season
lxg_wt = 0.60
seas_wt = 0.40

url = 'https://api.draftkings.com/draftgroups/v1/draftgroups/' + str(DRAFT_GROUP_ID) + '/draftables?format=json'

response = urllib.request.urlopen(url)
json_raw = json.loads(response.read())
data_raw = pd.DataFrame.from_dict(json_raw["draftables"])

data_dict = {}
# {name: capt_id, util_id, salary, team, fppg, status, oprk}

for i in data_raw.values:

	if i[4][0]['id'] == 219:
		try:
			fppg = float(i[4][0]['sortValue'])
		except:
			fppg = 0.0
		try:
			oprk = int(i[4][1]['sortValue'])
		except:
			oprk = 0

	else:
		try:
			fppg = float(i[4][1]['sortValue'])
		except:
			fppg = 0.0
		try:
			oprk = int(i[4][0]['sortValue'])
		except:
			oprk = 0

	if i[20] == 476:
		if i[2] in data_dict:
			data_dict[i[2]][0] = i[5]
		else:
			data_dict[i[2]] = [i[5], 0, int(i[21] * 2 / 3), i[24], fppg, i[23], oprk]

	else:
		if i[2] in data_dict:
			data_dict[i[2]][1] = i[5]
		else:
			data_dict[i[2]] = [0, i[5], i[21], i[24], fppg, i[23], oprk]

# ----------------------------------------------------------------------------------------------------
# pull game logs with nba_api
# ----------------------------------------------------------------------------------------------------

def name_change(old, new):
	data_dict[new] = data_dict[old] 
	del data_dict[old] 

#name_change('Robert Williams', 'Robert Williams III')
#data_dict['Robert Williams III'][5] = 'O'

nba_players = players.get_players()
time.sleep(0.5)

for i in data_dict.keys():
	if (data_dict[i][4] != 0) and (data_dict[i][5] != 'O'):
		print('--------------------------------------------------')
		print(i)
		try:
			pl = [player for player in nba_players if player['full_name'] == i][0]['id']
			log_all = playergamelog.PlayerGameLog(player_id = pl).get_data_frames()[0]
			time.sleep(0.5)
			log_x = playergamelog.PlayerGameLog(player_id = pl).get_data_frames()[0][0:last_x]
			time.sleep(0.5)

			# STANDARD DEVIATION CALCULATION
			log_lst = []

			for ind, row in log_all.iterrows():
				log_fp = row['PTS'] + (row['FG3M'] * .5) + (row['REB'] * 1.25) + (row['AST'] * 1.5) + ((row['STL'] + row['BLK']) * 2) - (row['TOV'] * .5)
				
				DD_TD = 0
				if row['PTS'] >= 10: DD_TD += 1
				if row['REB'] >= 10: DD_TD += 1
				if row['AST'] >= 10: DD_TD += 1
				if row['STL'] >= 10: DD_TD += 1
				if row['BLK'] >= 10: DD_TD += 1

				if DD_TD == 2: log_fp += 1.5
				elif DD_TD >= 3: log_fp += 4.5

				log_lst.append(log_fp)

			if len(log_lst) > 0:
				log_std = round(np.std(log_lst), 2)
			else:
				log_std = 0

			# LAST X GAMES AVERAGE FPPG
			fpx = []

			for ind, row in log_x.iterrows():
				log_fp = row['PTS'] + (row['FG3M'] * .5) + (row['REB'] * 1.25) + (row['AST'] * 1.5) + ((row['STL'] + row['BLK']) * 2) - (row['TOV'] * .5)
				
				DD_TD = 0
				if row['PTS'] >= 10: DD_TD += 1
				if row['REB'] >= 10: DD_TD += 1
				if row['AST'] >= 10: DD_TD += 1
				if row['STL'] >= 10: DD_TD += 1
				if row['BLK'] >= 10: DD_TD += 1

				if DD_TD == 2: log_fp += 1.5
				elif DD_TD >= 3: log_fp += 4.5

				fpx.append(log_fp)

			if len(fpx) > 0:
				fpx_avg = np.mean(fpx)
			else:
				fpx_avg = 0

			seas = data_dict[i][4]
			oprk = data_dict[i][6]

			if fpx_avg == 0:
				fppg = seas
			else:
				fppg = (fpx_avg * lxg_wt) + (seas * seas_wt)

			data_dict[i][4] = max(round(fppg + (oprk - 15.5) / 14.5 * log_std, 2), 0)

			print('Last 5 Games: ' + str(round(fpx_avg, 2)))
			print('Season Perf.: ' + str(round(seas, 2)))
			print('Weighted Pre: ' + str(round(fppg, 2)))
			print('OPRK: ' + str(oprk))
			print('STD: ' + str(log_std))
			print('ORPK STD ADJ: ' + str(data_dict[i][4]))

		except IndexError:
			seas = data_dict[i][4]
			oprk = data_dict[i][6]

			print('Season Perf.: ' + str(round(seas, 2)))
			print('OPRK: ' + str(oprk))
			print('ORPK ADJ: ' + str(max(round(fppg + (oprk - 15.5) / 14.5 * math.sqrt(seas), 2), 0)))

# ----------------------------------------------------------------------------------------------------
# proc eyeball, pick 4 or 5 captains
# high efficieny = low $/fppg
# ----------------------------------------------------------------------------------------------------

eff = {}
for i in data_dict.keys():
    if data_dict[i][4] > 0:
        eff[i] = [round(data_dict[i][2] / data_dict[i][4])]
    else:
        eff[i] = [999]

eff_sorted = sorted(eff.items(), key = lambda x: x[1])
import collections
sorted_eff = collections.OrderedDict(eff_sorted)

for i in sorted_eff.keys():
	sorted_eff[i] = sorted_eff[i] + [data_dict[i][2]] + [data_dict[i][4]] + [data_dict[i][5]]

sorted_eff

# ----------------------------------------------------------------------------------------------------
# parse raw csv into digestible structure for algorithm
# ----------------------------------------------------------------------------------------------------

p_list = []

for i in data_dict:
	if (data_dict[i][4] != 0) and (data_dict[i][5] != 'O') and (data_dict[i][2] > 1000):
		p_list.append(i)

# ----------------------------------------------------------------------------------------------------
# optimization algorithm, retains top FPPG lineups that are within salary
# ----------------------------------------------------------------------------------------------------

def dancho_iter(dancho, stock):

	for capt in [dancho]:
		p_list_1 = p_list.copy()
		p_list_1.remove(capt)

		for util_1 in p_list_1:
			p_list_2 = p_list_1.copy()
			p_list_2.remove(util_1)

			for util_2 in p_list_2:
				p_list_3 = p_list_2.copy()
				p_list_3.remove(util_2)

				for util_3 in p_list_3:
					p_list_4 = p_list_3.copy()
					p_list_4.remove(util_3)

					for util_4 in p_list_4:
						p_list_5 = p_list_4.copy()
						p_list_5.remove(util_4)

						for util_5 in p_list_5:

							if not((data_dict[capt][3] == data_dict[util_1][3]) and
								(data_dict[capt][3] == data_dict[util_2][3]) and
								(data_dict[capt][3] == data_dict[util_3][3]) and
								(data_dict[capt][3] == data_dict[util_4][3]) and
								(data_dict[capt][3] == data_dict[util_5][3])):

								tot_sal = (data_dict[capt][2] * 1.5) + data_dict[util_1][2] + data_dict[util_2][2] + data_dict[util_3][2] + data_dict[util_4][2] + data_dict[util_5][2]


								if (tot_sal <= salary) and (tot_sal > min_sal):

									tot_fppg = (data_dict[capt][4] * 1.5) + data_dict[util_1][4] + data_dict[util_2][4] + data_dict[util_3][4] + data_dict[util_4][4] + data_dict[util_5][4]

									if len(lineups) < stock:

										if len(lineups) > 0:

											temp = [util_1, util_2, util_3, util_4, util_5]
											temp.sort()

											if (([capt] + temp) not in lineups_sorted) and (([capt] + temp) not in lineups_chopped):

												lineups[capt + ',' + util_1 + ',' + util_2 + ',' + util_3 + ',' + util_4 + ',' + util_5] = [tot_sal, tot_fppg]
												lineups_fppg.append(tot_fppg)
												temp = [util_1, util_2, util_3, util_4, util_5]
												temp.sort()
												lineups_sorted.append([capt] + temp)

										else:

											lineups[capt + ',' + util_1 + ',' + util_2 + ',' + util_3 + ',' + util_4 + ',' + util_5] = [tot_sal, tot_fppg]
											lineups_fppg.append(tot_fppg)
											temp = [util_1, util_2, util_3, util_4, util_5]
											temp.sort()
											lineups_sorted.append([capt] + temp)

									elif tot_fppg > min(lineups_fppg):

										temp = [util_1, util_2, util_3, util_4, util_5]
										temp.sort()

										if (([capt] + temp) not in lineups_sorted) and (([capt] + temp) not in lineups_chopped):

											chop_block = ''

											for i in lineups:

												if chop_block != '':

													if lineups[i][1] <= lineups[chop_block][1]:

														chop_block = i
												else:

													chop_block = i

											lineups_fppg.remove(lineups[chop_block][1])
											del lineups[chop_block]

											x = chop_block.split(',')
											y = x[0]
											x.remove(y)
											x.sort()
											lineups_sorted.remove([y] + x)

											if ([y] + x) not in lineups_chopped:
												lineups_chopped.append([y] + x)

											lineups[capt + ',' + util_1 + ',' + util_2 + ',' + util_3 + ',' + util_4 + ',' + util_5] = [tot_sal, tot_fppg]
											lineups_fppg.append(tot_fppg)
											lineups_sorted.append([capt] + temp)


danchos = {
	'Kawhi Leonard':5,
	'Paul George':5,
	'Gordon Hayward':5,
	'Jayson Tatum':5
}

#data_dict['Enes Kanter'][4] = 15
#data_dict['Enes Kanter'][5] = 'O'

master_lineups = {}

for i in danchos.keys():

	lineups = {}
	lineups_fppg = []
	lineups_sorted = []
	lineups_chopped = []

	dancho_iter(i, danchos[i])

	for j in lineups.keys():
		master_lineups[j] = lineups[j]

	print('COMPLETED: ' + i)

# ----------------------------------------------------------------------------------------------------
# prints lineups and arranges array for output
# ----------------------------------------------------------------------------------------------------

print('\n')
print('CPT,UTIL,UTIL,UTIL,UTIL,UTIL,Salary,FPPG')

lineups_final = []
for i in master_lineups:
	print(i + ',' + str(master_lineups[i][0]) + ',' + str(round(master_lineups[i][1], 2)))

	nm = i.split(',')
	lineups_final.append([data_dict[nm[0]][0], data_dict[nm[1]][1], data_dict[nm[2]][1], data_dict[nm[3]][1], data_dict[nm[4]][1], data_dict[nm[5]][1]])

lineups_final.insert(0, ['CPT', 'UTIL', 'UTIL', 'UTIL', 'UTIL', 'UTIL'])

print('\n')

# ----------------------------------------------------------------------------------------------------
# output csv to be uploaded
# ----------------------------------------------------------------------------------------------------

with open(str(DRAFT_GROUP_ID) + '_' + CONTEST_ID + '.csv', 'w', newline = '') as csv_file:
	writer = csv.writer(csv_file)
	writer.writerows(lineups_final)
csv_file.close()