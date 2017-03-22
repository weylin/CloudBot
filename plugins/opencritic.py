import requests
import math

from cloudbot import hook

@hook.command('oc')
def oc(text):
    url = 'http://api.opencritic.com/api/'
    gameURL = url + 'game'
    searchURL = url + 'game/search'
    scoreURL = url +  'game/score'

    headers = {
    'content-type': "application/x-www-form-urlencoded",
    'cache-control': "no-cache"
    }

    searchQuery = {
    'criteria': text
    }
  
    response = requests.request("GET", searchURL, headers = headers, params = searchQuery)

    gameID = response.json()[0]['id']
    gameTitle = response.json()[0]['name']
    gameLink = 'http://opencritic.com/game/' + str(gameID) + '/'

    scoreQuery = {
    'id': gameID
    }

    response = requests.request("GET", gameURL, headers = headers, params = scoreQuery)

    if response.json()['ready'] == True:
        response = requests.request("GET", scoreURL, headers = headers, params = scoreQuery)

        gameScore = math.ceil(float(response.json()['score']))

        return '\x02{}\x02 - \x02Score:\x02 {} - {}'.format(gameTitle, gameScore, gameLink)
    else:
        return '\x02{}\x02 has not yet been released.'.format(gameTitle)
