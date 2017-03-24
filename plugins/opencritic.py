import requests
import math
import fuzzywuzzy
from fuzzywuzzy import process

from cloudbot import hook

@hook.command('oc')
def oc(text):
    url = 'http://api.opencritic.com/api/'
    searchURL = url + 'game/search'
    scoreURL = url +  'game/score'

    headers = {
    'content-type': "application/x-www-form-urlencoded",
    'cache-control': "no-cache"
    }

    searchQuery = {
    'criteria': text
    }
  
    response = requests.request("GET", searchURL, headers = headers, params = searchQuery).json()

    choices = [item['name'] for item in response]
    best = process.extract(text,choices, limit=1)[0][0]
        
    for item in response:
        if item['name'] == best:
            gameID = item['id']
            gameTitle = item['name']
            gameLink = 'http://opencritic.com/game/' + str(gameID) + '/'

    scoreQuery = {
    'id': gameID
    }

    response = requests.request("GET", scoreURL, headers = headers, params = scoreQuery).json()

    try:
        gameScore = math.ceil(float(response['score']))
    except:
        return '\x02{}\x02 does not have an average score yet.'.format(gameTitle)
    else:
        return '\x02{}\x02 - \x02Score:\x02 {} - {}'.format(gameTitle, gameScore, gameLink)
