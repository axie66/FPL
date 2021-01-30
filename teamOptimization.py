from FPL import FPL, PlayerStats
from pprint import pprint

class FPLOptimizer(object):
    def __init__(self, optimized, fpl):
        self.optimized = optimized
        self.minutesThreshold = 0.6
        self.fpl = fpl
        self.setUpPlayers()
        
    def setUpPlayers(self):
        self.players = sorted(self.fpl.players.values(), key=lambda p: p[self.optimized]/p['value'], reverse=True)
        self.players = [player for player in self.players if player['minutes'] > self.fpl.lastGameweek * 90 * self.minutesThreshold]
        self.cheapest = sorted(self.fpl.players.values(), key=lambda p: p['value'])
        
        self.replacements = None

    @staticmethod
    def getFormation(n):
        d, m, f = n//100, n//10%10, n%10
        return [f, m, d, 1]

    posDict = {
        'FWD': 0,
        'MID': 1,
        'DEF': 2,
        'GKP': 3
    }

    totalTeam = [3, 5, 5, 2]

    def getBaseTeam(self, formation):
        team = []
        teamLen = 0
        while len(team) < 11:
            for player in self.players:
                pos = self.posDict[player['posClass']]
                if(formation[pos] != 0):
                    team.append(player)
                    formation[pos] -= 1
        return team

    def getBench(self, formation):
        benchReq = [self.totalTeam[i] - formation[i] for i in range(4)]
        bench = []
        while len(bench) < 4:
            for player in self.cheapest:
                pos = self.posDict[player['posClass']]
                if(benchReq[pos] != 0):
                    bench.append(player)
                    benchReq[pos] -= 1
        return bench

    def getReplacements(self, teamSet, surplus):
        self.replacements = {player: [player] for player in teamSet}
        for player in teamSet:
            maxValue = player['value'] + surplus
            for p in self.players:
                if(p not in teamSet and p['value'] < maxValue and p[self.optimized] > player[self.optimized]
                and p['posClass'] == player['posClass']):
                    if(p['status'] == 'a'):
                        self.replacements[player].append(p)
            repls = self.replacements[player]
            if(len(repls) > 6):
                self.replacements[player] = self.replacements[player][:6]

    @staticmethod
    def numPermutations(replacements):
        perm = 1
        for L in replacements.values():
            perm *= len(L)
        return perm

    def getBestPossibleTeam(self, playerList, replacements, surplus):
        possibleTeams = set()
        def getPossibleTeams(partialTeam, playersLeft, surplus):
            if(len(playersLeft) == 0):
                team = Team(partialTeam, self.optimized)
                if(team not in possibleTeams):
                    possibleTeams.add(team)
            else:
                currentPlayer = playersLeft[0]
                for player in replacements[currentPlayer]:
                    if(player in partialTeam): continue
                    playerTeam = player.team
                    count = 0
                    for p in partialTeam:
                        if(p.team == playerTeam):
                            count += 1
                    if(count > 2): continue
                    extraCost = player['value'] - currentPlayer['value']
                    newSurplus = surplus - extraCost
                    if(newSurplus < 0): continue
                    newTeam = partialTeam + [player]
                    getPossibleTeams(newTeam, playersLeft[1:], newSurplus)

        getPossibleTeams([], playerList, surplus)
        teamList = list(possibleTeams)    
        #sortedTeamList = sorted(teamList, key=lambda t:t.points)
        bestTeam = max(teamList, key=lambda t: t.optimizable) if teamList else None
        return bestTeam

    def getOptimalTeam(self, formation):
        baseTeam = self.getBaseTeam(self.getFormation(formation))
        bench = self.getBench(self.getFormation(formation))

        baseTeamValue = sum(player['value'] for player in baseTeam)
        benchValue = sum(player['value'] for player in bench)
        surplus = 100 - baseTeamValue - benchValue
        teamSet = set(baseTeam)
        self.getReplacements(teamSet, surplus)
        pprint(self.replacements)
        print(self.numPermutations(self.replacements), 'permutations')
        #pprint(replacements)
        bestTeam = self.getBestPossibleTeam(baseTeam, self.replacements, surplus)
        if(not bestTeam):
            return
        remaining = 100 - bestTeam.value - sum(p['value'] for p in bench)

        teamDict = dict()
        fullTeams = set()
        for player in bestTeam.players:
            if(player.team in teamDict): teamDict[player.team] += 1
            else: teamDict[player.team] = 1

        for team in teamDict:
            if(teamDict[team] == 3):
                fullTeams.add(team)
        
        benchSet = set(bench)
        for i in range(len(bench)):
            player = bench[i]
            if(player.team in fullTeams):
                bench[i] = self.replaceWithCheapest(player, surplus, benchSet)
        
        return (bestTeam, bench)

    def replaceWithCheapest(self, player, surplus, benchSet):
        maxValue = player['value'] + surplus
        for p in self.cheapest:
            if(p['posClass'] == player['posClass'] and p != player and p not in benchSet):
                return p

class Team(object):
    def __init__(self, players, optimized):
        self.players = players
        self.optimizable = sum(player[optimized] for player in self.players)
        self.value = sum(player['value'] for player in self.players)
        self.id = sum(player.id for player in self.players)
        self.hashables = (self.id, self.optimizable, self.value)
    def __hash__(self):
        return hash(self.hashables)
    def __repr__(self):
        return f'<{self.hashables[1]} for {self.hashables[2]} mil>'

formationList = [352, 343, 451, 442, 433, 541, 532, 523]
bestTeams = []
fpl = FPL()
opt = FPLOptimizer('points', fpl)

#formation = 451

#baseTeam = getBaseTeam(getFormation(formation))
#bench = getBench(getFormation(formation))

'''for formation in formationList:
    print(f'Trying {formation}...', end='')
    best = getOptimalTeam(formation)
    bestTeams.append(best)
    tv = sum(p['value'] for p in best[0]) + sum(p['value'] for p in best[1])
    print(f'Done! Total Team Value: {tv}, Optimal {optimized}: {sum(p[optimized] for p in best[0])}')

starters = [team[0] for team in bestTeams]
benches = [team[1] for team in bestTeams]'''


'''
Trying 343...114048
Done! Total Team Value: 99.79999999999998, Points: 755
Trying 451...5417280
Done! Total Team Value: 99.8, Points: 723
Trying 442...142560
Done! Total Team Value: 99.19999999999999, Points: 744
Trying 433...115200
Done! Total Team Value: 99.6, Points: 751
Trying 541...1425600
Done! Total Team Value: 98.9, Points: 722
Trying 532...144000
Done! Total Team Value: 99.30000000000001, Points: 742
Trying 523...114400
Done! Total Team Value: 99.30000000000001, Points: 745
'''