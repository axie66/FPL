import numpy as np
import pandas as pd

###########################################################################
# Globals
###########################################################################

NUM_GK = 2
NUM_DEF = 5
NUM_MID = 5
NUM_FWD = 3

BUDGET = 100

FPL_DATA = '/Users/axie/projects/FPL/data/Fantasy-Premier-League/data/'

PLAYER_DATA_19_20 = FPL_DATA + '2019-20/players_raw.csv'
PLAYER_DATA_20_21 = FPL_DATA + '2020-21/players_raw.csv'

###########################################################################
# Short helper functions
###########################################################################


###########################################################################
# Long helper functions
###########################################################################

def parsePlayerDataCSV(path):
    data = pd.read_csv(path)
    return (data['web_name'].values, data['now_cost'].values, 
            data['total_points'].values, data['element_type'].values)

def makeTableau(costs, points, positions):
    numPlayers = names.size
    tableau = np.zeros((6, numPlayers+2), dtype=int)
    tableau[0][:numPlayers] = costs
    tableau[0][-1] = 1000
    np.negative(points, out=tableau[5][:numPlayers])
    tableau[5][-2] = 1
    for i in range(numPlayers):
        position = positions[i]
        tableau[position][i] = 1
    tableau[1:-1,-1] = (NUM_GK, NUM_DEF, NUM_MID, NUM_FWD)
    return tableau


###########################################################################
# Main functions
###########################################################################

def simplex(data):
    names, costs, points, positions = parsePlayerDataCSV(PLAYER_DATA_20_21)
    tableau = makeTableau(costs, points, positions)
    
