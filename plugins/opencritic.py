import requests
import datetime
import re
import fuzzywuzzy

from fuzzywuzzy import process
from cloudbot import hook

url = 'https://api.opencritic.com/api/game/'
headers = {
    'content-type': "application/json",
    'cache-control': "no-cache"
}

@hook.command('oc')
def oc(text):
    searchUrl = url + 'search'
    scoreUrl = url + 'score'

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

    scoreQuery = {
        'id': gameId
    }

    response = requests.request(
        "GET", scoreUrl, headers=headers, params=scoreQuery).json()

    try:
        gameScore = round(float(response['score']))
    except:
        return '\x02{}\x02 does not have an average score yet.'.format(gameTitle)
    else:
        return '\x02{}\x02 - \x02Score:\x02 {} - {}'.format(gameTitle, gameScore, gameUrl)

@hook.command('octop')
def octop(text):
    searchUrl = url + 'filter'
    output = []
    startDate = datetime.datetime.now().year

    if len(text) == 0:
        platformCategory = '6,7,27,29,30,32,33,36'
    elif text.lower() in {'switch', 'nintendo', 'nintendo switch'}:
        platformCategory = '32'
    elif text.lower() in {'sony', 'playstation', 'playstation 4', 'ps4', 'psn'}:
        platformCategory = '6'
    elif text.lower() in {'microsoft', 'ms', 'xbox', 'xbox one', 'xbox 1', 'xb1', 'xbl'}:
        platformCategory = '7'
    elif text.lower() in {'windows', 'pc'}:
        platformCategory = '27'
    elif text.lower() in {'3ds'}:
        platformCategory = '36'
    elif text.lower() in {'vive', 'htc', 'htc vive'}:
        platformCategory = '30'
    elif text.lower() in {'rift', 'oculus', 'oculus rift'}:
        platformCategory = '29'
    elif text.lower() in {'vr'}:
        platformCategory = '29,30'
    elif text.lower() in {'vita', 'ps vita', 'psp'}:
        platformCategory = '33'

    data = '{"Platforms": [' + platformCategory + '], "orderBy": "score", "limit": 5, "includeOnlyBase": true, "startDate": "' + str(startDate) + '-1-1", "endDate": "' + str(startDate) + '-12-31", "minTime": true}'

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

    if len(text) == 0:
        platformCategory = '6,7,27,29,30,32,33,36'
    elif text.lower() in {'switch', 'nintendo', 'nintendo switch'}:
        platformCategory = '32'
    elif text.lower() in {'sony', 'playstation', 'playstation 4', 'ps4', 'psn'}:
        platformCategory = '6'
    elif text.lower() in {'microsoft', 'ms', 'xbox', 'xbox one', 'xbox 1', 'xb1', 'xbl'}:
        platformCategory = '7'
    elif text.lower() in {'windows', 'pc'}:
        platformCategory = '27'
    elif text.lower() in {'3ds'}:
        platformCategory = '36'
    elif text.lower() in {'vive', 'htc', 'htc vive'}:
        platformCategory = '30'
    elif text.lower() in {'rift', 'oculus', 'oculus rift'}:
        platformCategory = '29'
    elif text.lower() in {'vr'}:
        platformCategory = '29,30'
    elif text.lower() in {'vita', 'ps vita', 'psp'}:
        platformCategory = '33'

    data = '{"Platforms": [' + platformCategory + '], "orderBy": "timeAscending", "limit": 5, "includeOnlyBase": true, "startDate": "' + str(startDate) + '", "minTime": true}'

    response = requests.post(searchUrl, headers=headers, data=data)

    output = []

    for i in response.json():
        output.append('\x02{}\x02: {}'.format(
            i['name'], i['releaseDate'][:10]))

    return ', '.join(output)
