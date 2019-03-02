import requests
import datetime
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
        gameScore = round(float(response['score']))
    except:
        return '\x02{}\x02 does not have an average score yet.'.format(gameTitle)
    else:
        return '\x02{}\x02 - \x02Score:\x02 {} - {}'.format(gameTitle, gameScore, gameLink)

@hook.command('octop')
def octop(text):
    url = 'http://api.opencritic.com/api/game/filter'

    headers = {
    'content-type': "application/json",
    }

    data = '{"limit": 5, "orderBy": "score", "startDate": "2017-1-1"}'

    output = []

    response = requests.post(url, headers = headers, data = data)

    for i in response.json():
        output.append('\x02{}\x02: {}'.format(i['name'], round(float(i['score']))))

    return ', '.join(output)

@hook.command('ocup')
def ocup(text):
    url = 'http://api.opencritic.com/api/game/filter'

    if text.lower() in {'switch', 'nintendo', 'nintendo switch'}:
        text = '32'
    elif text.lower() in {'sony', 'playstation', 'playstation 4', 'ps4', 'psn'}:
        text = '6'
    elif text.lower() in {'microsoft', 'ms', 'xbox', 'xbox one', 'xbox 1', 'xb1', 'xbl'}:
        text = '7'
    elif text.lower() in {'windows', 'pc'}:
        text = '27'
    elif text.lower() in {'3ds'}:
        text = '36'
    elif text.lower() in {'vive', 'htc', 'htc vive'}:
        text = '30'
    elif text.lower() in {'rift', 'oculus', 'oculus rift'}:
        text = '29'
    elif text.lower() in {'vr'}:
        text = '29,30'
    elif text.lower() in {'vita', 'ps vita', 'psp'}:
        text = '33'
    
    startDate = datetime.datetime.now()
    
    headers = {
    'content-type': "application/json",
    }

    data = '{"Platforms": [' + text + '], "limit": 5, "orderBy": "timeAscending", "startDate": "' + str(startDate) + '-3-24", "minTime": true}'

    output = []

    response = requests.post(url, headers = headers, data = data)

    for i in response.json():
        output.append('\x02{}\x02: {}'.format(i['name'], i['releaseDate'][:10]))

    return ', '.join(output)

