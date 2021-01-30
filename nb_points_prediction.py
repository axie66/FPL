from FPL import FPL, PlayerStats
from sklearn.naive_bayes import GaussianNB
from pprint import pprint

def getForm(history, week, features, prev=3): # get stats for previous n weeks, inclusive
    prevWeeks = history[week-prev+1:week+1]
    data = [] 
    for f in features:
        if(f == 'opponent_team'):
            avgF = sum(FDR[w[f]] for w in prevWeeks)/prev
        else:
            avgF = sum(float(w[f]) for w in prevWeeks)/prev
        data.append(avgF)
    return data

FDR = {
    'Arsenal': 4, 
    'Aston Villa': 2, 
    'Bournemouth': 3, 
    'Brighton': 2, 
    'Burnley': 3, 
    'Chelsea': 4, 
    'Crystal Palace': 2, 
    'Everton': 2, 
    'Leicester': 4, 
    'Liverpool': 5, 
    'Man City': 5, 
    'Man Utd': 4, 
    'Newcastle': 2, 
    'Norwich': 2,
    'Sheffield Utd': 3, 
    'Southampton': 2, 
    'Spurs': 4, 
    'Watford': 2, 
    'West Ham': 2, 
    'Wolves': 3
}

def getRecs(fpl, week): # gets player recommendations for next week
    gameweek = week
    features = ['goals_scored', 'total_points', 'clean_sheets', 'ict_index', 'opponent_team']
    X = []
    y = []
    for player in fpl.players.values():
        if(player['status'] == 'u' or player['status'] == 'n'):
            continue
        if(len(player.history) < gameweek):
            continue
        if(player['minutes'] < gameweek*90*0.25):
            continue
        cumulative = [0, 0, 0, 0, 0]
        for week in range(2, gameweek-1):
            last = getForm(player.history, week, features, prev=3)
            X.append(last)
            y.append(player.history[week+1]['total_points'])

    clf = GaussianNB()
    clf.fit(X, y)

    recs = []
    for player in fpl.players.values():
        if(player['status'] == 'u' or player['status'] == 'n'):
            continue
        if(len(player.history) < gameweek):
            continue
        if(player['minutes'] < gameweek*90*0.25):
            continue    

        data = getForm(player.history, gameweek-1, features, prev=3)
        data[-1] = player.fixtures[0][3]
        pred = clf.predict([data])
        if(pred[0] > 4):
            recs.append((player, pred[0]))
    return recs