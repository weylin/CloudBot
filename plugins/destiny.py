import datetime
import json
from cloudbot import hook
from html.parser import HTMLParser
from random import sample
from requests import get
from pickle import dump, load
from feedparser import parse
from cloudbot.util.web import try_shorten

BASE_URL = 'https://www.bungie.net/platform/Destiny/'
CACHE = {}
CLASS_TYPES = {0: "Titan ", 1: "Hunter ", 2: "Warlock ", 3: ''}
CONSOLES = ['\x02\x033Xbox\x02\x03', '\x02\x0312Playstation\x02\x03']
STAT_HASHES = {144602215: 'Int', 1735777505: 'Disc', 4244567218: 'Str'}
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
                'userId': userID['membershipId'],
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
    grim_tally = 0
    fragments = {}
    for level1 in lore_base:
        if level1.get('themeId','') == 'Enemies':
            for page in level1['pageCollection']:
                if page['pageId'] == 'BooksofSorrow':
                    for card in page['cardCollection']:
                        fragments[card['cardId']] = card['cardName']
        for level2 in level1.get('pageCollection', []):
            for card in level2.get('cardCollection', []):
                LORE_CACHE[card['cardName']] = {
                    'cardIntro': card.get('cardIntro', ''),
                    'cardDescription': card['cardDescription'],
                    'cardId': card['cardId']
                }
            for card in level2.get('cardBriefs', []):
                grim_tally += card.get('totalPoints', 0)
    CACHE['collections']['grim_tally'] = grim_tally
    CACHE['collections']['fragments'] = fragments


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
    '''Load in our pickle cache and the Headers'''
    global HEADERS
    HEADERS = {'X-API-Key': bot.config.get('api_keys', {}).get('destiny', None)}
    try:
        with open('destiny_cache', 'rb') as f:
            global CACHE
            CACHE = load(f)  # and the pickles!!!
    except EOFError:
        CACHE = {}
    CACHE.pop('collections', None)
    if not CACHE.get('links'):
        CACHE['links'] = {}
    if not CACHE.get('collections'):
        CACHE['collections'] = {'ghost_tally': 99}
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
        dump(LORE_CACHE, f)
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
        if 'last' in text.lower():
            return CACHE.get('last_nightfall', 'Unavailable')
        else:
            return CACHE['nightfall']
    else:
        advisors = get(
            '{}advisors/?definitions=true'.format(BASE_URL),
            headers=HEADERS).json()#['Response']['data']['nightfall']
        nightfallId = advisors['Response']['data']['nightfall']['specificActivityHash']
        nightfallActivityBundleHashId = advisors['Response']['data']['nightfall']['activityBundleHash']


        nightfallDefinition = advisors['Response']['definitions']['activities'][str(nightfallId)]

        output = '\x02{}\x02 - \x1D{}\x1D \x02Modifiers:\x02 {}'.format(
            nightfallDefinition['activityName'],
            nightfallDefinition['activityDescription'],
            ", ".join([advisors['Response']['definitions']['activities'][str(nightfallActivityBundleHashId)]['skulls'][skullId]['displayName'] for skullId in advisors['Response']['data']['nightfall']['tiers'][0]['skullIndexes']])
        )
        if 'nightfall' in CACHE and output != CACHE['nightfall']:
            CACHE['last_nightfall'] = CACHE['nightfall']
        CACHE['nightfall'] = output
        return output


#@hook.command('weekly')
def weekly(text, bot):
    if CACHE.get('weekly', None) and not text.lower() == 'flush':
        if 'last' in text.lower():
            return CACHE.get('last_weekly', 'Unavailable')
        else:
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
            if output != CACHE['weekly']:
                CACHE['last_weekly'] = CACHE['weekly']
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
    if 'last' in text.lower():
        return CACHE.get('last_xur', 'Unavailable')

    # reset happens at 9am UTC, so subtract that to simplify the math
    now = datetime.datetime.utcnow() - datetime.timedelta(hours=9)

    # xur is available from friday's reset until sunday's reset, i.e. friday (4) and saturday (5)
    if now.weekday() not in [4, 5]:
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
            output.append("{} days".format(time_to_xursday.days))

        if h: output.append("{} hours".format(h))
        if m: output.append("{} minutes".format(m))
        if s: output.append("{} seconds".format(s))

        return '\x02Xûr will return in\x02 {}'.format(", ".join(output))

    if CACHE.get('xur', None) and not text.lower() == 'flush':
        return CACHE['xur']

    xurStock = get(
        "{}Advisors/Xur/?definitions=true".format(BASE_URL),
        headers=HEADERS).json()['Response']

    items = [i['item'] for i in xurStock['data']['saleItemCategories'][2]['saleItems']]
    definitions = xurStock['definitions']['items']

    output = []
    for item in items:
        item_def = definitions[str(item['itemHash'])]
        stats = []
        for stat in item['stats']:
            if stat['statHash'] in STAT_HASHES and stat['value'] > 0:
                stats.append("{}: {}".format(STAT_HASHES[stat['statHash']], stat['value']))
        output.append("{}{}".format(
            item_def['itemName'] if 'Engram' not in item_def['itemName'] else item_def['itemTypeName'],
            " ({})".format(", ".join(stats)) if stats else ""
        ))
    output = ", ".join(output)

    if output != CACHE.get('xur', output):
        CACHE['last_xur'] = CACHE['xur']
    CACHE['xur'] = output
    return output


@hook.command('lore')
def lore(text, bot, notice):
    if not LORE_CACHE or text.lower() == 'flush':  # if the cache doesn't exist, create it
        prepare_lore_cache()
        text = ''
    complete = False
    if "complete" in text:
        complete = True
        text = text.replace("complete", "").strip()

    name = ''
    if not text:  # if we aren't searching, return a random card
        name = sample(list(LORE_CACHE), 1)[0]
        while name == 'grim_tally':
            name = sample(list(LORE_CACHE), 1)[0]
    else:
        matches = []
        for entry in LORE_CACHE:
            if entry == 'grim_tally':
                continue
            if text.lower() == entry.lower():
                name = entry
            elif text.lower() in entry.lower() or text.lower() in LORE_CACHE[entry].get('cardDescription', '').lower():
                matches.append(entry)
        if not name:
            if len(matches) == 1:
                name = matches[0]
            elif len(matches) == 0:
                return "I ain't found shit!"
            elif complete:
                notice("I found {} matches. You can choose from:".format(len(matches)))
                for line in matches:
                    notice(line)
                return
            else:
                return ("I found {} matches, please be more specific "
                        "(e.g. {}). For a complete list use 'complete'".format(
                            len(matches), ", ".join(matches[:3])))

    contents = LORE_CACHE[name]  # get the actual card contents
    output = strip_tags("{}: {} - {}".format(
        name, contents.get('cardIntro', ''), contents.get('cardDescription', '')))

    if complete:
        notice(output)
        return
    elif len(output) > 300:
        output = '{}... Read more at http://www.destinydb.com/grimoire/{}'.format(
            output[:301], contents['cardId'])

    return output if len(output) > 5 else lore('', bot, notice)


#@hook.command('grim')
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
        output.append("{}'s grimoire score on the {} is {} out of {}.".format(
            text, CONSOLES[console - 1], score, LORE_CACHE['grim_tally']))

    return output


@hook.command('pvp')
def pvp(text, nick, bot):
    defaults = ['k/d', 'k/h', 'kills', 'bestSingleGameKills', 'longestKillSpree',
        'bestWeapon', 'secondsPlayed']
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
    defaults = ['k/h', 'kills', 'activitiesCleared', 'longestKillSpree',
        'bestWeapon', 'secondsPlayed']
    return compile_stats(
        text=text,
        nick=nick,
        bot=bot,
        opts=PVE_OPTS,
        defaults=defaults,
        st_type='allPvE'
    )


@hook.command('collection')
def collection(text, nick, bot):
    text = nick if not text else text
    membership = get_user(text)
    if type(membership) == str:
        return membership
    output = []
    for console in membership:
        grimoire = get(
            "{}Vanguard/Grimoire/{}/{}/"
            .format(BASE_URL, console, membership[console]['membershipId']),
            headers=HEADERS
        ).json()['Response']['data']
        found_frags = []
        ghosts = 0
        for card in grimoire['cardCollection']:
            if card['cardId'] in CACHE['collections']['fragments']:
                found_frags.append([card['cardId']])
            elif card['cardId'] == 103094:
                ghosts = card['statisticCollection'][0]['displayValue']
                if int(ghosts) >= 99:
                    ghosts = 99
        output.append("{}: Grimoire {}/{}, Ghosts {}/{}, Fragments {}/{}".format(
            CONSOLES[console - 1], grimoire['score'], CACHE['collections']['grim_tally'],
            ghosts, CACHE['collections']['ghost_tally'],
            len(found_frags), len(CACHE['collections']['fragments']))
        )
    return output


#@hook.command('ghosts')
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
                output.append('{}: {} out of 99'.format(
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
    if nick in ['weylin', 'avcables[PS4]', 'DoctorRaptorMD[XB1]', 'tuzonghua[PS4]']:
        global CACHE
        CACHE = {'links': CACHE['links']}
        return "Sucessfully migrated! Now run the save command."
    else:
        return "Your light is not strong enough."

@hook.command('purge')
def purge(text, nick, bot):
    membership = get_user(nick)
    if type(membership) is not dict:
        return membership
    user_name = CACHE['links'].get(nick, nick)
    output = []
    text = "" if not text else text

    if text.lower() == "xbox" and membership.get(1, False):
        del membership[1]
        output.append("Removed Xbox from my cache on {}.".format(user_name))
    if text.lower() == "playstation" and membership.get(2, False):
        del membership[2]
        output.append("Removed Playstation from my cache on {}.".format(user_name))
    if not text or not membership:
        del CACHE[user_name]
        return 'Removed {} from my cache.'.format(user_name)
    else:
        CACHE[user_name] = membership
        return output if output else "Nothing to purge. WTF you doin?!"


@hook.command('profile')
def profile(text, nick, bot):
    text = nick if not text else text
    membership = get_user(text)
    if type(membership) is not dict:
        return membership
    return "https://www.bungie.net/en/Profile/254/{}".format(
        membership.get(1, membership.get(2, None))['userId'])

@hook.command('chars')
def chars(text, nick, bot):
    text = nick if not text else text
    text = text.split(" ")
    if text[0] in ['xbox', 'playstation', '1', '2', '3']:
        text = [nick] + text
    text[0] = CACHE['links'].get(text[0], text[0])
    if type(get_user(text[0])) is not dict:
        return "A user by the name {} was not found.".format(text[0])
    userID = get("http://www.bungie.net/Platform/User/SearchUsers/?q={}".format(
                 text[0].strip()), headers=HEADERS).json()['Response'][0]
    systems, characters = ([], [])
    if len(text) > 1:
        # narrow down our results
        for x in text[1:]:
            if x == 'xbox': systems.append(1)
            if x == 'playstation': systems.append(2)
            if x in ['1', '2', '3']: characters.append(int(x))

    userHash = get("https://www.bungie.net/platform/User/GetBungieAccount"
                   "/{}/254/".format(userID['membershipId']), headers=HEADERS
               ).json()['Response']['destinyAccounts']
    output = []
    for console in userHash:
        if console['userInfo']['membershipType'] not in systems and systems:
            continue
        console_output = []
        for i in range(len(console['characters'])):
            if i + 1 not in characters and characters:
                continue
            console['characters'][i]['characterClass']['className'],
            console_output.append("✦{} // {} // {} - {}".format(
            console['characters'][i]['powerLevel'],
            console['characters'][i]['characterClass']['className'],
            console['characters'][i]['race']['raceName'],
            try_shorten("https://www.bungie.net/en/Legend/Gear/{}/{}/{}".format(
                console['userInfo']['membershipType'],
                console['userInfo']['membershipId'],
                console['characters'][i]['characterId']
            ))
        ))
        output.append("{}: {}".format(
            CONSOLES[console['userInfo']['membershipType'] - 1],
            " || ".join(console_output)
        ))
    return " ; ".join(output)


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

@hook.command('news')
def news(bot):
    feed = parse("https://www.bungie.net/en/Rss/NewsByCategory?category=destiny&currentpage=1&itemsPerPage=1")
    if not feed.entries:
        return "Feed not found."

    return "{} - {}".format(
        feed['entries'][0]['summary'],
        try_shorten(feed['entries'][0]['link']))
