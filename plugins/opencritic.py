import requests
import datetime
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

knownPlatforms = {
    'switch', 'nintendo', 'nintendo switch',
    'sony', 'playstation', 'playstation 4', 'ps4', 'psn',
    'microsoft', 'ms', 'xbox', 'xbox one', 'xbox 1', 'xb1', 'xbl',
    'windows', 'pc',
    '3ds', 'nintendo 3ds',
    'vive', 'htc', 'htc vive', 'rift', 'oculus', 'oculus rift', 'vr', 'hmd',
    'vita', 'ps vita', 'psp'
}


def platformCategory(text):
    for platform, platform_id in platformList.items():
        if text.lower() in platform:
            return platform_id

    return '6,7,27,29,30,32,33,36'


def get_headers():
    local_headers = headers.copy()
    if api_key:
        local_headers['x-rapidapi-key'] = api_key
    return local_headers


@hook.command('oc')
def oc(text, bot):
    search_url = url + 'game/search'

    params = {'criteria': text}
    resp = requests.get(search_url, headers=get_headers(), params=params)

    if resp.status_code in (401, 403):
        return "OpenCritic API key is missing or invalid. Please check the bot configuration."

    try:
        response = resp.json()
    except ValueError:
        return "Error: Received non-JSON response from OpenCritic API."

    if isinstance(response, dict) and "message" in response:
        return "OpenCritic API Error: {}".format(response["message"])

    if not response:
        return "No games found for '{}'.".format(text)

    choices = [item['name'] for item in response]
    best_choice, _ = process.extractOne(text, choices)

    game_id = next((item['id'] for item in response if item['name'] == best_choice), None)

    if game_id is None:
        return "Could not find a matching game for '{}'.".format(text)

    # Fetch full game details
    detail_url = url + 'game/{}'.format(game_id)
    detail_resp = requests.get(detail_url, headers=get_headers())

    if detail_resp.status_code != 200:
        return "Error fetching details for '{}' (HTTP {}).".format(best_choice, detail_resp.status_code)

    try:
        game_data = detail_resp.json()
    except ValueError:
        return "Error: Received non-JSON response from OpenCritic API for game details."

    game_url = game_data.get('url', 'http://opencritic.com/game/{}'.format(game_id))
    game_date = game_data.get('firstReleaseDate', '????-??-??')[:10]

    score = game_data.get('topCriticScore', -1)
    if score == -1:
        return '\x02{}\x02 releases on {}.'.format(best_choice, game_date)

    try:
        game_score = round(float(score))
        return '\x02{}\x02 - \x02Score:\x02 {} - {}'.format(best_choice, game_score, game_url)
    except (TypeError, ValueError):
        return '\x02{}\x02 releases on {}.'.format(best_choice, game_date)


@hook.command('octop')
def octop(text, bot):
    filter_url = url + 'game/filter'
    output = []
    args = text.split()

    if not args:
        platform_text = ''
        start_year = datetime.datetime.now().year
    elif len(args) == 1:
        arg = args[0]
        if arg in knownPlatforms:
            platform_text = arg
            start_year = datetime.datetime.now().year
        else:
            platform_text = ''
            start_year = arg
    elif len(args) == 2:
        platform_text = next((arg for arg in args if arg in knownPlatforms), '')
        start_year = next((arg for arg in args if arg not in knownPlatforms), datetime.datetime.now().year)
    else:
        return 'Stop arguing so much. (Limit 2 arguments: platform and/or year.)'

    payload = {
        "Platforms": [int(i) if ',' not in i else [int(x) for x in i.split(',')] for i in [platformCategory(platform_text)]][0],
        "orderBy": "score",
        "limit": 5,
        "includeOnlyBase": True,
        "startDate": "{}-01-01".format(start_year),
        "endDate": "{}-12-31".format(start_year),
        "minTime": True
    }
    
    # Handle the flattened platform list correctly if platformCategory returns a comma-separated string
    platforms_raw = platformCategory(platform_text)
    platforms = [int(x) for x in platforms_raw.split(',')]
    payload["Platforms"] = platforms

    resp = requests.post(filter_url, headers=get_headers(), json=payload)
    if resp.status_code in (401, 403):
        return "OpenCritic API key is missing or invalid."

    try:
        response = resp.json()
    except ValueError:
        return "Error: Received non-JSON response from OpenCritic API."

    if isinstance(response, dict) and "message" in response:
        return "OpenCritic API Error: {}".format(response["message"])

    if not isinstance(response, list):
        return "Unexpected response from OpenCritic API."

    for i in response:
        try:
            output.append('\x02{}\x02: {}'.format(i['name'], round(float(i['score']))))
        except (KeyError, TypeError, ValueError):
            continue

    if not output:
        return "No highly-rated games found for the specified criteria."

    result = ', '.join(output)

    # Caching logic for default 'octop' (no args)
    if not args:
        cache_file = 'OpenCritic.pkl'
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'rb') as f:
                    cached_output = pickle.load(f)
                if cached_output == output:
                    return result

            with open(cache_file, 'wb') as f:
                pickle.dump(output, f)
        except (IOError, pickle.PickleError):
            pass  # Fail silently on cache errors

    return result


@hook.command('ocup')
def ocup(text, bot):
    filter_url = url + 'game/filter'
    start_date = datetime.datetime.now().strftime("%Y-%m-%d")

    platforms_raw = platformCategory(text)
    platforms = [int(x) for x in platforms_raw.split(',')]

    payload = {
        "Platforms": platforms,
        "orderBy": "timeAscending",
        "limit": 5,
        "includeOnlyBase": True,
        "startDate": start_date,
        "minTime": True
    }

    resp = requests.post(filter_url, headers=get_headers(), json=payload)

    if resp.status_code in (401, 403):
        return "OpenCritic API key is missing or invalid."

    try:
        response = resp.json()
    except ValueError:
        return "Error: Received non-JSON response from OpenCritic API."

    if isinstance(response, dict) and "message" in response:
        return "OpenCritic API Error: {}".format(response["message"])

    if not isinstance(response, list):
        return "Unexpected response from OpenCritic API."

    output = []
    for i in response:
        try:
            output.append('\x02{}\x02: {}'.format(i['name'], i['releaseDate'][:10]))
        except (KeyError, TypeError):
            continue

    if not output:
        return "No upcoming games found."

    return ', '.join(output)
