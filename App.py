#####################################################
# App.py
# 
# Written by Alex Xie (alexx)
#####################################################

# cmu_112_graphics module taken from CMU 15-112 course notes at 
# https://www.cs.cmu.edu/~112/notes/notes-animations-part2.html
from cmu_112_graphics import *
from tkinter import *
from FPL import FPL, PlayerStats
import PIL
from PIL.ImageEnhance import Brightness
import requests
from pprint import pprint
import os
import _pickle as pickle
import cv2
import datetime
import numpy as np
from teamOptimization import FPLOptimizer
from utils import makeTransfer, makeSub
from nb_points_prediction import getRecs
from unidecode import unidecode
import webbrowser

def runFPLApp():
    FPLApp(width=1000, height = 700)

class FPLApp(ModalApp):
    def appStarted(self):
        self.fpl = FPL()
        self.timerDelay = 1000
        self.bgColor = self.rgbString(12, 0, 50)
        self.loggedInSession = None
        self.userTeam = None
        self.publicTeamInfo = None
        self.playerImages = dict()
        # player images taken from https://fantasy.premierleague.com 
        # property of the Premier League and the Professional Player's Association
        self.playerImages = pickle.load(open('playerImages.p', 'rb'))
        
        # team images taken from https://premierleague.com 
        # property of the Premier League and their respective clubs
        self.teamImages = pickle.load(open('teamImages.p', 'rb'))

        self.intro = IntroScreen()
        self.stats = StatsMode()
        self.login = LoginScreen()
        self.team = TeamSelectionScreen()
        self.ai = AITeamPicker()
        self.recs = PlayerRecs()
        self.setActiveMode(self.intro)
        
        self.playerMode = None
        self.lastPage = None

    @staticmethod
    def rgbString(red, green, blue):
        return "#%02x%02x%02x" % (red, green, blue)

class IntroScreen(Mode):
    def appStarted(self):
        global root
        root = self._theRoot
        # image created by Jacob Lee, from http://www.jacoblee.co.uk/
        self.pic = self.loadImage('http://www.jacoblee.co.uk/imgs/galleryThumbs/PL-thumb-logo15.gif')
        self.pic = self.pic.convert('RGBA')
        self.pic = Brightness(self.pic).enhance(200)

    def keyPressed(self, event):
        if(event.key == 'Space'):
            self.app.setActiveMode(self.app.login)

    def redrawAll(self, canvas):
        canvas.create_rectangle(0, 0, self.width, self.height,
            fill=self.app.bgColor)
        canvas.create_image(self.width // 4, self.height // 2,
            image=ImageTk.PhotoImage(self.pic))
        canvas.create_text(self.width//2, self.height/3,
            anchor='w', text='FPyL', 
            font=f"Futura {self.width//6} bold", fill='white')
        canvas.create_text(self.width*8.1/9, self.height*4/7,
            anchor='ne', text='A Fantasy Premier\nLeague Helper App',
            font=f'Futura {self.width//30} bold', fill='white', justify=RIGHT)
        
        canvas.create_text(self.width*8.1/9, self.height*6/7,
            anchor='ne', text='By Alex Xie for 15-112',
            font=f'Futura {self.width//40} bold', fill='white', justify=RIGHT)

class TextBox(object):
    def __init__(self, x, y, w, h, font):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.font = font
        self.fontSize = int(font.split(' ')[1])
        self.entering = False
        self.failed = False
        self.text = ''
    
    def draw(self, canvas):
        if(self.entering):
            color = 'yellow'
        elif(self.failed):
            color = 'red'
        else:
            color = 'white'
        canvas.create_rectangle(self.x - self.w/2, self.y - self.h/2, 
            self.x + self.w/2, self.y + self.h/2, fill=color, width=5)
        canvas.create_text(self.x - self.w/2 + self.fontSize/2, self.y, anchor='w', text=self.text, 
            font=self.font)

    def wasClicked(self, event):
        return (abs(self.x - event.x) <= self.w/2 and abs(self.y - event.y) <= self.h/2)

class LoginScreen(Mode):
    def appStarted(self):
        border = self.width // 8

        font = f'Monaco {self.width//50} bold'
        t1y = border * 1.7
        self.emailBox = (border * 3.5, t1y - border / 4, 
            self.width - 2 * border, t1y + border / 4)
        self.enteringEmail = False

        t2y = border * 2.7
        self.passBox = (border * 3.5, t2y - border / 4, 
            self.width - 2 * border, t2y + border / 4)
        self.enteringPass = False

        self.email = ''       #'fpltest123456@gmail.com'
        self.password = ''    #'cherryfunk14'
        
        y4 = border * 4.7
        self.entry = Button(self.width/2, y4, border, border/2, 'Log In!', 
            f'Monaco {self.width//50} bold')

        self.failed = False

        self.fplButton = Button(self.width/2, border*3.7, border*4, border/2, 
            "Don't have a Fantasy account? Make one!", f'Monaco {self.width//50} bold')

        print()
        print('Use the following credentials for testing purposes:')
        print('Username: fpltest123456@gmail.com')
        print('Password: cherryfunk14')
        print()

    def mousePressed(self, event):
        if(self.inBounds(event.x, event.y, self.emailBox)):
           self.enteringEmail = True
           self.enteringPass = False
        elif(self.inBounds(event.x, event.y, self.passBox)):
            self.enteringPass = True
            self.enteringEmail = False
        elif(self.fplButton.wasClicked(event)):
            webbrowser.open_new('https://fantasy.premierleague.com/')
        elif(self.entry.wasClicked(event)):
            self.login()
        else:
            self.enteringPass = self.enteringEmail = self.enteringID = False

    @staticmethod
    def inBounds(x, y, bounds):
        if(bounds[0] < x < bounds[2] and
           bounds[1] < y < bounds[3]):
           return True
        return False

    def login(self):
        if(self.password == '' or self.email == ''): 
            self.failed = True
            return
        session = requests.session()
        url = 'https://users.premierleague.com/accounts/login/'
        data = {
            'password': self.password,
            'login': self.email,
            'redirect_uri': 'https://fantasy.premierleague.com/a/login',
            'app': 'plfpl-web'
        }
        session.post(url, data=data)
        selfURL = 'https://fantasy.premierleague.com/api/me'
        res = session.get(selfURL).json()
        print(res)
        if(not res['player']):
            self.failed = True
        else:
            self.app.id = res['player']['entry']
            self.app.userName = [res['player']['first_name'], res['player']['last_name']]
            self.app.loggedInSession = session

            teamURL = f'https://fantasy.premierleague.com/api/my-team/{self.app.id}'
            self.app.userTeam = session.get(teamURL).json()
            publicTeamInfoURL = f'https://fantasy.premierleague.com/api/entry/{self.app.id}/'
            self.app.publicTeamInfo = session.get(publicTeamInfoURL).json()

            self.app.setActiveMode(self.app.team)

    def keyPressed(self, event):
        if(event.key == 'Enter'):
            self.login()
        if(self.enteringEmail):
            if(event.key == 'Delete'):
                self.email = self.email[:-1]
            elif(len(event.key) == 1):
                self.email += event.key
        elif(self.enteringPass):
            if(event.key == 'Delete'):
                self.password = self.password[:-1]
            elif(len(event.key) == 1):
                self.password += event.key
        elif(event.key == 'a'):
            self.email = 'fpltest123456@gmail.com'
            self.password = 'cherryfunk14'
                
    def redrawAll(self, canvas):
        canvas.create_rectangle(0, 0, self.width, self.height, 
            fill=self.app.bgColor)
        border = self.width // 8
        canvas.create_text(self.width // 2, border * 0.2, anchor='n',
            text='Sign In', font=f'Futura {self.width//15} bold', fill='white')
        
        t1y = border * 1.7
        fill = 'yellow' if self.enteringEmail else 'red' if self.failed else 'white'
        canvas.create_rectangle(self.emailBox, width=5, fill=fill)
        canvas.create_text(border * 2, t1y, anchor='w',
            text='   Email', font=f'Monaco {self.width//30} bold', fill='white')
        canvas.create_text(border * 3.6, t1y, anchor='w',
            text=self.email, font=f'Monaco {self.width//50}')
        
        t2y = border * 2.7
        fill = 'yellow' if self.enteringPass else 'red' if self.failed else 'white'
        canvas.create_rectangle(self.passBox, width=5, fill=fill)
        canvas.create_text(border * 2, t2y, anchor='w',
            text='Password', font=f'Monaco {self.width//30} bold', fill='white')
        canvas.create_text(border * 3.6, t2y, anchor='w',
            text=len(self.password)*'•', font=f'Monaco {self.width//50}')

        self.fplButton.draw(canvas)

        self.entry.draw(canvas)

class TeamSelectionScreen(Mode):
    def appStarted(self):
        self.sidebar = 300
        self.fieldWidth = self.width - self.sidebar
        self.fieldHeight = self.height * 3/4
        self.topBorder = self.fieldWidth / 6
        self.horizBorder = self.fieldWidth / 10
        self.field = (
            (self.horizBorder * 1.7, self.topBorder),
            (self.fieldWidth - self.horizBorder * 1.7, self.topBorder),
            (self.fieldWidth - self.horizBorder, self.topBorder + self.fieldHeight),
            (self.horizBorder, self.topBorder + self.fieldHeight)
        )
        self.players = self.app.fpl.players
        self.privateInfo = self.app.userTeam
        self.publicInfo = self.app.publicTeamInfo
        self.playerImages = self.app.playerImages
        self.picks = self.privateInfo['picks']
        self.moneyData = self.privateInfo['transfers']

        self.selected = []
        self.getTeam()

        self.dragged = None
        self.setUpIcons()
        
        self.statsButton = Button(self.fieldWidth + self.sidebar/2.5, 
            self.horizBorder, self.width//4, self.height//15, 'Check Stats!',
            font=f'Monaco {self.sidebar//15} bold')

        self.transferButton = Button(self.fieldWidth + self.sidebar/2.5,
            self.horizBorder * 2, self.width//4, self.height//15, 'Make Transfers!',
            font=f'Monaco {self.sidebar//15} bold')

        self.aiTeamButton = Button(self.fieldWidth + self.sidebar/2.5,
            self.horizBorder * 3, self.width//4, self.height//15, 'View AI Team!',
            font=f'Monaco {self.sidebar//15} bold')

        self.recsButton = Button(self.fieldWidth + self.sidebar/2.5,
            self.horizBorder * 4, self.width//4, self.height//15, 'Check Our Recs!',
            font=f'Monaco {self.sidebar//15} bold')

        self.helpButton = Button(self.height//14, self.height//14, 
            self.width//25, self.width//25, text='?', 
            font=f'Futura {self.width//40} bold', bType='c')

        pprint(self.privateInfo)
        print()
        pprint(self.publicInfo)

    def getTeam(self):
        self.starters = [[], [], [], []]
        self.bench = []
        for element in self.picks:
            ID = element['element']
            if element['multiplier'] == 0:
                self.bench.append(ID)
            else:
                player = self.players[ID]
                pos = player['posClass']
                if(pos == 'GKP'):
                    self.starters[3].append(ID)
                elif(pos == 'DEF'):
                    self.starters[2].append(ID)
                elif(pos == 'MID'):
                    self.starters[1].append(ID)
                elif(pos == 'FWD'):
                    self.starters[0].append(ID)

    def setUpIcons(self):
        self.icons = []
        vertPoints = self.midpointFinder(self.topBorder * 1.8, 
            self.topBorder + self.fieldHeight, 2, True)
        for i in range(4):
            y = vertPoints[i]
            if(len(self.starters[i]) >= 5):
                n, include, border = len(self.starters[i]) - 2, True, self.horizBorder * 1.5   
            else:
                n, include, border = len(self.starters[i]), False, self.horizBorder
            horizPoints = self.midpointFinder(border,
                self.fieldWidth - border, n, include)
            for c in range(len(self.starters[i])):
                ID = self.starters[i][c]
                x = horizPoints[c]
                self.icons.append(PlayerIcon(ID, self.players[ID], x, y, 
                    self.scaleImage(self.playerImages[ID], 1/3) ))
        
        y = self.topBorder * 4.5
        dy = self.topBorder * 1.2
        dx = self.sidebar // 2.5
        for r in range(2):
            x = self.fieldWidth + self.sidebar / 4
            for c in range(2):
                ID = self.bench[r * 2 + c]
                self.icons.append(PlayerIcon(ID, self.players[ID], x, y,
                    self.scaleImage(self.playerImages[ID], 1/3)))
                x += dx
            y += dy

    @staticmethod
    def midpointFinder(a, b, midpoints, inclusive):
        # returns list of midpoints between a & b
        midpointList = [a] if inclusive else []
        for i in range(1, midpoints + 1):
            mid = int(a + (b - a) * i / (midpoints + 1))
            midpointList.append(mid)
        if(inclusive):
            midpointList.append(b)
        return midpointList

    def mousePressed(self, event):
        if(self.helpButton.wasClicked(event)):
            helpMode = HelpScreen(self.app.team, mode='k')
            self.app.setActiveMode(helpMode)
        if(self.transferButton.wasClicked(event)):
            if(self.selected):
                self.transferButton.text = 'Make Transfer!'
                self.transferButton.color = 'white'
                self.app.stats.mode = 'transfer'
                self.app.stats.pOut = self.selected[0].player
                self.app.setActiveMode(self.app.stats)
            else:
                self.transferButton.text = 'Pick a Player!'
                self.transferButton.color = 'red'
        elif(self.statsButton.wasClicked(event)):
            self.app.stats.mode = 'display'
            self.app.setActiveMode(self.app.stats)
        elif(self.aiTeamButton.wasClicked(event)):
            self.app.setActiveMode(self.app.ai)
        elif(self.recsButton.wasClicked(event)):
            self.app.setActiveMode(self.app.recs)
        for icon in self.icons:
            if icon.wasClicked(event):
                self.dragged = icon
                if(icon not in self.selected):
                    for i in self.icons:
                        i.selected = False
                    self.selected = [icon]
                    icon.selected =  True
                elif icon.selected:
                    icon.selected = False
                    self.selected = []

    def mouseDragged(self, event):
        if(self.helpButton.wasClicked(event)):
            self.app.setActiveMode(self.app.keyHelp)
        if(self.dragged):
            self.dragged.x = event.x
            self.dragged.y = event.y
        for icon in self.selected:
            icon.selected = False
        self.selected = []

    def mouseReleased(self, event):
        if(self.dragged != None):
            for icon in self.icons:
                if icon.id != self.dragged.id:
                    if(icon.overlaps(self.dragged) and self.canSwap(icon)):
                        '''self.dragged.x, icon.x = icon.x, self.dragged.origX
                        self.dragged.y, icon.y = icon.y, self.dragged.origY
                        self.dragged.origX, self.dragged.origY = self.dragged.x, self.dragged.y
                        icon.origX, icon.origY = icon.x, icon.y'''

                        newPicks = makeSub(self.app.fpl, self.app.loggedInSession, 
                            self.app.id, self.picks, icon.id, self.dragged.id)
                        print(newPicks.status_code)
                        pprint(newPicks.json())
                        if(newPicks.status_code == 200):
                            self.picks = newPicks.json()['picks']
                            self.getTeam()
                            self.setUpIcons()
                        else:
                            self.dragged.x = self.dragged.origX
                            self.dragged.y = self.dragged.origY
                        break
            else:
                self.dragged.x = self.dragged.origX
                self.dragged.y = self.dragged.origY
            self.dragged = None

    def canSwap(self, other):
        selfID = self.dragged.player.id
        otherID = other.player.id
        selfIsStarter, otherIsStarter = False, False
        for i in range(4):
            if(selfID in self.starters[i]): selfIsStarter = True
            if(otherID in self.starters[i]): otherIsStarter = True 
        if(selfIsStarter and otherIsStarter): return False
        elif(not selfIsStarter and not otherIsStarter):
            if(self.dragged.player['posClass'] != 'GKP' and other.player['posClass'] != 'GKP'):
                return True
        if(selfIsStarter):
            starter, bench = self.dragged, other
        else:
            starter, bench = other, self.dragged
        #print(starter.player, bench.player)

        starterPos = starter.player['posClass']
        benchPos = bench.player['posClass']
        if(starterPos == benchPos): return True
        elif(starterPos == 'GKP' or benchPos == 'GKP'):
            return False
        elif(starterPos == 'DEF'):
            num = len(self.starters[2])
            return num > 3
        elif(starterPos == 'MID'):
            num = len(self.starters[1])
            return num > 2
        elif(starterPos == 'FWD'):
            num = len(self.starters[0])
            return num > 1

    def drawTeam(self, canvas):
        for icon in self.icons:
            icon.draw(canvas)

    def drawSidebar(self, canvas):
        self.statsButton.draw(canvas)
        self.transferButton.draw(canvas)
        self.aiTeamButton.draw(canvas)
        self.recsButton.draw(canvas)

        canvas.create_text( self.fieldWidth + self.sidebar/2.2, self.height//2,
            text='Substitutes', font=f'Futura {self.sidebar//8} bold', fill='white')

    def redrawAll(self, canvas):
        canvas.create_rectangle(0, 0, self.width, self.height, 
            fill=self.app.bgColor)
        
        canvas.create_text(self.fieldWidth//2, self.topBorder//2, 
            text=f"{self.app.userName[0]}'s Team", fill='white', font=f'Futura {self.width//20} bold')
        
        canvas.create_polygon(self.field, fill='green', outline='white', width=5)

        self.drawTeam(canvas)
        self.drawTeamInfo(canvas)
        self.helpButton.draw(canvas)

        #canvas.create_line(self.width - self.sidebar, 0, 
        #    self.width - self.sidebar, self.height, width=10, fill='white')

        self.drawSidebar(canvas)

    def drawTeamInfo(self, canvas):
        x, y = self.horizBorder//4, self.height*3/4
        canvas.create_rectangle(x, y, 
            self.width//3.9, self.height - self.horizBorder//4,
            fill='white', width=5)
        x += self.horizBorder//5
        y += self.horizBorder//6
        canvas.create_text(x, y, text=f"Total Points: {self.publicInfo['summary_overall_points']}",
            font=f'Monaco {self.width//60}', anchor='nw')
        y += self.horizBorder//2.7
        canvas.create_text(x, y, text=f"Gameweek Points: {self.publicInfo['summary_event_points']}",
            font=f'Monaco {self.width//60}', anchor='nw')
        y += self.horizBorder//2.7
        canvas.create_text(x, y, text=f"Rank: {self.publicInfo['summary_overall_rank']}",
            font=f'Monaco {self.width//60}', anchor='nw')
        y += self.horizBorder//2.7
        canvas.create_text(x, y, text=f"Team Value: {self.moneyData['value']/10}",
            font=f'Monaco {self.width//60}', anchor='nw')
        y += self.horizBorder//2.7
        canvas.create_text(x, y, text=f"Funds Remaining: {self.moneyData['bank']/10}", 
            font=f'Monaco {self.width//60}', anchor='nw')
        y += self.horizBorder//2.7
        made = self.moneyData['made']
        limit = self.moneyData['limit']
        ft = max(limit-made, 0)
        canvas.create_text(x, y, text=f'Free Transfers: {ft}',
            font=f'Monaco {self.width//60}', anchor='nw')


    def keyPressed(self, event):
        if(event.key == 'q'):
            self.app.__init__(width=1000, height = 750)
        if(self.selected and event.key == 'Enter'):
            self.app.playerMode = PlayerMode(self.selected[0].player,
                redirect=self.app.team)
            self.app.setActiveMode(self.app.playerMode)

class PlayerIcon(object):
    def __init__(self, ID, player, x, y, img):
        self.id = ID
        self.x = x
        self.y = y
        self.player = player
        self.img = img
        
        self.selected = False
        
        self.origX = x
        self.origY = y

    def draw(self, canvas):
        rect = (self.x - 0.7*self.img.width, self.y, 
            self.x + 0.7*self.img.width, self.y + self.img.width/3)
        canvas.create_image(self.x, self.y, anchor='s', 
            image=ImageTk.PhotoImage(self.img))
        canvas.create_rectangle(rect, fill='blue', width=0)
        canvas.create_text(self.x, (rect[1] + rect[3])/2, 
            text=self.player.name, font=f'Monaco {int(self.img.width/7)}',
            fill='white')
        if(self.selected == True):
            canvas.create_rectangle(self.x - 0.7*self.img.width, self.y - self.img.height,
                self.x + 0.7*self.img.width, self.y + self.img.width/3,
                outline='red', width=5)

    def wasClicked(self, event):
        rect = (self.x - 0.7*self.img.width, self.y, 
            self.x + 0.7*self.img.width, self.y + self.img.width/3)
        x, y = event.x, event.y
        if(rect[0] < x < rect[2] and
            self.y - self.img.height < y < self.y + self.img.width/3):
            return True
        return False
        
    def overlaps(self, other):
        dist = (other.x - self.x) ** 2 + (other.y - self.y)**2
        return dist**0.5 < self.img.height

class HelpScreen(Mode):
    def __init__(self, redirect, mode='s'):
        super().__init__()
        self.redirect = redirect
        self.mode = mode # p (PlayerMode), s (StatsMode), k (Keys)

    def appStarted(self):
        self.keyHelp = '''\
Enter: Select currently highlighted item
Q: Exit, return to previous page, logout (on default team screen)
Space: 
    (1) Complete transfer (on transfer page)
    (2) Pause/unpause video (on highlight watcher page)
Up/Down Arrows: move selection up or down
Left/Right Arrows: skip up or down by ten (on "Make Transfers" and "Player Statistics" pages)
'''
        playerHelp = '''\
Value: price required to transfer a player into a Fantasy team
Points: amount of Fantasy points a player has earned this season
Minutes: number of minutes a player has played this season
Form: average amount of Fantasy points a player has earned in the last five gameweeks
Bonus: amount of FPL points a player has earned this season through the bonus points system 
BPS: number of points a player has earned this season in the bonus points system
Goals: number of goals a player has scored this season
Assists: number of assists a player has earned this season
xG: expected goals, a statistic measuring the number of goals "expected" of a player this season
xA: expected assists, a statistic measuring the number of assists "expected" of a player this season
ICT Index: statistic measuring a player's influence, creativity, and threat this season
Creativity: statistic measuring a player's creativity this season
Influence: statistic measuring a player's influence this season
Threat: statistic measuring a player's attacking threat this season
Status: player's availability to play next gameweek 
(status may be on of: A: Active, D: Doubtful, I: Injured, U: Unavailable, N: No longer in game)
Clean Sheets: number of games a player has completed without conceding any goals
Goals Conceded: number of goals scored against a player this season
Popularity: percent of Fantasy teams that own a player
Transfer Balance: net change in number of Fantasy players who own a player
Cost Change: net change in a player's value since the start of the season
Transfers In: number of times a player has been transferred into Fantasy players' teams
Transfers Out: number of times a player has been transferred out Fantasy players' teams
'''
        statsHelp1 = '''\
Name: name of player
Position: role of player in Fantasy game (i.e. Goalkeeper, Defender, Midfielder, Forward)
Goals: number of goals a player has scored this season
Assists: number of assists a player has earned this season
Minutes: number of minutes a player has played this sesason
Clean Sheets: number of a games a player has completed without conceding any goals
Saves: number of saves a player (usually a goalkeeper) has made this season
Own Goals: number of goals a player has scored against his own team this season
Pens Missed: number of penalty kicks a player has failed to score this season
Pens Saved: number of penalty kicks a player (usually a goalkeeper) has saved this season
Yellows: number of yellow cards a player has received this season
Reds: number of red cards a player has received this season
Goals Conceded: number of goals scored against a player this season
Games Played: number of games a player has been involved in this season(as a substitute or starter)
Play Percent: percent of total minutes a player has played this season
xG: expected goals, a statistic measuring the number of goals "expected" of a player this season
xA: expected assists, a statistic measuring the number of assists "expected" of a player this season
Shot: number of shots taken by a player on goal this season
Key Passes: number of passes made by a player that led to clear goal-scoring opportunities
Non-Penalty Goals: number of goals a player has scored this season, excluding goals from penalties
npxG: player's expected goals excluding goals from penalties
'''
        statsHelp2 = '''\
xGChain: expected goals from every possession a player is involved in this season
xGBuildup: expected goals from every possession a player is involved in without key passes or shots
xG90: expected goals per 90 minutes of play
xA90: expected assists per 90 minutes of play
Points: amount of Fantasy points a player has earned this season
Form: average amount of Fantasy points a player has earned in the last five gameweeks
PPM: amount of Fantasy points a player has earned per million of value
P90: amount of Fantasy points a player has earned per ninety minutes played
Bonus: amount of FPL points a player has earned this season through the bonus points system 
BPS: number of points a player has earned this season in the bonus points system
Creativity: statistic measuring a player's creativity this season
Influence: statistic measuring a player's influence this season
Threat: statistic measuring a player's attacking threat this season
ICT Index: statistic measuring a player's influence, creativity, and threat this season
Status: player's availability to play next gameweek 
        • A: Active, D: Doubtful, I: Injured, U: Unavailable, N: No longer in game
Value: price required to transfer a player into a Fantasy team
Popularity: percent of Fantasy teams that own a player
Transfers In: number of times a player has been transferred into Fantasy players' teams
Transfers Out: number of times a player has been transferred out Fantasy players' teams
'''
        self.playerHelp = [playerHelp, self.keyHelp]
        self.statsHelp = [statsHelp1, statsHelp2, self.keyHelp]
        self.statIndex = 0

    def keyPressed(self, event):
        if(event.key=='q'):
            self.app.setActiveMode(self.redirect)
        elif(self.mode!='k' and (event.key=='Right' or event.key=='Left')):
            if(self.mode == 'p'): pg = 2
            else: pg = 3
            self.statIndex = (self.statIndex + 1) % pg

    def redrawAll(self, canvas):
        text = self.keyHelp if self.mode=='k' else self.statsHelp[self.statIndex]
        title = 'Player Help' if self.mode=='p' else 'Stats Help' if self.mode=='s' else 'Key Help'
        canvas.create_rectangle(0, 0, self.width, self.height,
            fill=self.app.bgColor)
        canvas.create_text(self.width/2, self.height//10, 
            text=title, fill='white', font=f'Futura {self.width//20} bold')
        canvas.create_text(self.width/2, self.height*4/7,
            text=text, fill='white', font=f'Futura {self.width//50}', justify=LEFT)
        if(self.mode!='k'):
            if(self.mode=='p'): pg = 2
            else: pg = 3
            canvas.create_text(self.width/2, self.height*19/20, anchor='n', fill='white',
                text=f'Page {self.statIndex+1} of {pg}', font=f'Futura {self.width//70} bold')

class PlayerLinePlot(object):
    def __init__(self, x, y, w, h, xData, yData, xLabel=None, yLabel=None, outline=True):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.xData = xData
        self.yData = yData
        print(xData)
        print(yData)
        self.xLabel = xLabel
        self.yLabel = yLabel
        self.outline = outline
        self.xMax, self.xMin = max(xData), min(xData + [0])
        self.yMax, self.yMin = max(yData + [0]), min(yData + [0])
        if(self.yMax == self.yMin == 0): self.yMax = 1
        if(self.yLabel == 'value' and min(yData) != max(yData)):
            self.yMin = min(yData)
        self.topMargin = min(self.w, self.h)/3
        self.margin = min(self.w, self.h) / 8
        self.graphW = self.w - 2 * self.margin
        self.graphH = self.h - self.margin - self.topMargin
        self.corners = [
            (self.x - self.w/2, self.y - self.h/2),
            (self.x + self.w/2, self.y - self.h/2),
            (self.x + self.w/2, self.y + self.h/2),
            (self.x - self.w/2, self.y + self.h/2)
        ]
        self.gridCorners = [
            (self.x - self.w/2 + self.margin, self.y - self.h/2 + self.topMargin),
            (self.x + self.w/2 - self.margin, self.y - self.h/2 + self.topMargin),
            (self.x + self.w/2 - self.margin, self.y + self.h/2 - self.margin),
            (self.x - self.w/2 + self.margin, self.y + self.h/2 - self.margin)
        ]
        self.getPoints()
        self.p1 = self.valueToPoint(0, self.bestFit(0)) 
        self.p2 = self.valueToPoint(self.xData[-1], self.bestFit(self.xData[-1]))
    
    def bestFit(self, x):
        return self.slope * x + self.intercept

    def getPoints(self):
        self.slope, self.intercept, self.r = self.linearRegression(list(zip(self.xData, self.yData)))
        r = 5
        self.points = []
        values = zip(self.xData, self.yData)
        for xVal, yVal in values:
            x, y = self.valueToPoint(xVal, yVal)
            point = Button(x, y, 12, 12, None, None, bType='c', color='blue')
            point.xVal, point.yVal = xVal, yVal
            self.points.append(point)

    def draw(self, canvas):
        if(self.outline):
            canvas.create_rectangle(self.corners[0], self.corners[2], width=5)
        self.drawGrid(canvas)
        self.drawGraph(canvas)
        canvas.create_text(self.x, self.y - self.h/2 + self.topMargin/2,
            text=f'{self.yLabel} vs {self.xLabel}', font=f'Futura {int(self.margin//1.5)} bold',
            fill='black')
        canvas.create_line(self.p1, self.p2, fill='red', dash=(10, 5), width=3)
        canvas.create_text(self.x, self.y + self.h/2 - self.margin/2,
            text='Use arrow keys to toggle graphs | Click points to see values', font=f'Courier {int(self.margin/3)}')

    def drawGrid(self, canvas):
        xAxis = self.gridCorners[2][1] if self.yMin >= 0 \
            else self.gridCorners[0][1] if self.yMax == 0 \
            else self.gridCorners[0][1] + self.yMax/(self.yMax - self.yMin) * self.graphH
        canvas.create_line(self.gridCorners[0][0], xAxis, self.gridCorners[1][0], xAxis)
        canvas.create_line(self.gridCorners[0], self.gridCorners[3])
        canvas.create_polygon(
            (self.gridCorners[0][0] - self.margin/4, self.gridCorners[0][1]),
            (self.gridCorners[0][0] + self.margin/4, self.gridCorners[0][1]),
            (self.gridCorners[0][0], self.gridCorners[0][1] - self.margin/2),
            fill='black'
        )
        canvas.create_polygon(
            (self.gridCorners[2][0], xAxis - self.margin/4),
            (self.gridCorners[2][0], xAxis + self.margin/4),
            (self.gridCorners[2][0] + self.margin/2, xAxis),
            fill='black'
        )
        canvas.create_text(self.x + self.graphW/2, self.y - self.graphH/2,
            text=f'R = {round(self.r, 2)}', font=f'Monaco {int(self.margin//1.7)}',
            anchor='ne')

    def drawGraph(self, canvas):
        for i in range(len(self.points) - 1):
            canvas.create_line(self.points[i].x, self.points[i].y, 
                self.points[i + 1].x, self.points[i + 1].y, fill='blue', width=3)
        for point in self.points:
            point.draw(canvas)
        
    def valueToPoint(self, xVal, yVal):
        x = self.gridCorners[0][0] + xVal/self.xMax * self.graphW
        if(self.yMin == 0):
            y = self.gridCorners[0][1] + (1 - yVal/self.yMax) * self.graphH
        elif(self.yMax == 0):
            y = self.gridCorners[2][1] - (1 - yVal/self.yMin) * self.graphH
        else:
            y = self.gridCorners[0][1] + (self.yMax - yVal)/(self.yMax - self.yMin) * self.graphH
        return (x, y)

    @staticmethod
    def linearRegression(pointsList):
        xSum, ySum, listLen = 0, 0, len(pointsList)
        for x, y in pointsList:
            xSum += x
            ySum += y
        xAvg, yAvg = xSum / listLen, ySum / listLen

        ssXX, ssXY = 0, 0
        for x, y in pointsList:
            ssXX += (x - xAvg)**2
            ssXY += (x - xAvg) * (y - yAvg)
        slope = ssXY / ssXX if ssXX != 0 else 0
        intercept = yAvg - slope * xAvg

        def lineOfBestFit(x):
            return slope * x + intercept
        
        ssDev, ssRes = 0, 0
        for x, y in pointsList:
            ssDev += (y - yAvg)**2
            ssRes += (y - lineOfBestFit(x))**2
            
        r = (abs(ssDev - ssRes) / ssDev)**0.5 if ssDev != 0 else 1
        return (slope, intercept, r)


class PlayerMode(Mode):
    def __init__(self, player, redirect=None):
        super().__init__()
        self.player = player
        self.redirect = redirect

    stats = [
        'total_points',
        'goals_scored',
        'assists',
        'bonus',
        'bps',
        'clean_sheets',
        'goals_conceded',
        'ict_index',
        'minutes',
        'selected',
        'transfers_balance',
        'transfers_in',
        'transfers_out',
        'value'
    ]

    def appStarted(self):
        if(self.redirect==None):
            self.redirect = self.app.stats
        self.history = self.player.history
        self.border = self.width / 25
        self.image = self.app.playerImages[self.player.id] if self.player.id in self.app.playerImages else None
        self.teamImage = self.app.teamImages[self.player.team]
        self.counter = 0
        data = [a[self.stats[self.counter]] for a in self.history]
        pW, pH = self.width/2.5, self.height/3.5
        plotX, plotY = self.image.width + self.border + pW/2, self.height*4.15/5
        self.plot = PlayerLinePlot(
            plotX, plotY, pW, pH,
            list(range(1,self.app.fpl.lastGameweek+1)), data, xLabel='Gameweek',
            yLabel='Points') if len(self.history) > 1 else None
        self.display = None
        bW = self.width - (plotX + pW/2) - 2*self.border
        self.button = Button(plotX + pW/2 + self.border + bW/2,
            plotY, bW, pH, text=None, font=None)

        self.helpButton = Button(self.width - self.height/14, self.height/14,
            self.width/25, self.width/25, text='?', 
            font=f'Futura {self.width//40} bold', bType='c', outline='black')

    def keyPressed(self, event):
        graphChanged = False
        if(event.key == 'q'):
            self.app.setActiveMode(self.redirect)
        elif(event.key == 'Left' and self.plot):
            self.counter = (self.counter - 1) % len(self.stats)
            graphChanged = True
        elif(event.key == 'Right' and self.plot):
            self.counter = (self.counter + 1) % len(self.stats)
            graphChanged = True
        if(graphChanged):
            pW, pH = self.width/2.5, self.height/3.5
            data = [a[self.stats[self.counter]] for a in self.history]
            self.plot = PlayerLinePlot(
                self.image.width + self.border + pW/2,
                self.height*4.15/5, 
                pW, 
                pH, 
                list(range(1, len(self.player.gameHist)+1)), data, xLabel='Gameweek',
                yLabel=self.stats[self.counter])

    def redrawAll(self, canvas):
        self.drawHeader(canvas)
        self.drawSidebar(canvas)
        self.drawBody(canvas)
        self.drawPrevGames(canvas)
        self.drawPlot(canvas) if self.plot else None
        self.helpButton.draw(canvas)

    def drawPrevGames(self, canvas):
        self.button.draw(canvas)
        games = min(5, len(self.player.gameHist))
        top = self.button.y - self.button.h/2
        left = self.button.x - self.button.w/2
        for i in range(games):
            home, hScore, away, aScore, res = self.player.gameHist[-(i+1)]
            hAbbrev, aAbbrev = self.app.fpl.abbrevs[home], self.app.fpl.abbrevs[away]
            week = self.app.fpl.lastGameweek - i
            text = f'{hAbbrev} {hScore} – {aScore} {aAbbrev}'
            color = 'red' if res=='L' else 'green' if res=='W' else 'yellow'
            canvas.create_rectangle(left, top, left + self.button.w, top + self.button.h/5,
                fill=color)
            canvas.create_text(left+self.button.w/8, top+self.button.h/10,
                text=week, font=f'Futura {self.width//60} bold')
            canvas.create_text(left + self.button.w/2 + self.button.w/16, top+self.button.h/10, 
                text=text, font=f'Futura {self.width//50} bold')
            top += self.button.h/5


    def drawBody(self, canvas):
        x = self.image.width + self.border
        self.drawCol(canvas, x, ['points', 'minutes', 'form', 'bonus'])
        x += self.border * 3.5
        self.drawCol(canvas, x, ['goals', 'assists', 'xG', 'xA'])
        x += self.border * 3
        self.drawCol(canvas, x, ['ict', 'creativity', 'influence', 'threat'])
        x += self.border * 3.7
        self.drawCol(canvas, x, ['status', 'cs', 'yellows', 'reds'])
        x += self.border * 3
        self.drawCol(canvas, x, ['popularity', 'costChange', 'transfersIn', 'transfersOut'])

    def drawCol(self, canvas, x, labels):
        y = self.height/4 + self.border
        for stat in labels:
            canvas.create_text(x, y, text=stat, anchor='nw',
                font=f'Futura {self.width//40} bold')
            y += self.height/25
            val = round(self.player[stat], 2) if isinstance(self.player[stat], float)\
                else self.player[stat]
            canvas.create_text(x, y, text=f"{val}", anchor='nw',
                font=f'Monaco {self.width//45}')
            y += self.height/20

    def drawHeader(self, canvas):
        fontSize = self.width // 10
        if(len(self.player.name) > 8):
            fontSize = int(fontSize * 18/(10 + len(self.player.name)))
        canvas.create_line(self.image.width, self.height*1/4, 
            self.width, self.height * 1/4, fill=self.app.bgColor, width=20)
        canvas.create_text(self.image.width + self.border, self.height * 1/8,
            text=self.player.name, font=f'Futura {fontSize} bold', 
            anchor='w', fill='black')

    def drawPlot(self, canvas):
        self.plot.draw(canvas)
        if(self.display):
            x, y = self.display[1]
            w, h = self.plot.graphW//2.5, self.plot.graphH//3
            canvas.create_rectangle(x - w/2, y - h/2, x + w/2, y + h/2, fill='white')
            canvas.create_text(x, y, text=self.display[0],
                font=f'Monaco {int(self.plot.graphH//12)} bold', fill='black')

    def drawSidebar(self, canvas):
        x = self.image.width//2
        canvas.create_rectangle(0, 0, self.image.width, self.height, 
            fill=self.app.bgColor)
        canvas.create_image(x, self.height*3/7,
            image=ImageTk.PhotoImage(self.teamImage))
        if(self.image):
            canvas.create_image(0, self.height, anchor='sw',
                image=ImageTk.PhotoImage(self.image))
        canvas.create_text(x, self.height/8,
            text=self.player['posClass'], font=f'Futura {self.width//20} bold',
            fill='white', anchor='s')
        canvas.create_text(x, self.height/8,
            text=f"£{self.player['value']}", font=f'Futura {self.width//20} bold',
            fill='white', anchor='n')

    def mousePressed(self, event):
        if(self.button.wasClicked(event)):
            self.app.gwMode = GameweekMode(self.player)
            self.app.setActiveMode(self.app.gwMode)
        elif(self.helpButton.wasClicked(event)):
            helpMode = HelpScreen(redirect=self.app.playerMode, mode='p')
            self.app.setActiveMode(helpMode)
        if(self.plot):
            for point in self.plot.points:
                if(point.wasClicked(event)):
                    print(point.xVal, point.yVal)
                    self.display = (f'{self.plot.xLabel}: {point.xVal}\n{self.plot.yLabel}: {point.yVal}', (point.x, point.y))
                    break
            else:
                self.display = None

class Button(object):
    def __init__(self, x, y, w, h, text, font, bType='r', color='white', outline='black'):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.text = text
        self.font = font
        self.type = bType
        self.color = color
        self.bounds = (self.x - self.w/2, self.y - self.h/2,
                       self.x + self.w/2, self.y + self.h/2)
        self.outline = outline

    def wasClicked(self, event):
        if(self.bounds[0] < event.x < self.bounds[2] and
           self.bounds[1] < event.y < self.bounds[3]):
           return True
        else:
            return False 

    def draw(self, canvas):
        if(self.type == 'c'): 
            canvas.create_oval(self.bounds, fill=self.color, outline=self.outline)
        elif(self.type == 'r'):
            canvas.create_rectangle(self.bounds, fill=self.color, 
                outline=self.outline, width=5)
        if(self.text):
            canvas.create_text(self.x, self.y, text=self.text, 
                font=self.font)

class GameweekMode(Mode):
    def __init__(self, player):
        super().__init__()
        self.player = player
    
    def appStarted(self):
        self.offset = 0
        self.selected = 1
        self.gameHist = self.player.gameHist
        self.fixtures = self.player.fixtures
        self.lst = list(enumerate(self.gameHist + self.fixtures))
        self.border = self.width//25
        self.cellH = (self.height - self.border * 2)/11
        self.topBorder = self.cellH + self.border
        self.diffSpectrum = [self.app.rgbString(*color)
            for color in
            self.colorBlender((100, 255, 100), (255, 100, 100), 3)]
        self.diffSpectrum[2] = self.app.rgbString(200, 200, 200)
        #self.displayed = self.app.fpl.lastGameweek
        self.displayed=self.selected
        self.getHighlightThumbnails()
        self.selectedHighlight = 0
    
    def getHighlightThumbnails(self):
        week = self.displayed
        self.thumbnails = []
        self.highlights = None
        if(week in self.player.highlights):
            self.highlights = self.player.highlights[week]
            for highlights in self.player.highlights[week]:
                url = highlights[0]['thumbnail']
                image = self.loadImage(url)
                self.thumbnails.append(image)
        print(self.thumbnails)

    # helper function: returns list of intermediate colors between 2 given colors
    @staticmethod
    def colorBlender(rgb1, rgb2, midpoints):
        # returns list of colors between rgb1 & rgb2
        r1, g1, b1 = rgb1
        r2, g2, b2 = rgb2
        midpointList = [rgb1]
        for i in range(1, midpoints + 1):
            rmid = round(r1 + (r2 - r1) * i / (midpoints + 1))
            gmid = round(g1 + (g2 - g1) * i / (midpoints + 1))
            bmid = round(b1 + (b2 - b1) * i / (midpoints + 1))
            midpointList.append((rmid, gmid, bmid))
        midpointList.append(rgb2)
        return midpointList

    def drawGameTable(self, canvas):
        canvas.create_rectangle(self.border, self.border,
            self.border + self.width/4, self.border + self.cellH,
            fill='white')
        canvas.create_text(self.border + self.width/8, self.border + self.cellH/2,
            text=self.player.name, font=f'Futura {self.width//50} bold', fill='black')
        display = self.lst[self.offset:self.offset+10]
        y = self.topBorder
        orangeDims = None
        for item in display:

            if(len(item[1][2]) == 1):
                week, (gameweek, opp, home, diff, time) = item
                oppAbbrev = self.app.fpl.abbrevs.get(opp, '')
                text = f'{oppAbbrev} ({home})'
                color = self.diffSpectrum[diff-1]
            else:
                week, (home, hScore, away, aScore, res) = item
                hAbbrev, aAbbrev = self.app.fpl.abbrevs[home], self.app.fpl.abbrevs[away]
                text = f'{hAbbrev} {hScore} – {aScore} {aAbbrev}'
                color = 'red' if res=='L' else 'green' if res=='W' else 'yellow'
                gameweek = week + 1
            dims = self.border, y, self.border + self.width/4, y+self.cellH
            if(week + 1 == self.displayed):
                orangeDims = dims
            if(week + 1 == self.selected):
                blueDims = dims
            canvas.create_rectangle(dims, fill=color)
            canvas.create_text(self.border + self.width/64, y+self.cellH/2,
                text=gameweek, font=f'Futura {self.width//60} bold', anchor='w')
            canvas.create_text(self.border + self.width/8 + self.width/32, y+self.cellH/2,
                text=text, font=f'Futura {self.width//50} bold')
            y += self.cellH

        #if(orangeDims):
            #canvas.create_rectangle(orangeDims, fill=None, outline='orange', width=10)
        canvas.create_rectangle(blueDims, fill=None, outline='blue', width=5)

    def drawBody(self, canvas):
        canvas.create_rectangle(self.border + self.width/4, self.border,
            self.width-self.border, self.height-self.border, fill='white')
        if(self.lst[self.displayed-1][1][2] == 'A' or self.lst[self.displayed-1][1][2] == 'H'):
            week, (gameweek, opp, isHome, diff, time) = self.lst[self.displayed-1]
            if(isHome == 'H'): 
                home, away = self.player.team, opp
            else: 
                home, away = opp, self.player.team
            timeTo = (time - datetime.datetime.now()) - datetime.timedelta(hours=5)
            print(timeTo)
            if(timeTo.days == 0):
                if(timeTo.seconds < 3600):
                    timeString = f'{timeTo.seconds//60} min\n{timeTo.seconds%60}s'
                else:
                    timeString = f'{timeTo.seconds//3600} hr\n{timeTo.seconds//60%60} min'
            else:
                timeString = f'{timeTo.days} day\n{timeTo.seconds//3600} hr'
            canvas.create_text(
                (self.width/4 + self.width)/2, self.border*4,
                text='Time to:\n'+timeString, font=f'Futura {self.width//30} bold', justify=CENTER
            )
        else:
            week, (home, hScore, away, aScore, res) = self.lst[self.displayed-1]
            gameweek = week + 1
            canvas.create_text(
                (self.width/4 + self.width)/2, self.border*4,
                text=f'{hScore}–{aScore}', font=f'Futura {self.width//15} bold'
            )
            dx = (self.width*3/4-self.border*4)/5
            x = self.width/4 + 2*self.border
            y = self.height*2/5
            self.drawRow(canvas, week, x, y, dx, ['minutes', 'total_points', 'goals_scored', 'assists', 'bonus'])
            y += self.border*2
            self.drawRow(canvas, week, x, y, dx, ['ict_index', 'red_cards', 'yellow_cards', 'value', 'transfers_balance'])
        hImage, aImage = self.app.teamImages[home], self.app.teamImages[away]
        canvas.create_text(self.border+self.width/4+self.width/128, self.border,
            text=gameweek, anchor='nw', font=f'Futura {self.width//50} bold', fill='gray')
        if(hImage.height != 200): hImage = self.scaleImage(hImage, 200/hImage.height)
        if(aImage.height != 200): aImage = self.scaleImage(aImage, 200/aImage.height)
        canvas.create_image(self.border*4 + self.width/4, self.border*4,
            image=ImageTk.PhotoImage(hImage))
        canvas.create_image(self.width - self.border*4, self.border*4,
            image=ImageTk.PhotoImage(aImage))
        
        if(self.highlights):
            self.drawHighlights(canvas)
        else:
            canvas.create_text((self.width/4+self.width)/2, self.height*3/4,
                text='No highlights to display :(', font=f'Futura {self.width//40} bold')

    def drawHighlights(self, canvas):
        canvas.create_text((self.width/4+self.width)/2, self.height*3/4-self.border*2.5,
            text='Highlights', font=f'Futura {self.width//25} bold')
        x = self.width/4+self.border*2
        dx = (self.width*3/4-self.border*4)/4
        y = self.height*3/4
        num = min(len(self.thumbnails), 4)
        for i in range(num):
            canvas.create_image(x, y, anchor='w',
                image=ImageTk.PhotoImage(self.thumbnails[i]))
            if(i == self.selectedHighlight):
                imgW, imgH = self.thumbnails[0].size
                canvas.create_rectangle(x, y-imgH/2, x+imgW, y+imgH/2, 
                    fill=None, outline='red', width=5)
            x += dx
        
        title = self.highlights[self.selectedHighlight][0]['title']
        title = title[:title.find('|')-1]
        canvas.create_text(self.width*5/8, self.height*8/9,
            text=title,
            font=f'Futura {self.width//60} bold')

    statToReadable = {
        'minutes': 'Minutes', 
        'total_points': 'Points', 
        'goals_scored': 'Goals', 
        'assists': 'Assists', 
        'bonus': 'Bonus',
        'ict_index': 'ICT', 
        'red_cards': 'Reds', 
        'yellow_cards': 'Yellows', 
        'value': 'Value', 
        'transfers_balance': 'Balance'
    }

    def drawRow(self, canvas, week, x, y, dx, labels):
        for i in range(5):
            canvas.create_text(x, y, anchor='w', text=self.statToReadable[labels[i]], 
                font=f'Futura {self.width//40} bold')
            data = self.player.history[week][labels[i]]
            canvas.create_text(x, y+self.border/1.2, anchor='w', text=data, 
                font=f'Monaco {self.width//45} bold')
            x += dx

    def redrawAll(self, canvas):
        canvas.create_rectangle(0, 0, self.width, self.height, fill=self.app.bgColor)
        self.drawBody(canvas)
        self.drawGameTable(canvas)

    def keyPressed(self, event):
        pageMoved = False
        if(event.key=='q'):
            self.app.setActiveMode(self.app.playerMode)
        elif(event.key=='Up'):
            self.movePage(-1)
            pageMoved = True
        elif(event.key=='Down'):
            self.movePage(1)
            pageMoved = True
        elif(event.key=='Right'):
            self.selectedHighlight+=1
            self.selectedHighlight = min(self.selectedHighlight, len(self.thumbnails)-1)
        elif(event.key=='Left'):
            self.selectedHighlight-=1
            self.selectedHighlight = max(self.selectedHighlight, 0)
        elif(self.highlights and event.key=='Enter'):
            self.app.setActiveMode(HighlightWatcher(self.highlights[self.selectedHighlight], self.player))
        if(pageMoved):
            self.displayed = self.selected
            self.selectedHighlight = 0
            self.getHighlightThumbnails()

    def movePage(self, delta):
        if(delta < 0):
            if(self.selected - self.offset == 1): self.offset -= 1
            self.selected -= 1
            if(self.offset < 0):
                self.offset = 0
            if(self.selected < 1):
                self.selected = 1
        else:
            if(self.selected - self.offset == 10): self.offset += 1
            self.selected += 1
            if(self.offset > len(self.lst) - 10):
                self.offset = len(self.lst) - 10
            if(self.selected > len(self.lst)):
                self.selected = len(self.lst)

class StatsMode(Mode):    
    def __init__(self, headers=None):
        super().__init__()
        self.mode = 'display' # can be in either transfer mode or display mode
        if(headers):
            self.headers = headers
        else:
            self.headers = ['name', 'value', 'posClass', 'points', 'minutes', 
                'goals', 'assists', 'popularity', 'ppm', 'xG90', 'xA90']

    statAbbrevDict = {
        'name': 'Player', 'posClass': ' P ', 'goals': ' G ', 'assists': ' A ',
        'minutes': 'Min', 'cleanSheets': 'CS', 'saves': ' S ', 'ownGoals': 'OG',
        'pensMissed': 'PM', 'pensSaved': 'PS', 'yellows': 'YC', 'reds': 'RC',
        'conceded': 'GA', 'gamesPlayed': 'GP', 'playPercent': 'PP', 'xG': 'exG',
        'xA': 'exA', 'shots': 'SH', 'keyPasses': 'KP', 'nonPenaltyGoals': 'NPG',
        'npxG': 'nxG', 'xGChain': 'xGC', 'xGBuildup': 'xGB', 'xG90': 'xG90',
        'xA90': 'xA90', 'points': 'Pts', 'form': ' F ', 'ppm': 'PPM',
        'p90': 'P90', 'bonus': ' B ', 'bps': 'BPS', 'creativity': ' C ',
        'influence': ' I ', 'threat': ' T ', 'ict': 'ICT',
        'status': ' S ', 'value': ' V ', 'popularity': ' % ', 
        'transfersIn': 'TI', 'transfersOut': 'TO',
    }

    def appStarted(self):
        self.fpl = self.app.fpl
        self.border = self.width / 25
        self.topBorder = self.height / 7
        self.bottomBorder = self.height / 7
        self.players = self.fpl.players
        self.origLen = len(self.players)
        self.rowHeight = (self.height - self.topBorder - self.bottomBorder) / 11
        self.rowWidth = self.width - self.border * 2

        self.offset = 0
        self.selected = 0

        self.pOut = self.app.team.selected[0].player if self.app.team.selected else None

        self.playersToDisplay = self.players.values()
        self.sortingBy = 'points'
        self.key = lambda player: player[self.sortingBy]
        self.reverse = True
        self.playerLst = sorted(self.playersToDisplay, key=self.key, reverse=self.reverse)
        self.playersToDisplay = sorted(self.playersToDisplay, key=self.key, reverse=self.reverse)

        self.imagesToDisplay = dict()
        if(os.stat('displayImages.p').st_size == 0):
            for key in self.app.playerImages:
                img = self.app.playerImages[key]
                self.imagesToDisplay[key] = self.scaleImage(img, self.rowHeight/280)
            pickle.dump(self.imagesToDisplay, open('displayImages.p', 'wb'))
        else:
            self.imagesToDisplay = pickle.load(open('displayImages.p', 'rb'))

        self.getDisplayHeaders()
        self.getHeaderWidths()

        w = self.width//2.5
        self.search = TextBox(self.width//3 + w/3, self.height-self.bottomBorder/2,
            w, self.bottomBorder/2, font=f'Futura {self.height//30} bold')

        self.helpButton = Button(self.width - self.topBorder//2, self.topBorder//2,
            self.border, self.border, text='?', 
            font=f'Futura {self.width//40} bold', bType='c', outline='black')

        x = self.border + 2*(self.width//3+self.width//45)
        width = self.border*3.5
        height = self.rowHeight*1.1
        y = self.topBorder//2
        self.transferButton = Button(x+width//2, y, width, height,
            text='Transfer!', font=f'Futura {self.height//35} bold')
        self.displayButton = Button(self.width*5/6, self.height-self.bottomBorder/2,
            self.width//4, self.bottomBorder/2, text='Change Table Headers',
            font=f'Futura {self.height//45} bold')

    def searchName(self):
        name = self.search.text.lower()
        newPlayersToDisplay = []
        for player in self.playerLst:
            pName = unidecode(player.name).lower()
            firstName = unidecode(player['firstName']).lower()
            lastName = unidecode(player['lastName']).lower()
            if(name in pName or name in firstName or name in lastName):
                newPlayersToDisplay.append(player)

        self.offset = 0
        self.selected = 0
        self.playersToDisplay = newPlayersToDisplay

    def getDisplayHeaders(self):
        self.displayHeaders = []
        for header in self.headers:
            displayed = self.statAbbrevDict.get(header, None)
            self.displayHeaders.append(displayed)

    def getHeaderWidths(self):
        self.headerWidths = [self.width/3.5]
        totLen = sum(len(s) for s in self.displayHeaders[1:])
        for label in self.displayHeaders[1:]:
            prop = len(label)/totLen
            self.headerWidths.append(prop * (self.rowWidth - self.headerWidths[0]))

    def redrawAll(self, canvas):
        fill = self.app.bgColor if self.mode=='display' else '#5616e0'
        canvas.create_rectangle(0, 0, self.width, self.height, 
            fill=fill, width=5)
        if self.mode=='display':
            canvas.create_text(self.width/2, self.height/14, fill='white',
                text='Player Statistics', font=f'Futura {self.height // 15} bold')
        else:
            self.drawTransfer(canvas)
        self.drawTable(canvas)
        self.drawScrollBar(canvas)
        #canvas.create_text(0, 0, anchor='nw', fill='white',
        #    text='Press q to return to team screen', 
        #    font=f'Monaco {self.height // 30} bold')

        self.helpButton.draw(canvas)
        self.displayButton.draw(canvas)

        canvas.create_text(self.border, self.height-self.bottomBorder/2, anchor='w',
            text='Search players:', font=f'Futura {self.height//30} bold', fill='white')
        self.search.draw(canvas)

    def drawTransfer(self, canvas):
        width = self.width//3
        height = self.rowHeight*1.1
        x = self.border
        y = (self.topBorder - height)/2
        img = self.imagesToDisplay[self.pOut.id]
        canvas.create_rectangle(x, y, x + width, y+height, width=5,
            fill='white')
        canvas.create_text(x+self.border*0.3+img.width, y+height/2, anchor='w',
            text=f'Out: {self.pOut.name}  (£{self.pOut["value"]})', font=f'Futura {self.width//55} bold')
        canvas.create_image(x + self.border*0.1, y+height, anchor='sw',
            image=ImageTk.PhotoImage(img))
            
        x += width + width//15
        if(len(self.playersToDisplay) == 0):
            canvas.create_rectangle(x, y, x + width, y+height, width=5,
            fill='white')
        else:
            p = self.playersToDisplay[self.selected]
            img = self.imagesToDisplay[p.id]
            canvas.create_rectangle(x, y, x + width, y+height, width=5,
                fill='white')
            canvas.create_text(x+self.border*0.3+img.width, y+height/2, anchor='w',
                text=f'In: {p.name} (£{p["value"]})', font=f'Futura {self.width//55} bold')
            canvas.create_image(x + self.border*0.1, y+height, anchor='sw',
                image=ImageTk.PhotoImage(img))

            self.transferButton.draw(canvas)

    def drawTable(self, canvas):
        self.drawHeader(canvas)
        for i in range(10):
            if(i == len(self.playersToDisplay)): return
            playerIndex = i + self.offset
            selected = True if (playerIndex == self.selected) else False
            self.drawTableRow(canvas, i + 1, self.playersToDisplay[playerIndex], selected)

    def movePage(self, delta):
        if(delta < 0):
            if(self.selected - self.offset == 0): self.offset -= 1
            self.selected -= 1
            if(self.offset < 0):
                self.offset = 0
            if(self.selected < 0):
                self.selected = 0
        else:
            if(self.selected - self.offset == 9): self.offset += 1
            self.selected += 1
            if(len(self.playersToDisplay) > 10):
                if(self.offset > len(self.playersToDisplay) - 10):
                    self.offset = len(self.playersToDisplay) - 10
            if(self.selected > len(self.playersToDisplay) - 1):
                self.selected = len(self.playersToDisplay) - 1

    def keyPressed(self, event):
        if(event.key=='Right'):
            if(len(self.playersToDisplay) > 10):
                self.offset += 10
                self.selected += 10
                if(self.offset > len(self.playersToDisplay) - 10):
                    self.offset = len(self.playersToDisplay) - 10
                if(self.selected > len(self.playersToDisplay) - 1):
                    self.selected = len(self.playersToDisplay) - 1
        elif(event.key=='Left'):
            if(len(self.playersToDisplay) > 10):
                self.offset -= 10
                self.selected -= 10
                if(self.offset < 0):
                    self.offset = self.selected = 0
        elif(event.key=='Up'):
            self.movePage(-1)
        elif(event.key=='Down'):
            self.movePage(1)
        elif(event.key=='Enter'):
            if(self.playersToDisplay):
                p = self.playersToDisplay[self.selected]
                self.app.playerMode = PlayerMode(p)
                self.app.setActiveMode(self.app.playerMode)
        elif(self.search.entering):
            if(event.key == 'Delete'):
                self.search.text = self.search.text[:-1]
            elif(len(event.key) == 1):
                self.search.text += event.key
            elif(event.key == 'Space'):
                self.search.text += ' '
            self.searchName()
        elif(event.key =='q'):
            self.app.setActiveMode(self.app.team)

    def drawScrollBar(self, canvas):
        scrollBarBorder = self.border // 4
        canvas.create_rectangle(self.width - self.border + scrollBarBorder, 
            self.topBorder,
            self.width - scrollBarBorder, 
            self.height - self.bottomBorder, fill='white', width=5)
        progress = self.selected / len(self.players)
        tableHeight = 11 * self.rowHeight
        yLoc = self.topBorder + tableHeight * progress
        canvas.create_line(self.width - self.border + scrollBarBorder, yLoc,
            self.width - scrollBarBorder, yLoc, width=5, fill='red')

    def drawHeader(self, canvas):
        canvas.create_rectangle(self.border, self.topBorder,
            self.border + self.rowWidth, self.topBorder + self.rowHeight, 
            fill='#7e67e6', width=5)
        
        x = self.border
        for i in range(len(self.displayHeaders)):
            width = self.headerWidths[i]
            text = self.displayHeaders[i]
            if(text == self.statAbbrevDict[self.sortingBy]): 
                canvas.create_rectangle(x, self.topBorder,
                    x + width, self.topBorder + self.rowHeight,
                    fill='#bcaefc', width=5)
            canvas.create_line(x, self.topBorder, 
                x, self.topBorder + self.rowHeight, 
                fill='black', width=5)
            textX = x + width/2
            canvas.create_text(textX, self.topBorder + self.rowHeight/2, 
                text=text, font=f'Futura {self.width//50} bold', fill='black')
            x += width

    def drawTableRow(self, canvas, row, player, selected):
        if(selected): color = '#bad8ff'
        else: color = 'white'
        canvas.create_rectangle(self.border, 
            self.topBorder + self.rowHeight * row,
            self.border + self.rowWidth, 
            self.topBorder + self.rowHeight * (row + 1),
            fill=color, width=5)
        headers = self.headers
        widths = [self.headerWidths[0] * 3/4] + self.headerWidths[1:]
        x = self.border + self.headerWidths[0] * 1/4
        for i in range(len(headers)):
            width = widths[i]
            stat = headers[i]
            text = round(player[stat], 2) if isinstance(player[stat], float) else player[stat]
            if(i == 0):
                anchor='w'
                textX = x
                font = f'Futura {self.width//50} bold'
            else:
                anchor='center'
                textX = x + width/2
                font = f'Monaco {self.width//50}'
                canvas.create_line(x, self.topBorder + self.rowHeight * row, 
                    x, self.topBorder + self.rowHeight * (row+1), 
                    fill='black', width=5)
            canvas.create_text(textX, self.topBorder + self.rowHeight * (row + 0.5), 
                text=text, font=font, anchor=anchor)
            x += width
        
        img = self.imagesToDisplay[player.id] if player.id in self.imagesToDisplay else None
        if(img):
            canvas.create_image(self.border*1.1, 
                self.topBorder + self.rowHeight*(row + 1), anchor='sw',
                image=ImageTk.PhotoImage(img))

    def mousePressed(self, event):
        if(self.search.wasClicked(event)):
            self.search.entering = True
        else:
            self.search.entering = False
        if(self.displayButton.wasClicked(event)):
            self.app.setActiveMode(StatsModeSelectionScreen(list(self.statAbbrevDict.keys()), self.headers))
        elif(self.transferButton.wasClicked(event)):
            p = self.playersToDisplay[self.selected]
            res = makeTransfer(self.app.fpl, self.app.loggedInSession, self.app.id, 
                self.app.userTeam['picks'], p, self.pOut)
            print(res.text, res.status_code)
            self.transferButton.color='white'
            self.transferButton.text='Transfer!'
            self.transferButton.font = f'Futura {self.height//35} bold'

            if(res.status_code == 200):
                teamURL = f'https://fantasy.premierleague.com/api/my-team/{self.app.id}'
                self.app.userTeam = self.app.loggedInSession.get(teamURL).json()
                self.app.team.appStarted()
                self.app.setActiveMode(self.app.team)
            else:
                self.transferButton.color='red'
                if(p['posClass'] != self.pOut['posClass']):
                    self.transferButton.text='Wrong position!'
                else:
                    self.transferButton.text='Not enough $$$!'
                self.transferButton.font = f'Futura {self.width//70} bold'
                    
        elif(self.helpButton.wasClicked(event)):
            helpMode = HelpScreen(redirect=self.app.stats)
            self.app.setActiveMode(helpMode)
        if(event.y > self.topBorder and event.y < self.topBorder + self.rowHeight
            and event.x > self.border and event.x < self.width - self.border):
            x = self.border
            for i in range(len(self.headerWidths)):
                if(event.x < x + self.headerWidths[i]):
                    self.sortBy(self.headers[i])
                    break
                x += self.headerWidths[i]

    def sortBy(self, stat):
        print(stat)
        if(stat == self.sortingBy): self.reverse = not self.reverse
        else: self.reverse = True
        self.sortingBy = stat
        key = lambda player: player[self.sortingBy]
        self.playerLst.sort(key=key, reverse=self.reverse)
        self.playersToDisplay.sort(key=key, reverse=self.reverse)

class StatsModeSelectionScreen(Mode):
    def __init__(self, lst, selected):
        super().__init__()
        self.lst = lst
        self.selected = selected

    def appStarted(self):
        num = len(self.lst)
        self.cols = 4
        self.rows = num//self.cols + 1
        self.buttons = [[] for _ in range(self.rows)]
        self.border = self.width//25
        self.topBorder = self.width/7
        buttonWidth = (self.width - self.border * 2) / self.cols
        buttonHeight = (self.height - self.border - self.topBorder) / self.rows
        y = self.topBorder + buttonHeight/2
        for r in range(self.rows):
            x = self.border + buttonWidth/2
            for c in range(self.cols):
                index = r * self.cols + c
                if(index < len(self.lst)):
                    button = Button(x, y, buttonWidth, buttonHeight, text=self.lst[index],
                        font=f'Futura {self.width//50} bold')
                    if(self.lst[index] in self.selected):
                        button.color = 'yellow'
                    self.buttons[r].append(button)
                    x += buttonWidth
            y += buttonHeight
        
    def redrawAll(self, canvas):
        canvas.create_rectangle(0, 0, self.width, self.height, fill=self.app.bgColor)
        canvas.create_text(self.width//2, self.topBorder//2, 
            text='Change Headers', font=f'Futura {self.width//15} bold',
            fill='white')
        for row in self.buttons:
            for button in row:
                button.draw(canvas)

    def mousePressed(self, event):
        for row in self.buttons:
            for button in row:
                if(button.wasClicked(event)):
                    if(button.text in self.selected):
                        self.selected.remove(button.text)
                        button.color = 'white'
                    else:
                        self.selected.append(button.text)
                        button.color = 'yellow'
        
    def keyPressed(self, event):
        if(event.key == 'q'):
            mode = self.app.stats.mode
            self.app.stats = StatsMode(headers=self.selected)
            self.app.stats.mode = mode
            self.app.setActiveMode(self.app.stats)

class PlayerRecs(Mode):
    def appStarted(self):
        self.recs = getRecs(self.app.fpl, self.app.fpl.lastGameweek)
        self.recs.sort(key=lambda r: r[1], reverse=True)
        self.border = self.width//10
        self.setUpIcons()
    
    def setUpIcons(self):
        self.icons = []
        dx = (self.width - self.border*2)//4
        dy = (self.height - self.border*2)//3
        y = self.border + dy
        for r in range(3):
            x = self.border + dx/2
            for c in range(4):
                index = 4*r + c
                if(index < len(self.recs)):
                    player = self.recs[index][0]
                    icon = PlayerIcon(player.id, player, x, y,
                        self.scaleImage(self.app.playerImages[player.id], 1/2))
                    icon.ppoints = self.recs[index][1]
                    self.icons.append(icon)
                x += dx
            y += dy

    def keyPressed(self, event):
        if(event.key == 'q'):
            self.app.setActiveMode(self.app.team)

    def mousePressed(self, event):
        for icon in self.icons:
            if(icon.wasClicked(event)):
                self.app.playerMode = PlayerMode(icon.player, redirect=self.app.recs)
                self.app.setActiveMode(self.app.playerMode)

    def redrawAll(self, canvas):
        canvas.create_rectangle(0, 0, self.width, self.height,
            fill=self.app.bgColor)
        canvas.create_text(self.border/2, self.height/2, 
            text='Click on each player for more info!', angle=90,
            font=f'Futura {self.width//50} bold', fill='white')
        canvas.create_text(self.width-self.border/2, self.height/2, 
            text="Prediction made using sklearn's GaussianNB function", angle=270,
            font=f'Futura {self.width//50} bold', fill='white')
        canvas.create_text(self.width/2, self.height/10, 
            text=f'Best Player Predictions: Week {self.app.fpl.lastGameweek+1}', font=f'Futura {self.width//25} bold',
            fill='white')
        for icon in self.icons:
            icon.draw(canvas)
            canvas.create_text(icon.x - icon.img.width/2, icon.y - self.width//60, text=f'{icon.ppoints} pts',
                font=f'Futura {self.width//30} bold', angle=75, fill='white', anchor='sw')

class AITeamPicker(Mode):
    formations = [352, 343, 451, 442, 433, 541, 532, 523]

    def appStarted(self):
        self.optimized = 'xG'
        self.results = dict()

        self.sidebar = 300
        self.fieldWidth = self.width - self.sidebar
        self.fieldHeight = self.height * 3/4
        self.topBorder = self.fieldWidth / 6
        self.horizBorder = self.fieldWidth / 10
        self.field = (
            (self.horizBorder * 1.7, self.topBorder),
            (self.fieldWidth - self.horizBorder * 1.7, self.topBorder),
            (self.fieldWidth - self.horizBorder, self.topBorder + self.fieldHeight),
            (self.horizBorder, self.topBorder + self.fieldHeight)
        )
        self.players = self.app.fpl.players
        self.playerImages = self.app.playerImages

        self.setUp()

    optimizables = [
        'points', 'ict', 'xG', 'xA'
    ]

    def setUp(self):
        if(self.optimized not in self.results):
            self.opt = FPLOptimizer(self.optimized, self.app.fpl)
            self.bestTeams = dict()
            for f in self.formations:
                team = self.opt.getOptimalTeam(f)
                if(team):
                    self.bestTeams[f] = team
            self.displayedTeam = max(self.bestTeams.values(), key=lambda t: t[0].optimizable)
            print(self.displayedTeam)
            self.results[self.optimized] = self.displayedTeam
        else:
            self.displayedTeam = self.results[self.optimized]
            
        self.getTeam()
        self.setUpIcons()
        self.setOptimizeButtons()

    def setOptimizeButtons(self):
        self.optButtons = []
        y = self.height//17
        for r in range(2):
            x = self.fieldWidth + self.horizBorder
            y += self.height//14
            for c in range(2):
                text = self.optimizables[r * 2 + c]
                if(text==self.optimized): color='yellow'
                else: color='white'
                b = Button(x, y, self.horizBorder * 1.5, self.horizBorder//1.5,
                    text=self.optimizables[r * 2 + c], font=f'Monaco {self.width//50} bold',
                    color=color)
                self.optButtons.append(b)
                x += self.horizBorder * 1.6


    def getTeam(self):
        self.starters = [[], [], [], []]
        self.bench = []
        for element in self.displayedTeam[0].players:
            pos = element['posClass']
            ID = element.id
            if(pos == 'GKP'):
                self.starters[3].append(ID)
            elif(pos == 'DEF'):
                self.starters[2].append(ID)
            elif(pos == 'MID'):
                self.starters[1].append(ID)
            elif(pos == 'FWD'):
                self.starters[0].append(ID)
        for element in self.displayedTeam[1]:
            self.bench.append(element.id)

    def setUpIcons(self):
        self.icons = []
        vertPoints = self.midpointFinder(self.topBorder * 1.8, 
            self.topBorder + self.fieldHeight, 2, True)
        for i in range(4):
            y = vertPoints[i]
            if(len(self.starters[i]) >= 5):
                n, include, border = len(self.starters[i]) - 2, True, self.horizBorder * 1.5   
            else:
                n, include, border = len(self.starters[i]), False, self.horizBorder
            horizPoints = self.midpointFinder(border,
                self.fieldWidth - border, n, include)
            for c in range(len(self.starters[i])):
                ID = self.starters[i][c]
                x = horizPoints[c]
                self.icons.append(PlayerIcon(ID, self.players[ID], x, y, 
                    self.scaleImage(self.playerImages[ID], 1/3) ))
        
        y = self.topBorder * 4.5
        dy = self.topBorder * 1.2
        dx = self.sidebar // 2.5
        for r in range(2):
            x = self.fieldWidth + self.sidebar / 4
            for c in range(2):
                ID = self.bench[r * 2 + c]
                self.icons.append(PlayerIcon(ID, self.players[ID], x, y,
                    self.scaleImage(self.playerImages[ID], 1/3)))
                x += dx
            y += dy

    @staticmethod
    def midpointFinder(a, b, midpoints, inclusive):
        # returns list of midpoints between a & b
        midpointList = [a] if inclusive else []
        for i in range(1, midpoints + 1):
            mid = int(a + (b - a) * i / (midpoints + 1))
            midpointList.append(mid)
        if(inclusive):
            midpointList.append(b)
        return midpointList

    def drawTeam(self, canvas):
        for icon in self.icons:
            icon.draw(canvas)

    def mousePressed(self, event):
        for button in self.optButtons:
            if(button.wasClicked(event)):
                self.optimized = button.text
                self.setUp()

    def drawSidebar(self, canvas):
        canvas.create_text(self.fieldWidth + self.sidebar/2.2, self.height//15, 
            text='Optimize By:', font=f'Futura {self.sidebar//12} bold', fill='white')
        for button in self.optButtons:
            button.draw(canvas)
        
        y = self.height//3.5
        canvas.create_text(self.fieldWidth, y + self.height//15, text='Team\nStats',
            font=f'Futura {self.sidebar//10} bold', fill='white')
        for stat in self.optimizables:
            value = round(sum(player[stat] for player in self.displayedTeam[0].players), 2)
            canvas.create_text(self.fieldWidth + self.horizBorder * 1.1, y,
                text=f'{stat}:' + (7 -len(stat)) * ' ' + f'{value}', anchor='w',
                font=f'Monaco {self.sidebar//15}', fill='white')
            y += self.height//25

        canvas.create_text(self.fieldWidth + self.sidebar/2.2, self.height//2,
            text='Substitutes', font=f'Futura {self.sidebar//8} bold', fill='white')

    def keyPressed(self, event):
        if(event.key == 'q'):
            self.app.setActiveMode(self.app.team)

    def redrawAll(self, canvas):
        canvas.create_rectangle(0, 0, self.width, self.height, 
            fill=self.app.bgColor)
        
        canvas.create_text(self.fieldWidth//2, self.topBorder//2, 
            text='AI Generated Team', fill='white', font=f'Futura {self.width//20} bold')
        
        canvas.create_polygon(self.field, fill='green', outline='white', width=5)
        self.drawTeam(canvas)

        self.drawSidebar(canvas)

# all videos are taken from and are property of the NBC Sports Youtube Channel
class HighlightWatcher(Mode):
    def __init__(self, highlight, player):
        super().__init__()
        self.highlight = highlight
        self.player = player
        print(self.highlight)

    def appStarted(self):
        self.downloadVideo()
        self.vid = cv2.VideoCapture('temp.mp4')
        self.vid.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.app.timerDelay = 50
        self.imgW, self.imgH = 640, 360
        self.paused = False
        self.frame = None
        self.drawEdges = False
        
        self.title = self.highlight[0]['title']
        self.title = self.title[:self.title.find('|')-1]

        self.bS = self.width//12
        self.bY = self.height - (self.height - self.imgH)//4
        self.pause = Button(self.width//2, self.bY, self.bS, self.bS, text=None, font=None)
        self.fwd = Button(self.width//2 + self.bS*1.5,self.bY, self.bS, self.bS, text=None, font=None)
        self.bwd = Button(self.width//2 - self.bS*1.5, self.bY, self.bS, self.bS, text=None, font=None)

    def downloadVideo(self):
        stream = self.highlight[1].streams[0]
        filePath = self.highlight[0]['title'] + '.mp4'
        stream.download(quiet=False)
        os.rename(filePath, 'temp.mp4')

    def timerFired(self):
        if(not self.paused):
            for i in range(2):
                ret, frame = self.vid.read()
            if(ret):
                '''lower_green = np.array([40,40, 40])
                upper_green = np.array([70, 255, 255])
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                mask = cv2.inRange(hsv, lower_green, upper_green)
                frame = cv2.bitwise_and(frame, frame, mask=mask)
                rgbFrame = cv2.cvtColor(frame, cv2.COLOR_HSV2RGB)'''
                edges = cv2.Canny(frame, 200, 300)

                rgbFrame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                if(self.drawEdges):
                    self.frame = PIL.Image.fromarray(edges)
                else:
                    self.frame = PIL.Image.fromarray(rgbFrame)
            else:
                self.paused = True

    def keyPressed(self, event):
        if(event.key == 'q'):
            del self.vid
            os.remove('temp.mp4')
            self.app.timerDelay = 1000
            self.app.setActiveMode(self.app.gwMode)
        elif(event.key == 'Space'):
            if(not self.vid.read()[0]):
                self.vid.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.paused = not self.paused
        elif(event.key == 'Left'):
            currentFrame = self.vid.get(cv2.CAP_PROP_POS_FRAMES)
            newFrame = max(0, currentFrame - 150)
            self.vid.set(cv2.CAP_PROP_POS_FRAMES, newFrame)
        elif(event.key == 'Right'):
            currentFrame = self.vid.get(cv2.CAP_PROP_POS_FRAMES)
            maxFrame = self.vid.get(cv2.CAP_PROP_FRAME_COUNT)
            newFrame = min(maxFrame, currentFrame + 150)
            self.vid.set(cv2.CAP_PROP_POS_FRAMES, newFrame)
        elif(event.key == 'g'):
            self.drawEdges = not self.drawEdges
            self.timerFired()

    def mousePressed(self, event):
        if(self.pause.wasClicked(event)):
            self.paused = not self.paused
        elif(self.fwd.wasClicked(event)):
            currentFrame = self.vid.get(cv2.CAP_PROP_POS_FRAMES)
            maxFrame = self.vid.get(cv2.CAP_PROP_FRAME_COUNT)
            newFrame = min(maxFrame, currentFrame + 150)
            self.vid.set(cv2.CAP_PROP_POS_FRAMES, newFrame)
        elif(self.bwd.wasClicked(event)):
            currentFrame = self.vid.get(cv2.CAP_PROP_POS_FRAMES)
            newFrame = max(0, currentFrame - 150)
            self.vid.set(cv2.CAP_PROP_POS_FRAMES, newFrame)

    def redrawAll(self, canvas):
        canvas.create_rectangle(0, 0, self.width, self.height, fill=self.app.bgColor)
        canvas.create_text(self.width//2, (self.height-self.imgH)/4, text=self.title, 
            font=f'Futura {self.width//45} bold', fill='white')
        if(self.frame):
            self.pause.draw(canvas)
            bX = self.width//2 - self.bS*1.5
            canvas.create_polygon(
                (bX-self.bS/2, self.bY),
                (bX+self.bS/2, self.bY-self.bS/2),
                (bX+self.bS/2, self.bY+self.bS/2),
                fill='white', width=5
            )
            bX = self.width//2 + self.bS*1.5
            canvas.create_polygon(
                (bX+self.bS/2, self.bY),
                (bX-self.bS/2, self.bY-self.bS/2),
                (bX-self.bS/2, self.bY+self.bS/2),
                fill='white', width=5
            )
            canvas.create_rectangle(self.width/2-self.imgW/2, self.height/2-self.imgH/2, 
                self.width/2+self.imgW/2, self.height/2+self.imgH/2, fill=None,
                outline='black', width=20)
            canvas.create_image(self.width//2, self.height//2, 
                image=ImageTk.PhotoImage(self.frame))

def main():
    runFPLApp()

if(__name__ == '__main__'):
    main()