from io import BytesIO
import datetime
import glob
import os
import pickle
import platform
from random import randint
import stat
import sys
from time import sleep
import traceback
import urllib
import urllib.parse
from zipfile import ZipFile

from bs4 import BeautifulSoup
from pyvirtualdisplay import Display
import requests
from dateutil.relativedelta import relativedelta, FR
from selenium import webdriver

from cloudbot import hook
from cloudbot.event import EventType
from . import destiny_manifest


BASE_URL = 'https://www.bungie.net/Platform/'
CLASS_TYPES = {0: 'Titan ', 1: 'Hunter ', 2: 'Warlock ', 3: ''}

@hook.on_start()
def load_cache(bot):
    '''Load in our pickle manifest and the Headers'''

    # Set the API key
    global HEADERS
    HEADERS = {'X-API-Key': bot.config.get('api_keys', {}).get('destiny', None)}

    # Get the manifest pickle if it exists
    pickles = glob.glob('destiny_manifest_*.pickle')

    # If more than one pickle, only keep latest one
    if len(pickles) == 1:
        filename = pickles[0]
    elif len(pickles) > 1:
        os.remove(sorted(pickles)[0])
        filename = sorted(pickles)[-1]
    else:
        api_key = bot.config.get('api_keys', {}).get('destiny', None)
        filename = destiny_manifest.gen_manifest_pickle(api_key)

    try:
        with open(filename, 'rb') as f:
            global MANIFEST
            MANIFEST = pickle.load(f)
    except EOFError:
        MANIFEST = {}

@hook.event([EventType.message, EventType.action], singlethread=True)
def discord_tracker(event, db, conn):
    if event.nick == 'DTG' and 'Command sent from Discord by' in event.content:
        global DISCORD_USER
        DISCORD_USER = event.content[event.content.find("by") + 3: -1]

@hook.periodic(24 * 60 * 60, initial_interval=30)
def check_manifest(bot):
    api_key = bot.config.get('api_keys', {}).get('destiny', None)
    conn = bot.connections["DTG"]
    current = False
    try:
        current = destiny_manifest.is_manifest_current(api_key)
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback,
                          limit=2, file=sys.stdout)
        conn.message("#DTGCoding", "Error! {}".format(e))

    if not current:
        try:
            result = destiny_manifest.gen_manifest_pickle(api_key)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback,
                                      limit=2, file=sys.stdout)
            conn.message("#DTGCoding", "Manifest error: {}".format(e))
        else:
            conn.message("#DTGCoding", result)
    else:
        print("Destiny manifest is current!")

@hook.command('item')
def item_search(text, bot):
    '''
    Expects the text to be a valid object in the Destiny database
    Returns the item's name and description.
    TODO: Implement error checking
    '''
    item = urllib.parse.quote(text.strip())
    item_query = '{}Destiny2/Armory/Search/DestinyInventoryItemDefinition/{}'.format(BASE_URL, item)
    response = requests.get(item_query, headers=HEADERS).json()

    if response['ErrorCode'] == 1:
        item_results = response['Response']['results']['results']
    else:
        return 'Error: {}'.format(response['Message'])

    output = []
    for item in item_results:
        item_hash = item['hash']
        result = MANIFEST['DestinyInventoryItemDefinition'][item_hash]

        output.append('\x02{}\x02 ({}{}) - \x1D{}\x1D - http://db.destinytracker.com/d2/en/items/{}'.format(
            result['displayProperties']['name'],
            CLASS_TYPES[result['classType']],
            result['itemTypeAndTierDisplayName'],
            result['displayProperties'].get('description', 'Item has no description.'),
            result['hash']
        ))
    return output[:3]

# Name: Xûr, vendor hash: 2190858386, milestone hash: 534869653
@hook.command('xur')
def xur(text, bot):
    # reset happens at 9am UTC, so subtract that to simplify the math
    now = datetime.datetime.utcnow() - datetime.timedelta(hours=9)

    # xur is available from friday's reset until sunday's reset, i.e. friday (4) and saturday (5)
    if now.weekday() not in [4, 5] or not 'last' in text.lower():
        xursday_diff = 4 - now.weekday()
        if xursday_diff < -1: # if past saturday, bump to next week
            xursday_diff += 7

        xursday = (now + datetime.timedelta(days=xursday_diff)).replace(hour=0, minute=0, second=0, microsecond=0)
        time_to_xursday = xursday - now

        s = time_to_xursday.seconds
        h, s = divmod(s, 3600)
        m, s = divmod(s, 60)

        output = []

        if time_to_xursday.days > 0:
            output.append('{} days'.format(time_to_xursday.days))

        if h: output.append('{} hours'.format(h))
        if m: output.append('{} minutes'.format(m))
        if s: output.append('{} seconds'.format(s))

        return '\x02Xûr will return in\x02 {}'.format(', '.join(output))

    # Build URL
    recent_fri = datetime.datetime.now() + relativedelta(weekday=FR(-1))
    page_url = 'https://whereisxur.com/xur-location-destiny-2-{}/'.format(recent_fri.strftime('%m-%-d-%Y'))

    # Get page
    page = urllib.request.urlopen(page_url)
    soup = BeautifulSoup(page, 'html.parser')

    # Get the location
    loc = soup.find('h4', attrs={'class': 'title'}).text
    location = ' '.join(loc.split()[:-1])

    # Get the items
    item_row = soup.find('div', attrs={'class': 'et_pb_row_5'})
    xur_items = []

    for child in item_row.children:
        name = child.find('h4')
        if name != -1:
            xur_items.append(name.text)

    output = "\x02Xûr\x02 -- Location: {}; Items: {}".format(location, ", ".join(xur_items))
    return output

@hook.command('nightfall', 'nf')
def nightfall(text, bot):
    milestones_url = '{}Destiny2/Milestones/'.format(BASE_URL)
    response = requests.get(milestones_url, headers=HEADERS).json()

    if response['ErrorCode'] == 1:
        nightfall = response['Response']['2171429505']
    else:
        return 'Error: {}'.format(response['Message'])

    nightfall_activity_hash = nightfall["availableQuests"][0]["activity"]["activityHash"]
    nightfall_name = MANIFEST['DestinyActivityDefinition'][nightfall_activity_hash]['displayProperties']['name']
    nightfall_desc = MANIFEST['DestinyActivityDefinition'][nightfall_activity_hash]['displayProperties']['description']

    api_modifiers = nightfall["availableQuests"][0]["activity"]["modifierHashes"]
    modifiers = []
    for modifier in api_modifiers:
        modifiers.append(MANIFEST['DestinyActivityModifierDefinition'][modifier]['displayProperties']['name'])

    api_challenges = nightfall['availableQuests'][0]['challenges']
    challenges = []
    for challenge in api_challenges:
        challenges.append(MANIFEST['DestinyObjectiveDefinition'][challenge['objectiveHash']]['displayProperties']['name'])

    output = '\x02{}\x02 - \x1D{}\x1D \x02Modifiers:\x02 {} \x02Challenges:\x02 {}'.format(
                                                        nightfall_name,
                                                        nightfall_desc,
                                                        ', '.join(modifiers),
                                                        ', '.join(challenges[:2])
                                                    )
    return output

def get_chromedriver():
    driver = glob.glob('chromedriver')
    sys_plat = platform.system()

    if sys_plat == 'Linux':
        target = 'https://chromedriver.storage.googleapis.com/2.33/chromedriver_mac64.zip'
    elif sys_plat == 'Darwin':
        target = 'https://chromedriver.storage.googleapis.com/2.33/chromedriver_mac64.zip'
    elif sys_plat == 'Windows':
        target = 'https://chromedriver.storage.googleapis.com/2.33/chromedriver_win32.zip'
    else:
        raise Exception('Invalid platform')

    if len(driver) == 1:
        pass
    elif len(driver) > 1:
        raise Exception('Too many chromedrivers!')
    else:
        request = get(target)
        zip_file = ZipFile(BytesIO(request.content))
        zip_file.extractall()
        zip_file.close()

        # Permissions hackery
        st = os.stat('chromedriver')
        os.chmod('chromedriver', st.st_mode | 0o111)

# TODO: Unfinished
@hook.command('trials')
def trials(text, bot):
    if 'flush' in text.lower(): CACHE['trials'] = {}
    if 'last' in text.lower():
        try:
            return CACHE['last_trials']['output']
        except KeyError:
            return 'Unavailable.'
    if 'trials' in CACHE:
        if 'expiration' in CACHE['trials']:
            if datetime.datetime.utcnow() < string_to_datetime(CACHE['trials']['expiration']):
                return CACHE['trials']['output']
        if 'nextStart' in CACHE['trials']:
            if datetime.datetime.utcnow() < string_to_datetime(CACHE['trials']['nextStart']):
                time_to_trials = string_to_datetime(CACHE['trials']['nextStart']) - datetime.datetime.utcnow()
                s = time_to_trials.seconds
                h, s = divmod(s, 3600)
                m, s = divmod(s, 60)
                output = []
                if time_to_trials.days > 0:
                    output.append('{} days'.format(time_to_trials.days))
                if h: output.append('{} hours'.format(h))
                if m: output.append('{} minutes'.format(m))
                if s: output.append('{} seconds'.format(s))
                return '\x02Trials of Osiris will return in\x02 {}'.format(', '.join(output))

    # Get ChromeDriver if not present
    get_chromedriver()

    # Initialize display and driver
    display = Display(visible=0, size=(800, 600))
    display.start()
    browser = webdriver.Chrome("chromedriver")

    # Get the page
    url = "https://trials.report/"
    browser.get(url) # navigate to the page
    sleep(randint(2,3)) # sleep to make sure we get it
    page = browser.execute_script("return document.body.innerHTML") # returns the inner HTML as a string

    # Parse for info
    soup = BeautifulSoup(page, 'html.parser')

    # Get the location
    loc = soup.find('h2', attrs={'class': 'card__title'}).text
    trials_map = loc.strip()

    # Shutdown display and driver
    display.stop()
    browser.quit()

    new_trials= {
        'expiration': advisors['status']['expirationDate'],
        'nextStart': datetime_to_string(string_to_datetime(advisors['status']['startDate']) + datetime.timedelta(days=7)),
        'output': '\x02Trials of Osiris:\x02 {}'.format(trials_map)
    }

    if 'trials' in CACHE and new_trials != CACHE['trials']:
        CACHE['last_trials'] = CACHE['trials']
    CACHE['trials'] = new_trials
    return new_trials['output']
