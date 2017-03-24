import requests
import datetime

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
  
    response = requests.request("GET", searchURL, headers = headers, params = searchQuery)

    gameID = response.json()[0]['id']
    gameTitle = response.json()[0]['name']
    gameLink = 'http://opencritic.com/game/' + str(gameID) + '/'

    scoreQuery = {
    'id': gameID
    }

    response = requests.request("GET", scoreURL, headers = headers, params = scoreQuery)

    try:
        gameScore = round(float(response.json()['score']))
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
    return startDate

