import requests
import json

from cloudbot import hook

classTypeName = {0: "Titan", 1: "Hunter", 2: "Warlock", 3:''}

@hook.command('item')
def item_search(text, bot):
    """ Expects the tex to be a valid object in the Destiny database
       Returns the item's name and description.
       TODO: Implement error checking
   """
    api_key = bot.config.get("api_keys", {}).get("destiny", None)
    HEADERS = {"X-API-Key":api_key}
    
    item = text.strip()
    itemquery = 'https://www.bungie.net/platform/Destiny/Explorer/Items?name=' + item
    itemHash = requests.get(
        itemquery, headers=HEADERS).json()['Response']['data']['itemHashes'];
 
    output = []
    for item in itemHash:        
        itemquery = 'https://www.bungie.net/platform/Destiny/Manifest/inventoryItem/' + str(item)
        result = requests.get(
            itemquery, headers=HEADERS).json()['Response']['data']['inventoryItem'];
 
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
def nightfall(bot):
    api_key = bot.config.get("api_keys", {}).get("destiny", None)
    HEADERS = {"X-API-Key":api_key}
 
    result = requests.get(
        'https://www.bungie.net/platform/destiny/advisors/?definitions=true',
        headers=HEADERS).json()
    nightfallActivityId = str(result['Response']['data']['nightfallActivityHash'])
 
    result = requests.get(
        'https://www.bungie.net/platform/destiny/manifest/activity/{}/?definitions=true'
        .format(nightfallActivityId),
        headers=HEADERS).json()
    nightfallDefinition = result['Response']['data']['activity']
 
    if len(nightfallDefinition['skulls']) == 5:
        return '\x02{}\x02 - \x1D{}\x1D \x02Modifiers:\x02 {}, {}, {}'.format(
            nightfallDefinition['activityName'],
            nightfallDefinition['activityDescription'],
            nightfallDefinition['skulls'][1]['displayName'],
            nightfallDefinition['skulls'][2]['displayName'],
            nightfallDefinition['skulls'][3]['displayName']
        )
    else:
        return 'weylin lied to me, get good scrub.'

@hook.command('weekly')
def weekly(bot):
    api_key = bot.config.get("api_keys", {}).get("destiny", None)
    HEADERS = {"X-API-Key":api_key}
    
    weeklyHeroicId = requests.get(
        'https://www.bungie.net/platform/destiny/advisors/?definitions=true',
        headers=HEADERS).json()['Response']['data']['heroicStrike']['activityBundleHash']
 
    weeklyHeroicDefinition = requests.get(
        'https://www.bungie.net/platform/destiny/manifest/activity/{}/?definitions=true'
        .format(weeklyHeroicId),
        headers=HEADERS).json()['Response']['data']['activity']
    weeklyHeroicSkullIndex = weeklyHeroicDefinition['skulls']
 
    if len(weeklyHeroicSkullIndex) == 2:
        return '\x02{}\x02 - \x1D{}\x1D \x02Modifier:\x02 {}'.format(
            weeklyHeroicDefinition['activityName'],
            weeklyHeroicDefinition['activityDescription'],
            weeklyHeroicDefinition['skulls'][1]['displayName']
        )
    else:
        return 'weylin lied to me, get good scrub.'
        

@hook.command('triumph')
def triumph(text, bot):
    HEADERS = {"X-API-Key": bot.config.get("api_keys", {}).get("destiny", None)} 

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
 
    userID = requests.get(
        "http://www.bungie.net/Platform/User/SearchUsers/?q={}"
        .format(text.strip()),
        headers=HEADERS).json()['Response'][0]
    userIDHash = userID['membershipId']
    userName = userID['displayName']
 
    userHash = requests.get(
        "https://www.bungie.net/platform/User/GetBungieAccount/{}/254/"
        .format(userIDHash),
        headers=HEADERS).json()['Response']['destinyAccounts'][0]['userInfo']
    membershipType = userHash['membershipType']
    membershipId = userHash['membershipId']
 
    consoles = ['Xbox', 'Playstation']
    output = []
    membershipType = [membershipType] if type(membershipType) == int else membershipType
    for membership in membershipType:
        triumphHash = requests.get(
            "https://www.bungie.net/platform/Destiny/{}/Account/{}/Triumphs/"
            .format(membership, membershipId),
            headers=HEADERS
        ).json()['Response']['data']['triumphSets'][0]['triumphs']
 
        remaining = []
        for i in range(10):
            if not triumphHash[i]['complete']:
                remaining.append(triumphText[i])
 
        if len(remaining) == 0:
            output.append(
                "\x02{}\'s\x02 Year One Triumph is complete on {}!".format(
                    userName, consoles[membership - 1]))
        else:
            output.append(
                "\x02{}\'s\x02 Year One Triumph is not complete on {}. "
                "\x02Remaining task(s):\x02 {}".format(
                    userName, consoles[membership - 1], ', '.join(remaining)))
 
    return output

@hook.command('xur')
def xur(text, bot):
    api_key = bot.config.get("api_keys", {}).get("destiny", None)
    HEADERS = {"X-API-Key":api_key}

    r = requests.get("https://www.bungie.net/platform/Destiny/Advisors/Xur/?definitions=true", headers=HEADERS);

    xurStock = r.json()

    xurExoticHash0 = str(xurStock['Response']['data']['saleItemCategories'][0]['saleItems'][0]['item']['itemHash'])

    xurExoticName01 = str(xurStock['Response']['definitions']['items'][xurExoticHash0]['itemName'])

    xurExoticStatHash01 = str(xurStock['Response']['data']['saleItemCategories'][0]['saleItems'][0]['item']['stats'][1]['statHash'])
    xurExoticStatName01 = str(xurStock['Response']['definitions']['stats'][xurExoticStatHash01]['statName'])
    xurExoticStatValue01 = str(xurStock['Response']['data']['saleItemCategories'][0]['saleItems'][0]['item']['stats'][1]['value'])


    xurExoticStatHash02 = str(xurStock['Response']['data']['saleItemCategories'][0]['saleItems'][0]['item']['stats'][2]['statHash'])
    xurExoticStatName02 = str(xurStock['Response']['definitions']['stats'][xurExoticStatHash02]['statName'])
    xurExoticStatValue02 = str(xurStock['Response']['data']['saleItemCategories'][0]['saleItems'][0]['item']['stats'][2]['value'])


    xurExoticStatHash03 = str(xurStock['Response']['data']['saleItemCategories'][0]['saleItems'][0]['item']['stats'][3]['statHash'])
    xurExoticStatName03 = str(xurStock['Response']['definitions']['stats'][xurExoticStatHash03]['statName'])
    xurExoticStatValue03 = str(xurStock['Response']['data']['saleItemCategories'][0]['saleItems'][0]['item']['stats'][3]['value'])


    xurExoticStatName0 = xurStock['Response']['definitions']['stats'][xurExoticStatHash01]['statName']


    xurExoticHash1 = str(xurStock['Response']['data']['saleItemCategories'][0]['saleItems'][1]['item']['itemHash'])

    xurExoticName11 = str(xurStock['Response']['definitions']['items'][xurExoticHash1]['itemName'])

    xurExoticStatHash11 = str(xurStock['Response']['data']['saleItemCategories'][0]['saleItems'][1]['item']['stats'][1]['statHash'])
    xurExoticStatName11 = str(xurStock['Response']['definitions']['stats'][xurExoticStatHash11]['statName'])
    xurExoticStatValue11 = str(xurStock['Response']['data']['saleItemCategories'][0]['saleItems'][1]['item']['stats'][1]['value'])

    xurExoticStatHash12 = str(xurStock['Response']['data']['saleItemCategories'][0]['saleItems'][1]['item']['stats'][2]['statHash'])
    xurExoticStatName12 = str(xurStock['Response']['definitions']['stats'][xurExoticStatHash12]['statName'])
    xurExoticStatValue12 = str(xurStock['Response']['data']['saleItemCategories'][0]['saleItems'][1]['item']['stats'][2]['value'])

    xurExoticStatHash13 = str(xurStock['Response']['data']['saleItemCategories'][0]['saleItems'][1]['item']['stats'][3]['statHash'])
    xurExoticStatName13 = str(xurStock['Response']['definitions']['stats'][xurExoticStatHash13]['statName'])
    xurExoticStatValue13 = str(xurStock['Response']['data']['saleItemCategories'][0]['saleItems'][1]['item']['stats'][3]['value'])

    xurExoticStatName1 = xurStock['Response']['definitions']['stats'][xurExoticStatHash11]['statName']


    xurExoticHash2 = str(xurStock['Response']['data']['saleItemCategories'][0]['saleItems'][2]['item']['itemHash'])

    xurExoticName21 = str(xurStock['Response']['definitions']['items'][xurExoticHash2]['itemName'])

    xurExoticStatHash21 = str(xurStock['Response']['data']['saleItemCategories'][0]['saleItems'][2]['item']['stats'][1]['statHash'])
    xurExoticStatName21 = str(xurStock['Response']['definitions']['stats'][xurExoticStatHash21]['statName'])
    xurExoticStatValue21 = str(xurStock['Response']['data']['saleItemCategories'][0]['saleItems'][2]['item']['stats'][1]['value'])

    xurExoticStatHash22 = str(xurStock['Response']['data']['saleItemCategories'][0]['saleItems'][2]['item']['stats'][2]['statHash'])
    xurExoticStatName22 = str(xurStock['Response']['definitions']['stats'][xurExoticStatHash22]['statName'])
    xurExoticStatValue22 = str(xurStock['Response']['data']['saleItemCategories'][0]['saleItems'][2]['item']['stats'][2]['value'])

    xurExoticStatHash23 = str(xurStock['Response']['data']['saleItemCategories'][0]['saleItems'][2]['item']['stats'][3]['statHash'])
    xurExoticStatName23 = str(xurStock['Response']['definitions']['stats'][xurExoticStatHash23]['statName'])
    xurExoticStatValue23 = str(xurStock['Response']['data']['saleItemCategories'][0]['saleItems'][2]['item']['stats'][3]['value'])

    xurExoticStatName2 = xurStock['Response']['definitions']['stats'][xurExoticStatHash21]['statName']

    xurExoticHash3 = str(xurStock['Response']['data']['saleItemCategories'][0]['saleItems'][3]['item']['itemHash'])
    xurExoticName31 = str(xurStock['Response']['definitions']['items'][xurExoticHash3]['itemName'])

    xurExoticHash4 = str(xurStock['Response']['data']['saleItemCategories'][0]['saleItems'][5]['item']['itemHash'])
    xurExoticName41 = str(xurStock['Response']['definitions']['items'][xurExoticHash4]['itemTypeName'])

    return '\x030,1 Armor \x030,14 ' + xurExoticName01 + ' (' + xurExoticStatName01[:3] + ': ' + xurExoticStatValue01 + ', ' + xurExoticStatName02[:3] + ': ' + xurExoticStatValue02 + ', ' + xurExoticStatName03[:3] + ': ' + xurExoticStatValue03 + ')' + ', ' + xurExoticName11 + ' (' + xurExoticStatName11[:3] + ': ' + xurExoticStatValue11 + ', ' + xurExoticStatName12[:3] + ': ' + xurExoticStatValue12 + ', ' + xurExoticStatName13[:3] + ': ' + xurExoticStatValue13 + ')' + ', ' + xurExoticName21 + ' (' + xurExoticStatName21[:3] + ': ' + xurExoticStatValue21 + ', ' + xurExoticStatName22[:3] + ': ' + xurExoticStatValue22 + ', ' + xurExoticStatName23[:3] + ': ' + xurExoticStatValue23 + ') ' + '\x030,1 Weapon \x030,14 ' + xurExoticName31 + ' \x030,1 Engram \x030,14 ' + xurExoticName41
    
@hook.command('xur2')
def xur2(text, bot):
    api_key = bot.config.get("api_keys", {}).get("destiny", None)
    HEADERS = {"X-API-Key":api_key}

    xurStock = get(
        "https://www.bungie.net/platform/Destiny/Advisors/Xur/?definitions=true",
        headers=HEADERS).json()['Response']

    hashes = xurStock['data']['saleItemCategories'][0]['saleItems']
    text = xurStock['definitions']
    keys = [key for key in hashes]

    armor_list = []
    for i in range(3):
        exotic = '{} ({}: {}, {}: {}, {}: {})'.format(
            text['items'][hashes[keys[i]]['item']['itemHash']]['itemName'],
            text['definitions']['stats'][hashes[keys[i]]['item']['stats'][1]['statHash']]['statName'][:3],
            hashes[keys[i]]['item']['stats'][1]['value'],
            text['definitions']['stats'][hashes[keys[i]]['item']['stats'][2]['statHash']]['statName'][:3],
            hashes[keys[i]]['item']['stats'][2]['value'],
            text['definitions']['stats'][hashes[keys[i]]['item']['stats'][3]['statHash']]['statName'][:3],
            hashes[keys[i]]['item']['stats'][3]['value']
        )
        armor_list.append(exotic)
    weapon = text['items'][hashes[keys[3]]['item']['itemHash']]['itemName']
    engram = text['items'][hashes[keys[4]]['item']['itemHash']]['itemName']

    return '\x030,1 Armor \x030,14 {}; \x030,1 Weapon \x030,14 {}; \x030,1 Engram \x030,14 {}'.format(
        ', '.join(armor_list), weapon, engram) 







