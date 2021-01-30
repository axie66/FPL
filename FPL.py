import requests
from bs4 import BeautifulSoup
from pprint import pprint
import _pickle as pickle
import datetime
import os
import re
import codecs
import json
import pafy
from unidecode import unidecode
#import nltk

class FPL(object):
    abbrevs = {
        'Arsenal': 'ARS', 
        'Aston Villa': 'AVL', 
        'Bournemouth': 'BOU', 
        'Brighton': 'BHA', 
        'Burnley': 'BUR', 
        'Chelsea': 'CHE', 
        'Crystal Palace': 'CRY', 
        'Everton': 'EVE', 
        'Leicester': 'LEI', 
        'Liverpool': 'LIV', 
        'Man City': 'MCI', 
        'Man Utd': 'MUN', 
        'Newcastle': 'NEW', 
        'Norwich': 'NOR', 
        'Sheffield Utd': 'SHU', 
        'Southampton': 'SOU', 
        'Spurs': 'TOT', 
        'Watford': 'WAT', 
        'West Ham': 'WHU', 
        'Wolves': 'WOL'
    }

    def __init__(self, useCache=True, restart=False):
        self.sesh = requests.session()
        rootURL = 'https://fantasy.premierleague.com/api/bootstrap-static/'
        res = self.sesh.get(rootURL)
        self.json = res.json()
        understatTeams = [s.replace('_', ' ') for s in UnderstatScraper.TEAMS]
        self.fplToUnderstatTeamNames = dict(zip(FPL.TEAMS, understatTeams))

        now = datetime.datetime.now()
        self.teams = self.json['teams']
        
        for i in range(38):
            event = self.json['events'][i]
            timeString = event['deadline_time'][:-1]
            deadline = datetime.datetime.fromisoformat(timeString)
            if(now - deadline < datetime.timedelta(0)):
                break
        self.lastGameweek = i
        self.elements = self.json['elements'] # player data stored under key elements
        self.elementStats = self.json['element_stats']
        self.elementTypes = self.json['element_types']
        self.totalPlayers = self.json['total_players']
        self.codeToTeam = self.getTeamCodes()
        self.numToTeam = {n+1: self.TEAMS[n] for n in range(20)}
        self.players = dict()
        
        if(useCache):
            self.players = pickle.load(open('playerData.p', 'rb'))
        
        else:
            if(restart):
                open('playerData.p','w').close()


            if(os.stat('playerData.p').st_size == 0):
                self.getAllData()
            else:
                data = pickle.load(open('playerData.p', 'rb'))
                deltaT = datetime.timedelta(days=0.5)
                if(now - data['last_modified'] < deltaT):
                    self.players = data
                else:
                    self.getAllData()
        self.players.pop('last_modified')

    def getAllData(self):
        self.getPlayers()
        self.getHistoryAndFixtures()
        self.getUnderstatData()
        self.getHighlights()
        self.players['last_modified'] = datetime.datetime.today()
        pickle.dump(self.players, open('playerData.p', 'wb'))

    posDict = {
        1: 'GKP',
        2: 'DEF',
        3: 'MID',
        4: 'FWD'
    }

    def getGameHist(self, player):
        player.gameHist = []
        for game in player.history:
            if(game['was_home']):
                selfScore, otherScore = game['team_h_score'], game['team_a_score']
                home, away = player.team, game['opponent_team']
            else:
                selfScore, otherScore = game['team_a_score'], game['team_h_score']
                home, away = game['opponent_team'], player.team
            res = ''
            if(selfScore != None):
                if(selfScore > otherScore): res = 'W'
                elif(selfScore < otherScore): res = 'L'
                else: res = 'D'
            else:
                game['team_h_score'], game['team_a_score'] = '', ''
            player.gameHist.append((home, game['team_h_score'], 
                away, game['team_a_score'], res))

    def getPlayers(self):
        for player in self.elements:
            team = self.codeToTeam[player['team_code']]
            p = PlayerStats(player['web_name'], team)
            p.data['name'] = player['web_name']
            p.data['team'] = team
            p.data['element_type'] = player['element_type']
            p.data['posClass'] = FPL.posDict[player['element_type']]

            p.data['firstName'] = player['first_name']
            p.data['lastName'] = player['second_name']
            p.data['goals'] = player['goals_scored']
            p.data['assists'] = player['assists']
            p.data['minutes'] = player['minutes']
            p.data['cs'] = player['clean_sheets']
            p.data['saves'] = player['saves']
            p.data['ownGoals'] = player['own_goals']
            p.data['pensMissed'] = player['penalties_missed']
            p.data['pensSaved'] = player['penalties_saved']
            p.data['yellows'] = player['yellow_cards']
            p.data['reds'] = player['red_cards']
            p.data['conceded'] = player['goals_conceded']

            p.data['points'] = player['total_points']
            p.data['form'] = float(player['form'])

            p.data['bonus'] = player['bonus']
            p.data['bps'] = player['bps']
            p.data['creativity'] = float(player['creativity'])
            p.data['influence'] = float(player['influence'])
            p.data['threat'] = float(player['threat'])
            p.data['ict'] = float(player['ict_index'])
            p.data['dreamTeam'] = player['in_dreamteam']
            p.data['status'] = player['status']

            code = player['code']
            p.imageURL = 'https://platform-static-files.s3.amazonaws.com/' + \
                         'premierleague/photos/players/110x140/' + \
                         f'p{code}.png'

            p.photo = str(player['code']) + '.png'
            
            p.data['value'] = player['now_cost'] / 10
            p.data['popularity'] = float(player['selected_by_percent'])
            p.data['costChange'] = player['cost_change_start']
            p.data['transfersIn'] = player['transfers_in']
            p.data['transfersOut'] = player['transfers_out']

            p.data['probPlayingNextRound'] = player['chance_of_playing_next_round']
            p.data['probPlayingThisRound'] = player['chance_of_playing_this_round']

            p.data['ppm'] = round(p.data['points']/p.data['value'], 1)
            p.data['p90'] = round(p.data['points'] * 90/p.data['minutes'], 1) if p.data['minutes'] >= 360 else 0
            p.id = player['id']

            self.players[player['id']] = p

    def getHistoryAndFixtures(self):
        for ID in self.players:
            p = self.players[ID]
            print(f"{p.data['name']} - {ID}")
            url = f'https://fantasy.premierleague.com/api/element-summary/{ID}/'
            res = self.sesh.get(url)
            json = res.json()
            p.history = json['history']
            for element in p.history:
                element['ict_index'] = float(element['ict_index'])
                element['value'] = element['value']/10
                element['opponent_team'] = self.numToTeam[element['opponent_team']]
            self.getGameHist(p)
            p.fixtures = []
            for fixture in json['fixtures']:
                week = fixture['event'] if fixture['event'] else 'DGW'
                opp = self.numToTeam[fixture['team_a']] if fixture['is_home'] else \
                    self.numToTeam[fixture['team_h']]
                home = 'H' if fixture['is_home'] else 'A'
                diff = fixture['difficulty']
                isoTime = fixture['kickoff_time']
                if(isoTime): time = datetime.datetime.fromisoformat(isoTime[:-1])
                else: time = 'TBD'
                p.fixtures.append((week, opp, home, diff, time))
            

    # returns dictionary of codes and their corresponding teams
    def getTeamCodes(self):
        teamCodes = {
            team['code']: team['name'] 
            for team in self.teams
        }
        return teamCodes

    TEAMS = ['Arsenal', 'Aston Villa', 'Bournemouth', 'Brighton', 
    'Burnley', 'Chelsea', 'Crystal Palace', 'Everton', 'Leicester', 
    'Liverpool', 'Man City', 'Man Utd', 'Newcastle', 'Norwich', 
    'Sheffield Utd', 'Southampton', 'Spurs', 'Watford', 'West Ham', 'Wolves']
    
    def getUnderstatData(self):
        self.understat = UnderstatScraper()
        understatPlayers = self.understat.players
        for ID in self.players:
            player = self.players[ID]
            for name in understatPlayers:
                data = understatPlayers[name]
                understatTeam = data['team_title']
                if(player.name.lower() in name.lower() and
                   self.fplToUnderstatTeamNames[player.team] == understatTeam):
                    player.data['xG'] = float(data['xG'])
                    player.data['xA'] = float(data['xA'])
                    player.data['shots'] = int(data['shots'])
                    player.data['keyPasses'] = int(data['key_passes'])
                    player.data['nonPenaltyGoals'] = float(data['npg'])
                    player.data['npxG'] = float(data['npxG'])
                    player.data['xGChain'] = float(data['xGChain'])
                    player.data['xGBuildup'] = float(data['xGBuildup'])
                    if(player.data['minutes'] >= 360):
                        player.data['xG90'] = player.data['xG']/player.data['minutes'] * 90
                        player.data['xA90'] = player.data['xA']/player.data['minutes'] * 90
                    else:
                        player.data['xG90'] = 0
                        player.data['xA90'] = 0
                    break
            else:
                print(player, self.fplToUnderstatTeamNames[player.team])
                player.data['xG'] = 0
                player.data['xA'] = 0
                player.data['shots'] = 0
                player.data['keyPasses'] = 0
                player.data['nonPenaltyGoals'] = 0
                player.data['npxG'] = 0
                player.data['xGChain'] = 0
                player.data['xGBuildup'] = 0
                player.data['xG90'] = 0
                player.data['xA90'] = 0

    PLAYLIST_URLS = [
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1gso9MlV9HAP-cvdb-8cpfV',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1iuVaPWK528V7tbxiPVvbGH',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1gRgV694mK1U_GFRldkN7-0',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1hMO87Fnlase5_VZLF1PZVZ',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1iDp34jscqQ8KOcVKFGVFtT',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1gELBVHPWnEmwL281XTIblL',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1jR9s_ir65FlCkUU3-EO82E',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1h8DCEaHnxb4FSsMqhdbyag',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1jPd94WsadfNlaJc3poR0vn',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1gN4iL_D4zXeko7pgVa9LHK',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1hsGAw9Ne8aWAqUvvAsM1YF',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1jCg6fGPOt5BZPWlbUiBSN9',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1iwKPIo3NJZ-fuN3EhVrOt2',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1i8NlCFzueAzL7hREtbOwHH',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1g3h-3qrJaDVYQn4JfGlIGH'
    ]

    def getHighlights(self):
        for i, purl in enumerate(self.PLAYLIST_URLS):
            playlist = pafy.get_playlist(purl)
            for item in playlist['items']:
                self.isHighlight(item, i+1)

    def isHighlight(self, video, week):
        meta = video['playlist_meta']
        title = unidecode(meta['title'])
        if('HIGHLIGHTS' in title):
            return
        for player in self.players.values():
            if unidecode(player.name) in title:
                data = {
                        'duration': meta['duration'],
                        'thumbnail': meta['thumbnail'],
                        'title': meta['title'],
                        'views': meta['views']
                }
                if(week in player.highlights):
                    player.highlights[week].append((data, video['pafy']))
                else:
                    player.highlights[week] = [(data, video['pafy'])]

class PlayerStats(object):
    def __init__(self, name, team):
        # general info
        self.name = name
        self.team = team
        self.id = None
        self.history = None
        self.imageURL = None

        # dictionary containing all data below
        self.data = dict()
        self.highlights = dict()
        '''
        fullName = None
        age = None
        position = None

        # general stats
        goals = None
        assists = None
        minutes = None
        cleanSheets = None
        saves = None
        ownGoals = None
        pensMissed = None
        pensSaved = None
        yellowCards = None
        redCards = None
        conceded = None
        
        # advanced stats (i.e. I can't get it straight from the fpl api)
        gamesPlayed = None
        playPercent = None
        xG = None # expected goals - taken from understat.com
        xA = None # expected assists - taken from understat.com

        # points
        points = None # current point total
        form = None # average points from past 5 gameweeks
        # following stats can't be gathered directly from boostrap static endpoint
        weekHistory = None # list of week-by-week stats
        ppm = None # points per million pounds of value
        p90 = None # points per million per 90 minutes played

        # fpl stats
        bonus = None # total bonus points earned
        bps = None # total points earned in bps system
        creativity = None 
        influence = None # idk what creativity, influence, threat, or ict are
        threat = None    # but fpl apparently does so i'm putting 'em here
        ict = None
        dreamTeam = False # whether the player is in FPL's Dream Team; kinda useless tbh
        status = None # whether the player is a (active), i (injured), etc

        # economics
        value = None # current price
        popularity = None # % owned among all FPL players
        priceChangeProb = None # probability of player's price changing
        costChangeStart = None # change in player's price since start of season
        transfersIn = None
        transfersOut = None
        
        # playing time/fixtures
        nextFixtures = None # fixtures until end of season
        nailedness = None # how guaranteed player is to play
        competitors = None # players in same position on same team
        probPlayingNextRound = None # probabiltiy of player playing next week
        probPlayingThisRound = None # probability of player playing this week
        '''
    
    def __repr__(self):
        return f"<{self.data['firstName']} {self.data['lastName']} of {self.team}>"

    def __eq__(self, other):
        if(not isinstance(other, PlayerStats)): return False
        else: (self.id == other.id)
    
    def __hash__(self):
        return hash((self.name, self.team, self.id))

    def __getitem__(self, index):
        return self.data.get(index, None)

'''
class HighlightFinder(object):
    PLAYLIST_URLS = [
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1gso9MlV9HAP-cvdb-8cpfV',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1iuVaPWK528V7tbxiPVvbGH',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1gRgV694mK1U_GFRldkN7-0',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1hMO87Fnlase5_VZLF1PZVZ',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1iDp34jscqQ8KOcVKFGVFtT',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1gELBVHPWnEmwL281XTIblL',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1jR9s_ir65FlCkUU3-EO82E',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1h8DCEaHnxb4FSsMqhdbyag',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1jPd94WsadfNlaJc3poR0vn',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1gN4iL_D4zXeko7pgVa9LHK',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1hsGAw9Ne8aWAqUvvAsM1YF',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1jCg6fGPOt5BZPWlbUiBSN9',
        'https://www.youtube.com/playlist?list=PLXEMPXZ3PY1iwKPIo3NJZ-fuN3EhVrOt2'
    ]

    def __init__(self, fpl):
        self.fpl = fpl
        

    def getHighlights(self):
        for i, purl in enumerate(HighlightFinder.PLAYLIST_URLS):
            playlist = pafy.get_playlist(purl)
            for item in plist['items']:
                if(self.isHighlight(item)):
                    self.highlights[i + 1].append()

    def highlight(self, video):
        data = video['playlist_meta']
        title = data['title']
        if('HIGHLIGHTS' in title):
            return False
        for player in self.playerList:
            if player in title:
'''     


class UnderstatScraper(object):
    def __init__(self, teams=None):
        self.session  = requests.session()
        self.teams = teams if teams else UnderstatScraper.TEAMS
        self.players = dict()
        self.getPlayers()
    
    PATTERN = r"{}\s+=\s+JSON.parse\(\'(.*?)\'\)"
    
    TEAMS = ['Arsenal', 
             'Aston_Villa', 
             'Bournemouth',
             'Brighton',
             'Burnley',
             'Chelsea',
             'Crystal_Palace',
             'Everton',
             'Leicester',
             'Liverpool',
             'Manchester_City',
             'Manchester_United',
             'Newcastle_United',
             'Norwich',
             'Sheffield_United',
             'Southampton',
             'Tottenham',
             'Watford',
             'West_Ham',
             'Wolverhampton_Wanderers']

    def getPlayers(self):
        for team in self.teams:
            data = self.getTeam(team)
            for player in data:
                self.players[player['player_name']] = player

    def getTeam(self, team):
        url = f'https://understat.com/team/{team}/2019'
        return self.get_data(url, 'playersData')

    # The following code is taken from: 
    # https://github.com/amosbastian/understat/blob/master/understat/ by Amos Bastian
    @staticmethod
    def find_match(scripts, pattern):
        """Returns the first match found in the given scripts."""

        for script in scripts:
            match = re.search(pattern, script.string)
            if match:
                break

        return match

    @staticmethod
    def decode_data(match):
        """Returns data in the match's first group decoded to JSON."""

        byte_data = codecs.escape_decode(match.group(1))
        json_data = json.loads(byte_data[0].decode("utf-8"))

        return json_data

    def get_data(self, url, data_type):
        """Returns data from the given URL of the given data type."""

        html = self.session.get(url).text
        soup = BeautifulSoup(html, "html5lib")
        scripts = soup.find_all("script")

        pattern = re.compile(UnderstatScraper.PATTERN.format(data_type))
        match = UnderstatScraper.find_match(scripts, pattern)
        data = UnderstatScraper.decode_data(match)

        return data

# used as test function
def main():
    fpl = FPL(useCache=False, restart=True)
    #fpl = FPL()
    '''index = 0
    for e in fpl.elements:
        if e['photo'] == '174597.jpg':
            break
        index += 1
    pprint(fpl.elements[index])'''
    print(fpl.players[210])

if(__name__ == '__main__'):
    main()
