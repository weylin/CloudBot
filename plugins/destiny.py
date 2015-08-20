import json
from cloudbot import hook
from html.parser import HTMLParser
from random import randint, sample
from requests import get
from pickle import dump, load

BASE_URL = 'https://www.bungie.net/platform/Destiny/'
CACHE = {}
CLASS_TYPES = {0: "Titan", 1: "Hunter", 2: "Warlock", 3: ''}  # why is 3 here?
CONSOLES = ['Xbox', 'Playstation']
LORE_CACHE = {}
HEADERS = {}


class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data().replace('\n','\t')

def get_membership(user_name, bot):
    """
    Takes in a username and returns a dictionary of all systems they are
    on as well as their associated id for that system
    """
    if CACHE.get(user_name, None):
        return CACHE[user_name]
    else:
        userID = get(
            "http://www.bungie.net/Platform/User/SearchUsers/?q={}"
            .format(user_name.strip()),
            headers=HEADERS).json()['Response'][0]
        userIDHash = userID['membershipId']
        userName = userID['displayName']

        userHash = get(
            "https://www.bungie.net/platform/User/GetBungieAccount/{}/254/"
            .format(userIDHash),
            headers=HEADERS).json()['Response']['destinyAccounts']
        membership = {}  # {console: memberId}
        for result in userHash:
            membership[result['userInfo']['membershipType']] = result['userInfo']['membershipId']
        CACHE[userName] = membership
        return membership

def prepare_lore_cache():
    """
   This function will allow us to do this: LORE_CACHE[name]['cardIntro']
   """
    lore_base = get("{}/Vanguard/Grimoire/Definition/".format(BASE_URL),
        headers=HEADERS).json()['Response']['themeCollection']
 
    global LORE_CACHE
    LORE_CACHE = {}
    for level1 in lore_base:
        for level2 in level1['pageCollection']:
            for card in level2['cardCollection']:
                LORE_CACHE[card['cardName']] = {
                    'cardIntro': card.get('cardIntro', ''),
                    'cardDescription': card['cardDescription'],
                    'cardId': card['cardId']
                }

@hook.on_start()
def load_cache(bot):
    """Load in our pickle cache and the Headers"""
    global HEADERS
    HEADERS = {"X-API-Key": bot.config.get("api_keys", {}).get("destiny", None)}
    try:
        with open('destiny_cache', 'rb') as f:
            global CACHE
            CACHE = load(f)  # and the pickles!!!
    except EOFError:
        CACHE = {}
    try:
        with open('lore_cache', 'rb') as f:
            global LORE_CACHE
            LORE_CACHE = load(f)  # and the pickles!!!
    except EOFError:
        LORE_CACHE = {}


@hook.command('save')
def save_cache():
    output = 'Neither cache saved'
    with open('destiny_cache', 'wb') as f:
        dump(CACHE, f)
        output = ["Main cache saved"]
    with open('lore_cache', 'wb') as f:
        dump(CACHE, f)
        output.append("Lore cache saved")
    return output


@hook.command('item')
def item_search(text, bot):
    """
    Expects the tex to be a valid object in the Destiny database
    Returns the item's name and description.
    TODO: Implement error checking
    """
    item = text.strip()
    itemquery = '{}Explorer/Items?name={}'.format(BASE_URL, item)
    itemHash = get(
        itemquery, headers=HEADERS).json()['Response']['data']['itemHashes']

    output = []
    for item in itemHash:
        itemquery = '{}Manifest/inventoryItem/{}'.format(BASE_URL, item)
        result = get(
            itemquery, headers=HEADERS).json()['Response']['data']['inventoryItem']

        output.append('\x02{}\x02 ({} {} {}) - \x1D{}\x1D - http://www.destinydb.com/items/{}'.format(
            result['itemName'],
            result['tierTypeName'],
            result['classType'],
            result['itemTypeName'],
            result.get('itemDescription', 'Item has no description.'),
            result['itemHash']
        ))
    return output[:3]


@hook.command('nightfall')
def nightfall(text, bot):
    if CACHE.get('nightfall', None) and not text.lower() == 'flush':
        return CACHE['nightfall']
    else:
        nightfallActivityId = get(
            '{}advisors/?definitions=true'.format(BASE_URL),
            headers=HEADERS).json()['Response']['data']['nightfallActivityHash']

        nightfallDefinition = get(
            '{}manifest/activity/{}/?definitions=true'
            .format(BASE_URL, nightfallActivityId),
            headers=HEADERS).json()['Response']['data']['activity']

        if len(nightfallDefinition['skulls']) == 5:
            output = '\x02{}\x02 - \x1D{}\x1D \x02Modifiers:\x02 {}, {}, {}, {}, {}'.format(
                nightfallDefinition['activityName'],
                nightfallDefinition['activityDescription'],
                nightfallDefinition['skulls'][0]['displayName'],
                nightfallDefinition['skulls'][1]['displayName'],
                nightfallDefinition['skulls'][2]['displayName'],
                nightfallDefinition['skulls'][3]['displayName'],
                nightfallDefinition['skulls'][4]['displayName'],
            )
            CACHE['nightfall'] = output
            return output
        else:
            return 'weylin lied to me, get good scrub.'


@hook.command('weekly')
def weekly(text, bot):
    if CACHE.get('weekly', None) and not text.lower() == 'flush':
        return CACHE['weekly']
    else:
        weeklyHeroicId = get(
            '{}advisors/?definitions=true'.format(BASE_URL),
            headers=HEADERS
        ).json()['Response']['data']['heroicStrike']['activityBundleHash']

        weeklyHeroicDefinition = get(
            '{}manifest/activity/{}/?definitions=true'
            .format(BASE_URL, weeklyHeroicId),
            headers=HEADERS).json()['Response']['data']['activity']
        weeklyHeroicSkullIndex = weeklyHeroicDefinition['skulls']

        if len(weeklyHeroicSkullIndex) == 2:
            output = '\x02{}\x02 - \x1D{}\x1D \x02Modifier:\x02 {}'.format(
                weeklyHeroicDefinition['activityName'],
                weeklyHeroicDefinition['activityDescription'],
                weeklyHeroicDefinition['skulls'][1]['displayName']
            )
            CACHE['weekly'] = output
            return output
        else:
            return 'weylin lied to me, get good scrub.'


@hook.command('triumph')
def triumph(text, bot):
    triumphText = [
        '\x02Apprentice of Light\x02 (Max Level)',
        '\x02Light of the Garden\x02 (Main Story Complete)',
        '\x02Light in the Dark\x02 (The Dark Below Complete)',
        '\x02Light of the Reef\x02 (House of Wolves Complete)',
        '\x02Bane of Skolas\x02 (PoE 35 Complete)',
        '\x02Bane of Atheon\x02 (HM VoG Complete)',
        '\x02Bane of Crota\x02 (HM CE Complete)',
        '\x02Public Servant\x02 (50 Public Events Complete)',
        '\x02Crucible Gladiator\x02 (Win 100 Crucible Matches)',
        '\x02Chest Hunter\x02 (Found 20 Golden Chests)',
    ]

    membership = get_membership(text, bot)
    output = []
    for console in membership:
        triumphHash = get(
            "{}{}/Account/{}/Triumphs/"
            .format(BASE_URL, console, membership[console]),
            headers=HEADERS
        ).json()['Response']['data']['triumphSets'][0]['triumphs']

        remaining = []
        for i in range(10):
            if not triumphHash[i]['complete']:
                remaining.append(triumphText[i])

        if len(remaining) == 0:
            output.append(
                "\x02{}\'s\x02 Year One Triumph is complete on {}!".format(
                    text, CONSOLES[console - 1]))
        else:
            output.append(
                "\x02{}\'s\x02 Year One Triumph is not complete on {}. "
                "\x02Remaining task(s):\x02 {}".format(
                    text, CONSOLES[console - 1], ', '.join(remaining)))

    return output


@hook.command('xur')
def xur(text, bot):
    if CACHE.get('xur', None) and not text.lower() == 'flush':
        return CACHE['xur']
    else:
        xurStock = get(
            "{}Advisors/Xur/?definitions=true".format(BASE_URL),
            headers=HEADERS).json()['Response']

        hashes = xurStock['data']['saleItemCategories'][0]['saleItems']
        text = xurStock['definitions']
        exoticsHash = [hashes[i]['item'] for i in range(5)]

        armor_list = []
        for i in range(3):
            exotic = '{} ({}: {}, {}: {}, {}: {})'.format(
                text['items'][str(exoticsHash[i]['itemHash'])]['itemName'],
                text['stats'][str(exoticsHash[i]['stats'][1]['statHash'])]['statName'][:3],
                exoticsHash[i]['stats'][1]['value'],
                text['stats'][str(exoticsHash[i]['stats'][2]['statHash'])]['statName'][:3],
                exoticsHash[i]['stats'][2]['value'],
                text['stats'][str(exoticsHash[i]['stats'][3]['statHash'])]['statName'][:3],
                exoticsHash[i]['stats'][3]['value']
            )
            armor_list.append(exotic)
        weapon = text['items'][str(exoticsHash[3]['itemHash'])]['itemName']
        engram = text['items'][str(exoticsHash[4]['itemHash'])]['itemName']
        output = '\x030,1 Armor \x030,14 {}; \x030,1 Weapon \x030,14 {}; \x030,1 Engram \x030,14 {}'.format(
            ', '.join(armor_list), weapon, engram)
        CACHE['xur'] = output
        return output

@hook.command('lore')
def lore(text, bot):
    if not LORE_CACHE:  # if the cache doesn't exist, create it
        prepare_lore_cache()
 
    if not text:  # if we aren't searching, return a random card
        name = sample(list(LORE_CACHE), 1)[0]
    else:
        matches = []
        for entry in LORE_CACHE:
            if text.lower() in entry.lower():
                name = entry
            elif text.lower() in entry.lower():
                matches.append(entry)
        if not name:
             if len(matches) == 1:
                 name = matches[0]
             elif len(matches) == 0:
                 return "I ain't found shit!"
             else:
                 return ("Search too ambiguous, please be more specific "
                   "(e.g. {}).".format(", ".join(matches[:3])))
 
    contents = LORE_CACHE[name]  # get the actual card contents
    output = strip_tags("{}: {} - {}".format(
            name, contents.get('cardIntro', ''), contents['cardDescription']))
    if len(output) > 300:
        output = '{}... Read more at http://www.destinydb.com/grimoire/{}'.format(
            output[:301], contents['cardId'])
 
    return output if len(output) > 5 else lore(bot)

@hook.command('grim')
def grim(text, bot):
    membership = get_membership(text, bot)
    output = []
    for console in membership:
        score = get(
            "{}Vanguard/Grimoire/{}/{}/"
            .format(BASE_URL, console, membership[console]),
            headers=HEADERS
        ).json()['Response']['data']['score']
        output.append("{}'s grimoire score on the {} is {}.".format(
            text, CONSOLES[console - 1], score))

    return output


@hook.command('rules')
def rules(bot):
    return "Check 'em! https://www.reddit.com/r/DestinyTheGame/wiki/irc"


@hook.command('compare')
def compare(text, bot):
    return 'Do it your fucking self, lazy bastard!'
