import json
from cloudbot import hook
from html.parser import HTMLParser
from random import sample
from requests import get
from pickle import dump, load

BASE_URL = 'https://www.bungie.net/platform/Destiny/'
CACHE = {}
CLASS_TYPES = {0: "Titan ", 1: "Hunter ", 2: "Warlock ", 3: ''}
CONSOLES = ['\x02\x033Xbox\x02\x03', '\x02\x0312Playstation\x02\x03']
LORE_CACHE = {}
HEADERS = {}
WEAPON_TYPES = ['Super', 'Melee', 'Grenade', 'AutoRifle', 'FusionRifle',
    'HandCannon', 'Machinegun', 'PulseRifle', 'RocketLauncher', 'ScoutRifle',
    'Shotgun', 'Sniper', 'Submachinegun', 'Relic', 'SideArm']
PVP_OPTS = ['activitiesEntered', 'assists', 'avgKillDistance', 'deaths', 'kills', 'k/d',
    'bestSingleGameKills', 'bestSingleGameScore', 'bestWeapon', 'longestKillSpree',
    'secondsPlayed', 'longestSingleLife', 'orbsDropped', 'precisionKills',
    'precisionRate', 'suicides', 'winRate', 'zonesCaptured']
PVE_OPTS = ['activitiesEntered', 'activitiesCleared', 'avgKillDistance',
    'bestSingleGameKills', 'bestWeapon', 'longestKillSpree', 'deaths', 'kills', 'k/h',
    'secondsPlayed', 'longestSingleLife', 'orbsDropped', 'precisionKills',
    'precisionRate', 'suicides', 'winRate', 'publicEventsCompleted']


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
    return s.get_data().replace('\n', '\t')


def get_user(user_name):
    """
    Takes in a username and returns a dictionary of all systems they are
    on as well as their associated id for that system, plus general information
    """
    user_name = CACHE['links'].get(user_name, user_name)
    if CACHE.get(user_name, None):
        return CACHE[user_name]
    else:
        try:
            userID = get(
                "http://www.bungie.net/Platform/User/SearchUsers/?q={}".format(user_name.strip()),
                headers=HEADERS).json()['Response'][0]
            userHash = get(
                "https://www.bungie.net/platform/User/GetBungieAccount/{}/254/"
                .format(userID['membershipId']),
                headers=HEADERS).json()['Response']['destinyAccounts']
        except:
            return "A user by the name {} was not found.".format(user_name)

        user_info = {}  #
        for result in userHash:
            character_dict = {}
            for character in result['characters']:
                character_dict[character['characterId']] = {
                    'level': character['level'],
                    'class': character['characterClass']['className']
                }
            user_dict = {
                'membershipId': result['userInfo']['membershipId'],
                'clan': result.get('clanName', 'None'),
                'characters': character_dict
            }
            user_info[result['userInfo']['membershipType']] = user_dict

        CACHE[userID['displayName']] = user_info
        return user_info if user_info != {} else "A user by the name {} was not found.".format(user_name)

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

def best_weapon(data):
    best = 0
    weapon = None
    for stat in data:
        if "weaponKills" in stat:
            if data[stat]['basic']['value'] > best:
                best = data[stat]['basic']['value']
                weapon = stat
    return "{}: {} kills".format(
        weapon[11:], round(best)) if best else "You ain't got no best weapon!"

def get_stat(data, stat):
    if stat in WEAPON_TYPES:
        stat = "weaponKills{}".format(stat)
    if stat in data:
        return '\x02{}\x02: {}'.format(
            data[stat]['statId'], data[stat]['basic']['displayValue'])
    elif stat == 'k/d':
        return '\x02k/d\x02: {}'.format(round(
            data['kills']['basic']['value'] / data['deaths']['basic']['value'], 2))
    elif stat == 'k/h':
        return '\x02k/h\x02: {}'.format(round(data['kills']['basic']['value'] / (
            data['secondsPlayed']['basic']['value'] / 3600), 2))
    elif stat == 'avgKillDistance':
        return '\x02avgKillDistance\x02: {}m'.format(round(
            data['totalKillDistance']['basic']['value'] / data['kills']['basic']['value'], 2))
    elif stat == 'winRate':
        return '\x02winRate\x02: {}'.format(round(data['activitiesWon']['basic']['value'] / (
            data['activitiesEntered']['basic']['value'] - data['activitiesWon']['basic']['value']), 2))
    elif stat == 'precisionRate':
        return '\x02precisionRate\x02: {}'.format(round(data['precisionKills']['basic']['value'] / (
            data['kills']['basic']['value'] - data['precisionKills']['basic']['value']), 2))
    elif stat == 'bestWeapon':
        return '\x02bestWeapon\x02: {}'.format(best_weapon(data))
    else:
        return "Invalid option {}".format(stat)


def compile_stats(text, nick, bot, opts, defaults, st_type):
    if not text:
        text = nick
    text = text.split(" ")
    if text[0].lower() == 'help':
        return 'options: {}'.format(", ".join(opts + WEAPON_TYPES))
    elif text[0] in opts or text[0] in WEAPON_TYPES:
        text = [nick] + text
    membership = get_user(text[0])
    if type(membership) == str:
        return membership
    if len(text) == 1:  # if no stats are specified, add some
        text.extend(defaults)
    split = True if 'split' in text else False
    path = 'characters' if split else 'mergedAllCharacters'

    output = []
    for console in membership:
        data = get(
            "{}Stats/Account/{}/{}/".format(
                BASE_URL, console, membership[console]['membershipId']),
            headers=HEADERS
        ).json()['Response'][path]
        tmp_out = []
        if split:
            if text[1] not in opts and text[1] not in WEAPON_TYPES:
                return 'I can\'t split {}. Try another option.'.format(text[1])
            for character in data:
                if not character['deleted'] and character['results'][st_type].get('allTime', False):
                    tmp_out.append('\x02{}\x02 {}'.format(
                        membership[console]['characters'][character['characterId']]['class'],
                        get_stat(character['results'][st_type]['allTime'], text[1])
                    ))
        else:
            data = data['results'][st_type]['allTime']
            for stat in text[1:]:
                tmp_out.append(get_stat(data, stat))

        output.append("{}: {}".format(CONSOLES[console - 1], ", ".join(tmp_out)))
    return "; ".join(output)


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
    if not CACHE.get('links'):
        CACHE['links'] = {}
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

        output.append('\x02{}\x02 ({} {}{}) - \x1D{}\x1D - http://www.destinydb.com/items/{}'.format(
            result['itemName'],
            result['tierTypeName'],
            CLASS_TYPES[result['classType']],
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
def triumph(text, nick, bot):
    text = nick if not text else text
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
    membership = get_user(text)
    if type(membership) == str:
        return membership
    output = []
    for console in membership:
        triumphHash = get(
            "{}{}/Account/{}/Triumphs/"
            .format(BASE_URL, console, membership[console]['membershipId']),
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
        exoticsHash = [hashes[i]['item'] for i in range(6)]

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
        engram = text['items'][str(exoticsHash[5]['itemHash'])]['itemTypeName']
        output = '\x02Armor\x02 {} \x02Weapon\x02 {} \x02Engram\x02 {}'.format(
            ', '.join(armor_list), weapon, engram)
        CACHE['xur'] = output
        return output


@hook.command('lore')
def lore(text, bot):
    if not LORE_CACHE or text.lower() == 'flush':  # if the cache doesn't exist, create it
        prepare_lore_cache()
        text = ''

    name = ''
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
        name, contents.get('cardIntro', ''), contents.get('cardDescription', '')))
    if len(output) > 300:
        output = '{}... Read more at http://www.destinydb.com/grimoire/{}'.format(
            output[:301], contents['cardId'])

    return output if len(output) > 5 else lore('', bot)


@hook.command('grim')
def grim(text, nick, bot):
    text = nick if not text else text
    membership = get_user(text)
    if type(membership) == str:
        return membership
    output = []
    for console in membership:
        score = get(
            "{}Vanguard/Grimoire/{}/{}/"
            .format(BASE_URL, console, membership[console]['membershipId']),
            headers=HEADERS
        ).json()['Response']['data']['score']
        output.append("{}'s grimoire score on the {} is {}.".format(
            text, CONSOLES[console - 1], score))

    return output


@hook.command('pvp')
def pvp(text, nick, bot):
    defaults = ['k/d', 'bestSingleGameKills', 'longestKillSpree',
        'longestSingleLife', 'orbsDropped', 'bestWeapon']
    return compile_stats(
        text=text,
        nick=nick,
        bot=bot,
        opts=PVP_OPTS,
        defaults=defaults,
        st_type='allPvP'
    )


@hook.command('pve')
def pve(text, nick, bot):
    defaults = ['k/h', 'activitiesCleared', 'longestKillSpree',
        'publicEventsCompleted', 'orbsDropped', 'bestWeapon']
    return compile_stats(
        text=text,
        nick=nick,
        bot=bot,
        opts=PVE_OPTS,
        defaults=defaults,
        st_type='allPvE'
    )


@hook.command('ghosts')
def ghosts(text, nick, bot):
    text = nick if not text else text
    membership = get_user(text)
    if type(membership) == str:
        return membership
    output = []
    for console in membership:
        data = get(
            "{}Vanguard/Grimoire/{}/{}/"
            .format(BASE_URL, console, membership[console]['membershipId']),
            headers=HEADERS
        ).json()['Response']['data']['cardCollection']
        for card in data:
            if card['cardId'] == 103094:
                output.append('{}: {}/77'.format(
                    CONSOLES[console - 1],
                    card['statisticCollection'][0]['displayValue'])
                )
    return output



@hook.command('link')
def link(text, nick, bot):
    text = text.split(" ")
    if text[0].lower == 'flush':
        CACHE['links'][text[1]] = ""
        return "{} flushed".format(text[1])
    else:
        CACHE['links'][nick] = text[0]
        return "{} linked to {}".format(text[0], nick)

@hook.command('migrate')
def migrate(text, nick, bot):
    if nick in ['weylin', 'avcables[PS4]', 'DoctorRaptorMD[XB1]']:
        global CACHE
        CACHE = {'links': CACHE['links']}
        return "Sucessfully migrated! Now run the save command."
    else:
        return "Your light is not strong enough."

@hook.command('rules')
def rules(bot):
    return "Check 'em! https://www.reddit.com/r/DestinyTheGame/wiki/irc"


@hook.command('compare')
def compare(text, bot):
    return 'Do it your fucking self, lazy bastard!'

@hook.command('ping')
def ping(text, bot):
    return 'pong'

@hook.command('100')
def the100(bot):
    return 'Check out our The100.io group here: https://www.the100.io/g/1151'

@hook.command('clan')
def clan(bot):
    return 'Check out our Clan: https://www.bungie.net/en/Clan/Detail/939927'
