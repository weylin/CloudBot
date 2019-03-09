import requests
from cloudbot import hook

url = 'https://www.apexlegendsapi.com/api/v1/player'

@hook.on_start
def on_start(bot, db):
    global apexKey
    apexKey = bot.config.get('api_keys', {}).get('apex', None)

@hook.command('apex')
def apexLegend(text):

    # A new entry to config.json needs to be created under 'api_keys'
    # for this to work.
    header = {
    'authorization': apexKey
    }

    # Right now we default to the PC platform but this can be changed
    # in the future to allow for a second platform parameter to be
    # passed into the payload.
    payload = {
        'platform': 'pc',
        'name': text
    }

    request = requests.get(url, headers=header, params=payload).json()

    legendLevel = request['level']
    legendName = request['legends'][0]['name']
    legendData = request['legends'][0]['stats']

    # Create new Dict for each of the Dicts inside the stat List.
    output = {}
    for item in legendData:
        output.update(item)

    # Build the stat grouping for each banner on current Legend.
    statGroup = ', '.join('\x02{}\x02: {}'.format(stat.replace('_', ' ').title(), value) for stat, value in output.items()) 

    # Build the rest of the user information with the statGroup on the end.
    return '\x02{}\x02 - Level {}: \x02{}\x02 - {}'.format(text, legendLevel, legendName.replace('_', ' ').title(), statGroup) 
