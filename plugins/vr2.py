import requests
from cloudbot import hook

STEAM_LOOKUP = 'http://store.steampowered.com/api/appdetails?appids='
VR_LOBBY_URL = 'https://api.vrlobby.net/v1/getcurrentcounts'

def get_game_name_by_id(game_id):
    return requests.get(STEAM_LOOKUP + game_id).json()[game_id]['data']['name']
    
@hook.command('mpvr')
def mpvr(text):
    response = requests.get(VR_LOBBY_URL)
    data = response.json()
    
    not_vr_games = ['365960', '457550', '438100', '244210', '218620', '378860', '570', '346110', '359320', '286160', '234630', '310560', '211500', '223750', '307960', '266410', '375900', '517710', '332490', '582500', '233610', '393430', '476480', '360970']
    full_list = data['body']['Items'][0]['counts'].split(",")

    game_id_to_player_count = dict([entry.split(":") for entry in full_list if entry.split(":")[0] not in not_vr_games][:10])
    game_name_to_player_count = {get_game_name_by_id(game_id): player_count
                                 for game_id, player_count in game_id_to_player_count.items()}
    sorted_games = sorted(game_name_to_player_count.items(), reverse=True, key=lambda item: int(item[1]))
    return ', '.join('\x02%s\x02: %s' % (game_name, player_count) for game_name, player_count in sorted_games)
