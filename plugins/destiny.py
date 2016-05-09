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
CLASS_TYPES = {0: 'Titan ', 1: 'Hunter ', 2: 'Warlock ', 3: ''}
CLASS_HASH = {671679327: 'Hunter', 3655393761: 'Titan', 2271682572: 'Warlock'}
RACE_HASH = {898834093: 'Exo', 3887404748: 'Human', 2803282938: 'Awoken'}
CONSOLES = ['\x02\x033Xbox\x02\x03', '\x02\x0312Playstation\x02\x03']
STAT_HASHES = {144602215: 'Int', 1735777505: 'Disc', 4244567218: 'Str'}
ENEMY_RACE_HASH = {3265589059: 'Hive', 546070638: 'Cabal', 711470098: 'Vex', 1636291695: 'Fallen'}
BOSS_COMBATANT_HASH = {1: 'Pilot Servitor', 2: 'Val Aru\'un', 3: 'Wretched Knight', 4: 'Overmind Minotaur', 5: 'Seditious Mind', 6: 'Noru’usk, Servant of Oryx', 7: 'Keksis the Betrayed', 8: 'Sylok, the Defiled'}
LORE_CACHE = {}
HEADERS = {}
WEAPON_TYPES = ['Super', 'Melee', 'Grenade', 'AutoRifle', 'FusionRifle',
    'HandCannon', 'Machinegun', 'PulseRifle', 'RocketLauncher', 'ScoutRifle',
    'Shotgun', 'Sniper', 'Submachinegun', 'Relic', 'SideArm']
WEAPON_CLASSES = {"PrimaryWeapon": ['HandCannon', 'AutoRifle', 'PulseRifle',
                                    'ScoutRifle'],
                  "SpecialWeapon": ['FusionRifle', 'Shotgun', 'Sniper', 'SideArm'],
                  "HeavyWeapon": ['Machinegun', 'Submachinegun', 'RocketLauncher',
                                  'Relic'],
                  "Ability": ['Super', 'Melee', 'Grenade']}
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

def get_user(user_name, console=None):
    '''
    Takes in a username and returns a dictionary of all systems they are
    on as well as their associated id for that system, plus general information
    '''
    platforms = CACHE['links'].get(user_name, {console: user_name})

    if CACHE.get(user_name, None):
        return CACHE[user_name]
    else:
        user_info = {}
        for platform in platforms:
            gamertag = platforms[platform]
            try:
                # Get the Destiny membership ID
                membershipId = get('{}SearchDestinyPlayer/{}/{}/'.format(BASE_URL, platform, gamertag),
                    headers=HEADERS).json()['Response'][0]['membershipId']
                # Then get Destiny summary
                characterHash = get(
                    '{}{}/Account/{}/Summary/'
                    .format(BASE_URL, platform, membershipId),
                    headers=HEADERS).json()['Response']['data']
            except:
                return 'A user by the name {} was not found.'.format(gamertag)

            character_dict = {}
            for character in characterHash['characters']:
                character_dict[character['characterBase']['characterId']] = {
                    'level': character['characterLevel'],
                    'LL': character['characterBase']['powerLevel'],
                    'race': RACE_HASH[character['characterBase']['raceHash']],
                    'class': CLASS_HASH[character['characterBase']['classHash']]
                }
            user_dict = {
                'membershipId': membershipId,
                'clan': characterHash.get('clanName', 'None'),
                'characters': character_dict
            }
            user_info[platform] = user_dict

        CACHE[user_name] = user_info
        return user_info if user_info else 'A user by the name {} was not found.'.format(user_name)

def prepare_lore_cache():
    '''
   This function will allow us to do this: LORE_CACHE[name]['cardIntro']
   '''
    lore_base = get('{}/Vanguard/Grimoire/Definition/'.format(BASE_URL),
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
        if 'weaponKills' in stat:
            if data[stat]['basic']['value'] > best:
                best = data[stat]['basic']['value']
                weapon = stat
    return '{}: {} kills'.format(
        weapon[11:], round(best)) if best else 'You ain\'t got no best weapon!'

def get_weaponclass_total(data, weapon_class):
    # TODO: No Land Beyond, Universal Remote, Sleeper Simulant, etc.
    if weapon_class in WEAPON_CLASSES:
        weaponclass_kills = 0
        for primitive_stat in WEAPON_CLASSES[weapon_class]:
            raw_stat = "weaponKills{0}".format(primitive_stat)
            weaponclass_kills += data[raw_stat]['basic']['value']
        return weaponclass_kills
    else:
        return None

def get_stat(data, stat):
    if stat in WEAPON_TYPES:
        stat = 'weaponKills{}'.format(stat)
    if stat in data:
        return '\x02{}\x02: {}'.format(
            data[stat]['statId'], data[stat]['basic']['displayValue'])
    elif stat.endswith("Percentage"):
        orig_stat = stat[:-len("Percentage")]
        if orig_stat in WEAPON_TYPES:
            orig_stat = "weaponKills{0}".format(orig_stat)
            return '\x02{0}\x02: {1}%'.format(stat, round( (data[orig_stat]['basic']['value'] /
                                                            data['kills']['basic']['value']) * 100, 2))
        elif orig_stat in WEAPON_CLASSES:
            return '\x02{0}\x02: {1}%'.format(stat, round( (get_weaponclass_total(data, orig_stat) /
                                                            data['kills']['basic']['value']) * 100, 2))
        else:
            return "Invalid percentage stat request {0}".format(orig_stat)
    elif stat in WEAPON_CLASSES:
        return '\x02{0}\x02: {1}'.format(stat, get_weaponclass_total(data, stat))
    elif stat == 'k/d':
        return '\x02k/d\x02: {}'.format(round(
            data['kills']['basic']['value'] / data['deaths']['basic']['value'], 2))
    elif stat == 'k/h':
        return '\x02k/h\x02: {}'.format(round(data['kills']['basic']['value'] / (
            data['secondsPlayed']['basic']['value'] / 3600), 2))
    elif stat == 'd/h':
        return '\x02d/h\x02: {}'.format(round(data['deaths']['basic']['value'] / (
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
        return 'Invalid option {}'.format(stat)

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
    except FileNotFoundError:
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
    except FileNotFoundError:
        LORE_CACHE = {}

def compile_stats(text, nick, bot, opts, defaults, split_defaults, st_type, notice):
    if not text:
        text = nick
    text = text.split(' ')
    CONSOLE_MAP = {"xbox": 1, "playstation": 2}

    # Do you need help?
    if text[0].lower() == 'help':
        notice('options: {}'.format(', '.join(opts + WEAPON_TYPES)))
        return

    target = compile_stats_arg_parse(text, nick)

    if target['user'] is None or not target['nick']:
        return "No possible user found."

    membership = target['user']

    # if no stats are specified, add some
    if not target['stats']:
        target['stats'] = defaults if not target['split'] else split_defaults
    split = target['split']
    path = 'characters' if split else 'mergedAllCharacters'

    output = []
    for console in membership:
        # If a console has been specified, grab only that console
        if target['console'] and console != CONSOLE_MAP[target['console']]:
            continue

        # Get stats
        data = get(
            '{}Stats/Account/{}/{}/'.format(
                BASE_URL, console, membership[console]['membershipId']),
            headers=HEADERS
        ).json()['Response'][path]
        tmp_out = []
        if not split:
            try:
                data = data['results'][st_type]['allTime']
                for stat in target['stats']:
                    tmp_out.append(get_stat(data, stat))
            except KeyError:
                return "Data not available yet."
        else:
            for character in data:
                if not character['deleted'] and character['results'][st_type].get('allTime', False):
                    tmp_out.append('\x02{}\x02 {}'.format(
                        membership[console]['characters'][character['characterId']]['class'],
                        " / ".join([get_stat(character['results'][st_type]['allTime'], stat) for stat in target['stats']])
                    ))

        output.append('{}: {}'.format(CONSOLES[console - 1], ', '.join(tmp_out)))
    return '\x02{0}\x02: {1}'.format(target['nick'], '; '.join(output))

def compile_stats_arg_parse(text_arr, given_nick):
    '''Parse the input

    :param textArr: the input text array to parse
    :type  textArr: string
    :param nick: the nick to get stats on
    :type nick: string

    :returns: a dictionary of values to use
    :rtype: dictionary of strings
    '''

    CONSOLES = {"xbl": "xbox", "psn": "playstation"}
    CONSOLE2ID = {"xbox": 1, "playstation": 2}
    nick = ''
    user = None
    console = None
    collect = []
    split = False

    # Nick/console
    args = text_arr[:]
    while args:
        check_arg = args.pop(0)
        if check_arg in CONSOLES and not console:
            console = CONSOLES[check_arg]
            if user:
                # better run it again
                user = get_user(nick, CONSOLE2ID[console])
            elif collect:
                # gamertag may have been given, try it
                for i, arg in enumerate(collect):
                    user = get_user(arg, CONSOLE2ID[console])
                    if not isinstance(user, str):
                        # Gamertag given, found, remove it.
                        collect.pop(i)
                        nick = arg
                        break
        elif check_arg == 'split':
            split = True
        elif not nick:
            if console:
                # perfect, we can just return the user for it
                t = get_user(check_arg, CONSOLE2ID[console])
            else:
                # not perfect, but give it a shot
                t = get_user(check_arg)

            if not isinstance(t, str):
                # XXX: Right now, the only string returned is "A user by
                # the name (nick) can't be found." So 'string' return
                # type means that's the case; anything else is real,
                # valid, good data.
                user = t
                nick = check_arg
            else:
                # not split, not nick, not console
                # must be collect
                collect.append(check_arg)
        else:
            collect.append(check_arg)

    # If we didn't get a nick, assume the requester.
    if not nick:
        user = get_user(given_nick, CONSOLE2ID[console]) if console else get_user(given_nick)
        if not isinstance(user, str):
           nick = given_nick
        else:
           user = None

    return_dict = {'user': user, 'nick': nick, 'console': console, 'stats': collect, 'split': split}
    return return_dict


@hook.command('pvp')
def pvp(text, nick, bot, notice):
    defaults = ['k/d', 'k/h', 'd/h', 'kills', 'bestSingleGameKills',
        'longestKillSpree', 'bestWeapon', 'secondsPlayed']
    split_defaults = ['k/d']
    return compile_stats(
        text=text,
        nick=nick,
        bot=bot,
        opts=PVP_OPTS,
        defaults=defaults,
        split_defaults=split_defaults,
        st_type='allPvP',
        notice=notice
    )

@hook.command('pve')
def pve(text, nick, bot, notice):
    defaults = ['k/h', 'kills', 'activitiesCleared', 'longestKillSpree',
        'bestWeapon', 'secondsPlayed']
    split_defaults = ['k/d']
    return compile_stats(
        text=text,
        nick=nick,
        bot=bot,
        opts=PVE_OPTS,
        defaults=defaults,
        split_defaults=split_defaults,
        st_type='allPvE',
        notice=notice
    )

@hook.command('save')
def save_cache():
    output = 'Neither cache saved'
    with open('destiny_cache', 'wb') as f:
        dump(CACHE, f)
        output = ['Main cache saved']
    with open('lore_cache', 'wb') as f:
        dump(LORE_CACHE, f)
        output.append('Lore cache saved')
    return output


@hook.command('item')
def item_search(text, bot):
    '''
    Expects the tex to be a valid object in the Destiny database
    Returns the item's name and description.
    TODO: Implement error checking
    '''
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
            ', '.join([advisors['Response']['definitions']['activities'][str(nightfallActivityBundleHashId)]['skulls'][skullId]['displayName'] for skullId in advisors['Response']['data']['nightfall']['tiers'][0]['skullIndexes']])
        )
        if 'nightfall' in CACHE and output != CACHE['nightfall']:
            CACHE['last_nightfall'] = CACHE['nightfall']
        CACHE['nightfall'] = output
        return output

@hook.command('coe')
def coe(text,bot):
    if CACHE.get('coe', None) and text.lower() not in ['flush', 'clear', 'purge']:
        if 'last' in text.lower():
            return CACHE.get('last_coe', 'Unavailable')
        else:
            return CACHE['coe']
    else:
        advisors = get('{}advisors/?definitions=true'.format(BASE_URL),headers=HEADERS).json()['Response']['data']
        for activity in advisors['activities']:
            if activity['display']['advisorTypeCategory'] == 'Challenge of the Elders':
                modifiers = []
                for skullCategory in activity['extended']['skullCategories']:
                    for skull in skullCategory['skulls']:
                        modifiers.append(skull['displayName'])
                output = '\x02Challenge of the Elders\x02 - \x02Rounds:\x02 {} || \x02Modifiers:\x02 {}'.format(
                    ' // '.join(BOSS_COMBATANT_HASH[round['bossCombatantHash']] for round in activity['activityTiers'][0]['extended']['rounds']),
                    ' // '.join(modifiers)
                    )
                if 'coe' in CACHE and output != CACHE['coe']:
                    CACHE['last_coe'] = CACHE['coe']
                CACHE['coe'] = output
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
            output.append('{} days'.format(time_to_xursday.days))

        if h: output.append('{} hours'.format(h))
        if m: output.append('{} minutes'.format(m))
        if s: output.append('{} seconds'.format(s))

        return '\x02Xûr will return in\x02 {}'.format(', '.join(output))

    if CACHE.get('xur', None) and not text.lower() == 'flush':
        return CACHE['xur']

    xurStock = get(
        '{}Advisors/Xur/?definitions=true'.format(BASE_URL),
        headers=HEADERS).json()['Response']

    items = [i['item'] for i in xurStock['data']['saleItemCategories'][2]['saleItems']]
    definitions = xurStock['definitions']['items']

    output = []
    for item in items:
        item_def = definitions[str(item['itemHash'])]
        stats = []
        for stat in item['stats']:
            if stat['statHash'] in STAT_HASHES and stat['value'] > 0:
                stats.append('{}: {}'.format(STAT_HASHES[stat['statHash']], stat['value']))
        output.append('{}{}'.format(
            item_def['itemName'] if 'Engram' not in item_def['itemName'] else item_def['itemTypeName'],
            ' ({})'.format(', '.join(stats)) if stats else ''
        ))
    output = ', '.join(output)

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
    if 'complete' in text:
        complete = True
        text = text.replace('complete', '').strip()

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
                return 'I ain\'t found shit!'
            elif complete:
                notice('I found {} matches. You can choose from:'.format(len(matches)))
                for line in matches:
                    notice(line)
                return
            else:
                return ('I found {} matches, please be more specific '
                        '(e.g. {}). For a complete list use \'complete\''.format(
                            len(matches), ', '.join(matches[:3])))

    contents = LORE_CACHE[name]  # get the actual card contents
    output = strip_tags('{}: {} - {}'.format(
        name, contents.get('cardIntro', ''), contents.get('cardDescription', '')))

    if complete:
        notice(output)
        return
    elif len(output) > 300:
        output = '{}... Read more at http://www.destinydb.com/grimoire/{}'.format(
            output[:301], contents['cardId'])

    return output if len(output) > 5 else lore('', bot, notice)

@hook.command('collection')
def collection(text, nick, bot):
    text = nick if not text else text
    membership = get_user(text)
    links = CACHE['links'].get(nick)

    if type(membership) == str:
        return membership

    output = []

    for console in membership:
        grimoire = get(
            '{}Vanguard/Grimoire/{}/{}/'
            .format(BASE_URL, console, membership[console]['membershipId']),
            headers=HEADERS
        ).json()['Response']['data']
        found_frags = []
        ghosts = 0
        for card in grimoire['cardCollection']:
            if 'fragments' not in CACHE['collections']:
                # XXX: don't allow !collections to be broken
                # because of bad cache
                prepare_lore_cache()
            if card['cardId'] in CACHE['collections']['fragments']:
                found_frags.append([card['cardId']])
            elif card['cardId'] == 103094:
                ghosts = card['statisticCollection'][0]['displayValue']
                if int(ghosts) >= 99:
                    ghosts = 99

        if console == 1:
            platform = "xbl"
        else:
            platform = "psn"

        output.append('{}: Grimoire {}/{}, Ghosts {}/{}, Fragments {}/{} - {}'.format(
            CONSOLES[console - 1],
            grimoire['score'],
            CACHE['collections']['grim_tally'],
            ghosts,
            CACHE['collections']['ghost_tally'],
            len(found_frags),
            len(CACHE['collections']['fragments']),
            try_shorten('http://destinystatus.com/{}/{}/grimoire'.format(
                platform,
                links[console]
            ))
        ))
    return output

@hook.command('link')
def link(text, nick, bot, notice):
    text = text.lower().split(' ')
    err_msg = 'Invalid use of link command. Use: !link <gamertag> <xbl/psn>'

    # Check for right number of args
    if not 0 < len(text) < 3 or text[0] == '':
        notice(err_msg)
        return

    # Check that single arg is correct
    if len(text) == 1 and text[0] not in 'flush':
        notice(err_msg)
        return

    # Remove any previous cached char info
    CACHE[nick] = {}

    # If nick doesn't exist in cache, or we flush, reset cache value
    if not CACHE['links'].get(nick, None) or 'flush' in text:
        CACHE['links'][nick] = {}

    # Only give flush message if we flush
    if 'flush' in text:
        return '{} flushed from my cache'.format(nick)

    platform = text[1]
    gamertag = text[0]

    if platform not in ['psn', 'xbl']: # Check for a valid console
        notice(err_msg)
        return
    elif platform == 'psn':
        CACHE['links'][nick][2] = gamertag
        return '{} linked to {} on Playstation'.format(gamertag, nick)
    elif platform == 'xbl':
        CACHE['links'][nick][1] = gamertag
        return '{} linked to {} on Xbox'.format(gamertag, nick)
    else:
        notice(err_msg)
        return

@hook.command('migrate')
def migrate(text, nick, bot):
    if nick in ['weylin', 'avcables', 'DoctorRaptorMD[XB1]', 'tuzonghua']:
        global CACHE
        CACHE = {'links': CACHE['links']}
        return 'Sucessfully migrated! Now run the save command.'
    else:
        return 'Your light is not strong enough.'

@hook.command('purge')
def purge(text, nick, bot):
    membership = get_user(nick)

    if type(membership) is not dict:
        return membership
    user_name = nick
    output = []
    text = '' if not text else text

    if text.lower() == 'xbl' and membership.get(1, False):
        del membership[1]
        output.append('Removed Xbox from my cache on {}.'.format(user_name))
    if text.lower() == 'psn' and membership.get(2, False):
        del membership[2]
        output.append('Removed Playstation from my cache on {}.'.format(user_name))
    if not text or not membership:
        del CACHE[user_name]
        return 'Removed {}\'s characters from my cache.'.format(nick)
    else:
        CACHE[user_name] = membership
        return output if output else 'Nothing to purge. WTF you doin?!'

@hook.command('profile')
def profile(text, nick, bot):
    text = nick if not text else text
    membership = get_user(text)
    if type(membership) is not dict:
        return membership

    if membership.get(1, False):
        platform = 1
        membershipId = membership.get(1)['membershipId']
    elif membership.get(2, False):
        platform = 2
        membershipId = membership.get(2)['membershipId']
    else:
        return 'No profile!'

    bungieUserId = get(
        'http://www.bungie.net/Platform/User/GetBungieAccount/{}/{}/'.format(membershipId, platform),
        headers=HEADERS).json()['Response']['bungieNetUser']['membershipId']

    return 'https://www.bungie.net/en/Profile/254/{}'.format(bungieUserId)

@hook.command('chars')
def chars(text, nick, bot, notice):
    text = nick if not text else text
    text = text.split(' ')
    CONSOLE2ID = {"xbox": 1, "playstation": 2}

    err_msg = 'Invalid use of chars command. Use: !chars <nick> or !chars <gamertag> <psn/xbl>'

    target = compile_stats_arg_parse(text, nick)
    if target['stats'] or target['split']:
        return err_msg

    characterHash = target['user']

    if type(characterHash) is not dict:
        return 'A user by the name {} was not found.'.format(text[0])

    output = []
    for console in characterHash:
        if target['console'] and CONSOLE2ID[target['console']] != console:
            print("{0} is not {1}".format(console, target['console']))
            continue
        console_output = []
        for char in characterHash[console]['characters']:
            console_output.append('✦{} // {} // {} - {}'.format(
                characterHash[console]['characters'][char]['LL'],
                characterHash[console]['characters'][char]['class'],
                characterHash[console]['characters'][char]['race'],
                try_shorten('https://www.bungie.net/en/Legend/Gear/{}/{}/{}'.format(
                    console,
                    characterHash[console]['membershipId'],
                    char
                ))
            ))
        output.append('{}: {}'.format(
            CONSOLES[console - 1],
            ' || '.join(console_output)
        ))
    return "\x02{0}\x02: {1}".format(target['nick'], ' ; '.join(output))

@hook.command('rules')
def rules(bot):
    return 'Check \'em! https://www.reddit.com/r/DestinyTheGame/wiki/irc'

@hook.command('compare')
def compare(text, bot):
    return 'Do it your fucking self, lazy bastard!'

@hook.command('ping')
def ping(text, bot):
    return 'pong'

@hook.command('ooboo')
def ooboo(text, bot):
    return 'https://www.youtube.com/watch?v=HJKW2ZcRtMY'

@hook.command('100')
def the100(bot):
    return 'Check out our The100.io group here: https://www.the100.io/g/1151'

@hook.command('clan')
def clan(bot):
    return 'Check out our Clan: https://www.bungie.net/en/Clan/Detail/939927'

@hook.command('news')
def news(bot):
    feed = parse('https://www.bungie.net/en/Rss/NewsByCategory?category=destiny&currentpage=1&itemsPerPage=1')
    if not feed.entries:
        return 'Feed not found.'

    return '{} - {}'.format(
        feed['entries'][0]['summary'],
        try_shorten(feed['entries'][0]['link']))
