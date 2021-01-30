###################################################
# model.py
# Alex Xie
###################################################

import os
import torch
import torch.nn as nn
import requests
import pickle
from pprint import pprint

MAIN = 'https://fantasy.premierleague.com/api/bootstrap-static/'
PLAYER = 'https://fantasy.premierleague.com/api/element-summary/'#{ID}/
UNDERSTAT_TEAM = 'https://understat.com/team/' #{team}/2019
CACHE = 'cache.p'

class FPLData(object):
    session = requests.session()


    def __init__(self, restart=False):
        self.allData = self.session.get(MAIN).json()
        if(os.stat(CACHE).st_size != 0 and not restart):
            del self.allData['elements']
            del self.allData['teams']
            self.getCache()
        else:
            self.playerData = self.allData.pop('elements')
            self.teamData = self.allData.pop('teams')
            self.id2player = dict()
            self.getData() # populates playerData, id2player, teamData
            self.makeCache()

    def getCache(self):
        self.playerData, self.id2player, self.teamData = pickle.load(open(CACHE, 'rb'))
        
    def makeCache(self):
        cached = [self.playerData, self.id2player, self.teamData]
        pickle.dump(cached, open(CACHE, 'wb'))
    
    def getData(self):
        total = len(self.playerData)
        counter = 1
        for elem in self.playerData:
            elemID = elem['id']
            self.id2player[elemID] = elem['web_name']
            
            teamIndex = elem['team'] - 1
            roster = self.teamData[teamIndex].get('roster', [])
            roster.append(elemID)
            self.teamData[teamIndex]['roster'] = roster

            print(f'({counter}/{total}) Getting data for: {elem["web_name"]}')
            res = self.session.get(PLAYER + f'{elemID}/').json()
            elem['history'] = res['history']
            elem['fixtures'] = res['fixtures']

            counter+=1

    def getGameweek(self, gw):
        assert(1 <= gw <= 38)
        performances = []
        for data in self.playerData:
            history = data['history']
            firstWeek = history[0]['round']
            lastWeek = history[-1]['round']

            if(gw < firstWeek or gw > lastWeek):
                continue
            
            guess = gw - firstWeek

            if(guess < len(history) and history[guess]['round'] == gw):
                performances.append(history[guess])
            else:
                # we guessed wrong, re-guess with offset
                for i in [-2, -1, 1, 2]: 
                    if(0 <= guess+i < len(history) and 
                       history[guess+i]['round'] == gw):
                       performances.append(history[guess+i])
                       break
                else:
                    self.printPlayer(data['id'])
        return performances

    def printPlayer(self, playerID):
        for data in self.playerData:
            if data['id'] == playerID:
                first = data['first_name']
                last = data['second_name']
                teamIndex = data['team']-1
                team = self.teamData[teamIndex]['name']
                print(f'{first} {last} of {team} ({playerID})')
                return data

class Model(nn.Module):
    def __init__(self):
        super(Model, self).__init__()
        self.relu = nn.ReLU()
        # < form, is_home, Gp90, Ap90, team, opponent, GAp90, xGp90, xAp90 >
        self.fc1 = nn.Linear(9, 32)
        self.fc2 = nn.Linear(32, 64)
        self.fc3 = nn.Linear(64, 1)
    
    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        x = self.fc3(x)
        return x

def train():
    fpl = FPLData()

    data = []
    targets = []

    for gw in range(6, 20):
        performances = fpl.getGameweek(gw)
        for player in performances:
            if(player['minutes'] == 0): 
                continue
            targets.append(player['total_points'])
            
            form = 0
            home = player['was_home']
            gp90 = 0 # past 5 games
            ap90 = 0 # past 5 games

            for prior in range(gw - 5, gw):
                pass






class GKPModel(nn.Module):
    pass

class DEFModel(nn.Module):
    pass

class MIDModel(nn.Module):
    pass

class FWDModel(nn.Module):
    pass

