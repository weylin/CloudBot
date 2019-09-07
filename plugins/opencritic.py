import requests
import datetime
import re
import fuzzywuzzy
import pickle
import os.path

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

knownPlatforms = {'switch', 'nintendo', 'nintendo switch',
                  'sony', 'playstation', 'playstation 4', 'ps4', 'psn',
                  'microsoft', 'ms', 'xbox', 'xbox one', 'xbox 1', 'xb1', 'xbl',
                  'windows', 'pc',
                  '3ds', 'nintendo 3ds',
                  'vive', 'htc', 'htc vive', 'rift', 'oculus', 'oculus rift', 'vr', 'hmd',
                  'vita', 'ps vita', 'psp'}


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
    searchUrl = url + 'search'
    scoreUrl = url + 'score'
    dateUrl = url + 'filter'
    games = []

    searchQuery = {
        'criteria': text
    }

    response = requests.request(
        "GET", searchUrl, headers=headers, params=searchQuery).json()

    choices = [item['name'] for item in response]
    bestChoice = process.extract(text, choices, limit=1)[0][0]

    for item in response:
        if item['name'] == bestChoice:
            gameId = item['id']
            gameTitle = item['name']
            gameUrl = 'http://opencritic.com/game/' + \
                str(gameId) + '/' + \
                re.sub('[^0-9a-zA-Z]+', '-', item['name']).lower()

    games.append(gameId)

    scoreQuery = {
        'id': gameId
    }
    scoreResponse = requests.request(
        "GET", scoreUrl, headers=headers, params=scoreQuery).json()

    dateQuery = '{"ids": ' + str(games) + ', "orderBy": "timeAscending"}'
    gameDate = requests.post(dateUrl, headers=headers, data=dateQuery).json()[
        0]['releaseDate'][:10]

    try:
        gameScore = round(float(scoreResponse['score']))
    except:
        return '\x02{}\x02 releases on {}.'.format(gameTitle, gameDate)
    else:
        return '\x02{}\x02 - \x02Score:\x02 {} - {}'.format(gameTitle, gameScore, gameUrl)


@hook.command('octop')
def octop(text):
    searchUrl = url + 'filter'
    output = []

    args = text.split(' ')

    if len(args[0]) == 0:
        text = ''
        startDate = datetime.datetime.now().year
    
    elif len(args) == 1:
        for arg in args:
            if arg in knownPlatforms:
                text = arg
                startDate = datetime.datetime.now().year
            else:
                startDate = arg
                text = ''

    elif len(args) == 2:
        for arg in args:
            if arg in knownPlatforms:
                text = arg
            else:
                startDate = arg

    else:
        return 'Stop arguing so much. (Limit 2 arguments, platform and/or year.)'

    data = '{"Platforms": [' + platformCategory(text) + '], "orderBy": "score", "limit": 5, "includeOnlyBase": true, "startDate": "' + str(
        startDate) + '-1-1", "endDate": "' + str(startDate) + '-12-31", "minTime": true}'

    response = requests.post(searchUrl, headers=headers, data=data)

    for i in response.json():
        output.append('\x02{}\x02: {}'.format(
            i['name'], round(float(i['score']))))
    
    if len(args[0]) == 0:
        if os.path.exists('OpenCritic.pkl'):
            octopReadFile = open('OpenCritic.pkl', 'rb')

            octopOld = pickle.load(octopReadFile)

            octopReadFile.close

            if octopOld == output:
                return ', '.join(output)
            else:
                octopWriteFile = open('OpenCritic.pkl', 'wb')

                pickle.dump(output, octopWriteFile)

                octopWriteFile.close
            
                return ', '.join(output)
        else:
            octopWriteFile = open('OpenCritic.pkl', 'wb')

            pickle.dump(output, octopWriteFile)

            octopWriteFile.close

            return ', '.join(output)
    else:
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

    return ', '.join(output)
