import datetime
import glob
import json
import os
import pickle
import sys
import traceback
import urllib
import urllib.parse

from bs4 import BeautifulSoup
from feedparser import parse
import requests
from dateutil.relativedelta import relativedelta, FR

from cloudbot import hook
from cloudbot.event import EventType
from cloudbot.util.web import try_shorten
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
    api_key = HEADERS['X-API-Key']
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
def item_search(text):
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
def xur():
    # reset happens at 9am UTC, so subtract that to simplify the math
    now = datetime.datetime.utcnow() - datetime.timedelta(hours=9)

    # xur is available from friday's reset until sunday's reset, i.e. friday (4) and saturday (5)
    if now.weekday() not in [4, 5, 6, 0]:
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
def nightfall():
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

# Milestone hash: 3551755444
@hook.command('trials')
def trials():
    trials_info = requests.get('https://api.trialsofthenine.com/week/0/').json()

    if not trials_info['Status'] == 'Success':
        return 'Error fetching Trials info'

    status = False

    now = datetime.datetime.utcnow()
    begin = datetime.datetime.strptime(trials_info['Response']['startDate'],'%Y-%m-%d %H:%M:%S')
    end = datetime.datetime.strptime(trials_info['Response']['endDate'],'%Y-%m-%d %H:%M:%S')

    if begin < now < end:
        status = True

    if not status:
        return '\x02Trials of the Nine:\x02 Unavailable.'

    if trials_info['Status'] == 'Success':
        trials_map = trials_info['Response']['name']
        trials_mode = trials_info['Response']['mode']

    return '\x02Trials of the Nine:\x02 {} on {}'.format(trials_mode, trials_map)

@hook.command('weekly')
def weekly():
    result = requests.get('{}Destiny2/Milestones/'.format(BASE_URL), headers=HEADERS).json()

    if result['ErrorCode'] != 1:
        return "Error fetching weekly info :("

    # Get raid challenge
    raid_challenges = result['Response']['3660836525']['availableQuests'][0]['challenges']
    raid_challenge = ""
    for challenge in raid_challenges:
        if challenge['activityHash'] != 3879860661:
            if challenge['objectiveHash'] not in [1004127727, 1490146686]:
                raid_challenge = MANIFEST['DestinyObjectiveDefinition'][challenge['objectiveHash']]['displayProperties']['name']

    # Get flashpoint
    flashpoint_info = result['Response']['463010297']['availableQuests'][0]['questItemHash']
    flashpoint_location = MANIFEST['DestinyInventoryItemDefinition'][flashpoint_info]['displayProperties']['name']

    # Get meditations info
    meditations = result['Response']['3245985898']['availableQuests']

    meditation_locations = []
    for quest in meditations:
        location_info = MANIFEST['DestinyActivityDefinition'][quest['questItemHash']]['displayProperties']['name'].split(':')

        try:
            location = location_info[1]
        except IndexError:
            location = location_info[0]

        meditation_locations.append(location.replace('"', ''))


    return "\x02Weekly activities:\x02 Leviathan Raid Challenge: {} || {} || Meditations: {}".format(raid_challenge, flashpoint_location, ",".join(meditation_locations))

@hook.command('clanweekly')
def clan_weekly(text):
    # Default to #DTG clan ID
    if not text:
        clan = 939927
    else:
        try:
            clan = int(text)
        except ValueError:
            return "Error: Invalid clan ID"

    # Get status of weekly clan engrams
    clan_query = '{}Destiny2/Clan/{}/WeeklyRewardState/'.format(BASE_URL, clan)
    response = requests.get(clan_query, headers=HEADERS).json()

    # Catch error
    if response['ErrorCode'] == 1:
        clan_results = response['Response']['rewards'][0]['entries']
    else:
        return 'Error: {}'.format(response['Message'])

    # Get the relevant data from the manifest
    milestone_rewards_def = MANIFEST['DestinyMilestoneDefinition'][4253138191]['rewards']['1064137897']['rewardEntries']

    # Build the output
    output = []
    earned_count = 0
    for reward_entry in clan_results:
        reward_hash = str(reward_entry['rewardEntryHash'])
        reward = milestone_rewards_def[reward_hash]
        reward_name = reward['displayProperties']['name']
        reward_earned = reward_entry['earned']
        if reward_entry['earned'] == True:
            earned_count += 1

        # Don't let avcables be lazy
        if reward_name == "Trials of the Nine" and reward_earned == False:
            result = "{} - Hey @avcables, go run Trials!".format(reward_name)
        else:
            result = "{} - Earned: {}".format(reward_name, reward_earned)
        output.append(result)

    if earned_count == 4:
        return "\x02Clan weekly rewards:\x02 Completed! Let them burn in your light!"
    elif 0 < earned_count < 4:
        return "\x02Clan weekly rewards:\x02 {}".format(" || ".join(output))
    else:
        return "\x02Clan weekly rewards:\x02 None have been earned you slackers!"

@hook.command('rules')
def rules():
    return 'Check \'em! https://www.reddit.com/r/DestinyTheGame/wiki/irc'

@hook.command('news')
def news():
    feed = parse('https://www.bungie.net/en/Rss/NewsByCategory?category=destiny&currentpage=1&itemsPerPage=1')
    if not feed.entries:
        return 'Feed not found.'

    return '{} - {}'.format(
        feed['entries'][0]['summary'],
        try_shorten(feed['entries'][0]['link']))
