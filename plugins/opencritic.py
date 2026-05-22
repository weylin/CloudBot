import requests
import datetime
import re
import fuzzywuzzy
import pickle
import os.path

from fuzzywuzzy import process
from cloudbot import hook

url = 'https://opencritic-api.p.rapidapi.com/'
headers = {
    'content-type': "application/json",
    'x-rapidapi-host': "opencritic-api.p.rapidapi.com"
}
api_key = None


@hook.on_start()
def load_key(bot):
    global api_key
    api_key = bot.config.get("api_keys", {}).get("opencritic")
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
def oc(text, bot):
    searchUrl = url + 'game/search'
    scoreUrl = url + 'game/score'
    dateUrl = url + 'game/filter'
    games = []

    local_headers = headers.copy()
    if api_key:
        local_headers['x-rapidapi-key'] = api_key

    searchQuery = {

        'criteria': text
    }

    resp = requests.request(
        "GET", searchUrl, headers=local_headers, params=searchQuery)
    
    if resp.status_code == 403 or resp.status_code == 401:
        return "OpenCritic API key is missing or invalid. Please check the bot configuration."

    response = resp.json()

    if isinstance(response, dict) and "message" in response:
        return "OpenCritic API Error: {}".format(response["message"])

    if not response:
        return "No games found for '{}'.".format(text)

    choices = [item['name'] for item in response]
    bestChoice = process.extract(text, choices, limit=1)[0][0]

    gameId = None
    for item in response:
        if item['name'] == bestChoice:
            gameId = item['id']
            gameTitle = item['name']
            break

    if gameId is None:
        return "Could not find a matching game for '{}'.".format(text)

    # Fetch full game details (including score and date) in one call
    detail_url = url + 'game/{}'.format(gameId)
    detail_resp = requests.get(detail_url, headers=local_headers)
    
    if detail_resp.status_code != 200:
        return "Error fetching details for '{}' (HTTP {}).".format(gameTitle, detail_resp.status_code)

    game_data = detail_resp.json()
    
    gameUrl = game_data.get('url', 'http://opencritic.com/game/{}'.format(gameId))
    gameDate = game_data.get('firstReleaseDate', '????-??-??')[:10]

    try:
        score = game_data.get('topCriticScore', -1)
        if score == -1:
            return '\x02{}\x02 releases on {}.'.format(gameTitle, gameDate)
        
        gameScore = round(float(score))
    except (TypeError, ValueError):
        return '\x02{}\x02 releases on {}.'.format(gameTitle, gameDate)
    else:
        return '\x02{}\x02 - \x02Score:\x02 {} - {}'.format(gameTitle, gameScore, gameUrl)


@hook.command('octop')
def octop(text, bot):
    searchUrl = url + 'game/filter'
    output = []

    local_headers = headers.copy()
    if api_key:
        local_headers['x-rapidapi-key'] = api_key

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

    resp = requests.post(searchUrl, headers=local_headers, data=data)
    
    if resp.status_code == 403 or resp.status_code == 401:
        return "OpenCritic API key is missing or invalid."

    response = resp.json()

    if isinstance(response, dict) and "message" in response:
        return "OpenCritic API Error: {}".format(response["message"])

    if not isinstance(response, list):
        return "Unexpected response from OpenCritic API."

    for i in response:
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
def ocup(text, bot):
    searchUrl = url + 'game/filter'
    output = []
    startDate = datetime.datetime.now().strftime("%Y-%m-%d")

    local_headers = headers.copy()
    if api_key:
        local_headers['x-rapidapi-key'] = api_key

    data = '{"Platforms": [' + platformCategory(text) + '], "orderBy": "timeAscending", "limit": 5, "includeOnlyBase": true, "startDate": "' + \
        str(startDate) + '", "minTime": true}'

    resp = requests.post(searchUrl, headers=local_headers, data=data)
    
    if resp.status_code == 403 or resp.status_code == 401:
        return "OpenCritic API key is missing or invalid."

    response = resp.json()

    if isinstance(response, dict) and "message" in response:
        return "OpenCritic API Error: {}".format(response["message"])

    if not isinstance(response, list):
        return "Unexpected response from OpenCritic API."

    output = []

    for i in response:
        output.append('\x02{}\x02: {}'.format(
            i['name'], i['releaseDate'][:10]))

    return ', '.join(output)
