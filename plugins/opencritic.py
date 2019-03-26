import requests
import datetime
import fuzzywuzzy

from fuzzywuzzy import process
from cloudbot import hook

url = 'https://api.opencritic.com/api/game/'
headers = {
    'content-type': "application/json",
    'cache-control': "no-cache"
}
platformList = {
    ('switch', 'nintendo', 'nintendo switch'): '32',
    ('sony', 'playstation', 'playstation 4', 'ps4', 'psn'): '6',
    ('microsoft', 'ms', 'xbox', 'xbox one', 'xbox 1', 'xb1', 'xbl'): '7',
    ('windows', 'pc'): '27',
    ('3ds', 'nintendo 3ds'): '36',
    ('vive', 'htc', 'htc vive'): '30',
    ('rift', 'oculus', 'oculus rift'): '29',
    ('vr', 'hmd'): '29,30',
    ('vita', 'ps vita', 'psp'): '33'
}


def platformCategory(text):
    platformId = ''

    for platform, id in platformList.items():
        if text.lower() in platform:
            platformId = id

    if len(platformId) == 0:
        platformId += '6,7,27,29,30,32,33,36'

    return platformId


@hook.command('oc')
def oc(text):
<<<<<<< HEAD
    searchUrl = url + 'search'
    scoreUrl = url + 'score'
    dateUrl = url + 'filter'
    games = []

    searchQuery = {
        'criteria': text
    }

    response = requests.request(
        "GET", searchUrl, headers=headers, params=searchQuery).json()
=======
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
>>>>>>> upstream/master

    choices = [item['name'] for item in response]
    best = process.extract(text,choices, limit=1)[0][0]
        
    for item in response:
        if item['name'] == best:
            gameID = item['id']
            gameTitle = item['name']
<<<<<<< HEAD
            gameUrl = 'http://opencritic.com/game/' + \
                str(gameId) + '/' + \
                re.sub('[^0-9a-zA-Z]+', '-', item['name']).lower()

    games.append(gameId)

    scoreQuery = {
        'id': gameId
=======
            gameLink = 'http://opencritic.com/game/' + str(gameID) + '/'

    scoreQuery = {
    'id': gameID
>>>>>>> upstream/master
    }
    scoreResponse = requests.request(
        "GET", scoreUrl, headers=headers, params=scoreQuery).json()

<<<<<<< HEAD
    dateQuery = '{"ids": ' + str(games) + ', "orderBy": "timeAscending"}'
    gameDate = requests.post(dateUrl, headers=headers, data=dateQuery).json()[
        0]['releaseDate'][:10]

    try:
        gameScore = round(float(scoreResponse['score']))
=======
    response = requests.request("GET", scoreURL, headers = headers, params = scoreQuery).json()

    try:
        gameScore = round(float(response['score']))
>>>>>>> upstream/master
    except:
        return '\x02{}\x02 releases on {}.'.format(gameTitle, gameDate)
    else:
<<<<<<< HEAD
        return '\x02{}\x02 - \x02Score:\x02 {} - {}'.format(gameTitle, gameScore, gameUrl)


@hook.command('octop')
def octop(text):
    searchUrl = url + 'filter'
    output = []
    startDate = datetime.datetime.now().year

    data = '{"Platforms": [' + platformCategory(text) + '], "orderBy": "score", "limit": 5, "includeOnlyBase": true, "startDate": "' + str(
        startDate) + '-1-1", "endDate": "' + str(startDate) + '-12-31", "minTime": true}'

    response = requests.post(searchUrl, headers=headers, data=data)

    for i in response.json():
        output.append('\x02{}\x02: {}'.format(
            i['name'], round(float(i['score']))))

    return ', '.join(output)


@hook.command('ocup')
def ocup(text):
    searchUrl = url + 'filter'
    output = []
    startDate = datetime.datetime.now().strftime("%Y-%-m-%-d")

    data = '{"Platforms": [' + platformCategory(text) + '], "orderBy": "timeAscending", "limit": 5, "includeOnlyBase": true, "startDate": "' + \
        str(startDate) + '", "minTime": true}'

    response = requests.post(searchUrl, headers=headers, data=data)

    output = []

    for i in response.json():
        output.append('\x02{}\x02: {}'.format(
            i['name'], i['releaseDate'][:10]))
=======
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
>>>>>>> upstream/master

    return ', '.join(output)

