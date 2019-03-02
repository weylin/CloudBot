import requests
import datetime
import re
import fuzzywuzzy
from fuzzywuzzy import process

from cloudbot import hook

@hook.command('oc')
def oc(text):
    url = 'http://api.opencritic.com/api/'
    searchUrl = url + 'game/search'
    scoreUrl = url + 'game/score'

    headers = {
        'content-type':"application/x-www-form-urlencoded",
        'cache-control':"no-cache"
    }

    searchQuery = {
        'criteria':text
    }

    response = requests.request("GET", searchUrl, headers = headers, params = searchQuery).json()

    choices = [item['name'] for item in response]
    bestChoice = process.extract(text, choices, limit=1)[0][0]

    for item in response:
        if item['name'] == bestChoice:
            gameId = item['id']
            gameTitle = item['name']
            gameUrl = 'http://opencritic.com/game/' + str(gameId) + '/' + re.sub('[^0-9a-zA-Z]+', '-', item['name']).lower()

    scoreQuery = {
        'id':gameId
    }

    response = requests.request("GET", scoreUrl, headers = headers, params = scoreQuery).json()

    try: 
        gameScore = round(float(response['score']))
    except:
        return '\x02{}\x02 does not have an average score yet.'.format(gameTitle)
    else:
        return '\x02{}\x02 - \x02Score:\x02 {} - {}'.format(gameTitle, gameScore, gameUrl)
