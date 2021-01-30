import requests
from FPL import FPL, PlayerStats
import json
from pprint import pprint
from copy import deepcopy

def makeTransfer(fpl, session, ID, picks, pIn, pOut):
    out = None
    for pick in picks:
        if(pick['element'] == pOut.id):
            out = pick
            break
    else:
        raise(Exception('pOut is not in your team!'))

    transferURL = 'https://fantasy.premierleague.com/api/transfers/'
    transfers = [{
        'element_in': pIn.id,
        'element_out': pOut.id,
        'purchase_price': int(pIn['value'] * 10),
        'selling_price': out['selling_price']}]
    payload = {
        'entry': ID,
        'event': fpl.lastGameweek+1,
        'freehit': False,
        "transfers": transfers,
        'wildcard': False,
    }

    transfer = session.post(transferURL, json=payload)
    return transfer

def makeSub(fpl, session, ID, oldPicks, p1, p2):
    picks = deepcopy(oldPicks)
    i1, i2 = None, None
    for i in range(len(picks)):
        pick = picks[i]
        if(pick['element'] == p1):
            i1 = i
        elif(pick['element'] == p2):
            i2 = i
        if(i1 != None and i2 != None):
            break
    else:
        raise(Exception("You can't sub players who aren't in your team!"))
    
    subURL = f'https://fantasy.premierleague.com/api/my-team/{ID}/'
    picks[i1]['position'], picks[i2]['position'] = picks[i2]['position'], picks[i1]['position']
    picks[i1]['is_captain'], picks[i2]['is_captain'] = picks[i2]['is_captain'], picks[i1]['is_captain']
    picks[i1]['is_vice_captain'], picks[i2]['is_vice_captain'] = picks[i2]['is_vice_captain'], picks[i1]['is_vice_captain']
    picks[i1], picks[i2] = picks[i2], picks[i1]
    starters, bench = picks[:11], picks[11:]

    newStarters = sorted(starters, key=lambda s: (fpl.players[s['element']]['element_type']-1)*100+s['position'])
    lineup = newStarters + bench
    newLineup = [{
    'element': p['element'],
    'position': i+1,
    'is_captain': p['is_captain'],
    'is_vice_captain': p['is_vice_captain']
    } for i, p in enumerate(lineup)]
    print('new lineup: ')
    pprint(newLineup)

    sub = session.post(subURL, json={'picks': newLineup})
    return sub
            
# 457 for 269