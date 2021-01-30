from cmu_112_graphics import *
from FPL import FPL
import urllib.request 

fpl = FPL()
#players = list(fpl.players.values())

'''for player in players:
    print(player.imageURL)
    fileName = player.imageURL.replace('https://platform-static-files.s3.amazonaws.com/premierleague/photos/players/110x140/p', '')
    try:
        urllib.request.urlretrieve(player.imageURL, f'playerImages/{fileName}')
    except:
        print(player.__dict__)
        print()'''

teams = list(fpl.teamCodes.keys())
for team in teams:
    fileName = 'teamImages/' + fpl.teamCodes[team] + '.png'
    url = f'https://premierleague-static-files.s3.amazonaws.com/premierleague/badges/t{team}.png'
    try:
        urllib.request.urlretrieve(url, fileName)
    except:
        print(fpl.teamCodes[team])