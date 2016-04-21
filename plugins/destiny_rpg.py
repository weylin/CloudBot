import random
from cloudbot import hook
from operator import itemgetter
from time import time
from tinydb import TinyDB, Query

SPACE_MAGIC = "☆*✲ﾟ*｡｡*ﾟ✲*☆"
EVENTS = [
    "A Taken Lieutenant is corrupting the area",
    "A Pack of Wolves is prowling",
    "The Blades of Crota have invaded this world",
    "A Warsat has dropped from orbit",
    "Fallen Skiffs inbound",
    "A high value target has been spotted nearby",
    "A Devil Walker has dropped"]


def new_player(nick):
    global PLAYERS
    new_eid = PLAYERS.insert({
        'nick': nick, 'events': 0, 'xp': 0,
        'level': 0, 'streak': 0, 'penalty': 0
    })
    return PLAYERS.get(eid=new_eid)


def add_xp(xp, user):
    global PLAYERS, PLAYER_Q
    player = PLAYERS.get(PLAYER_Q.nick == user)
    if not player:
        player = new_player(user)

    player['xp'] += xp
    player['events'] += 1
    player['streak'] += 1
    levelled_up = False
    if player['xp'] >= 1000:
        levelled_up = True
        player['level'] += 1
        player['xp'] -= 1000
    # update the DB
    PLAYERS.update(player, eids=[player.eid])
    return "{} gained {}xp{}!".format(
        user, xp, " and levelled up!" if levelled_up else "")


def hit_or_miss(deploy, shoot):
    """Calculates if the action will be successful."""
    if shoot - deploy < 1:
        return .05
    elif 1 <= shoot - deploy <= 7:
        out = random.uniform(.60, .75)
        return out
    else:
        return 1


def set_event_time(channel):
    global GAME, GAME_Q
    curr_game = GAME.get(GAME_Q.channel == channel)
    curr_game['event_time'] = random.randint(
        int(time()) + 1800, int(time()) + 3600)
    curr_game['event_status'] = False
    GAME.update(curr_game, eids=[curr_game.eid])


def generate_event():
    """Try and randomize the event message so people can't highlight on it/script against it."""
    lt = SPACE_MAGIC[:random.randint(1, len(SPACE_MAGIC) - 1)] + ' '
    rt = ' ' + SPACE_MAGIC[random.randint(1, len(SPACE_MAGIC) - 1):]
    eb = random.choice(EVENTS)
    return (lt, eb, rt)


@hook.on_start()
def load_cache(bot):
    """Load in/create our database, tables, and query objects."""
    global GAME, PLAYERS, GAME_Q, PLAYER_Q
    db = TinyDB('destiny_rpg.json')
    GAME = db.table('game')
    PLAYERS = db.table('players')
    GAME_Q = Query()
    PLAYER_Q = Query()


@hook.command("startgame", autohelp=False, permissions=["op"])
def start_game(bot, chan, message, conn):
    """Start Destiny in your channel, to stop the game use .stopgame"""
    global GAME, GAME_Q
    if not chan.startswith("#"):
        return "Where is your fireteam guardian?"
    curr_game = GAME.get(GAME_Q.channel == chan)
    if not curr_game:
        GAME.insert({
            'channel': chan, 'game_on': True, 'network': conn.name,
            'event_status': False, 'event_time': time()
        })
    elif curr_game['game_on']:
        return "there is already a game running in {}.".format(chan)
    else:
        GAME.update({'game_on': True}, eids=[curr_game.eid])
    set_event_time(channel=chan)
    message("Destiny has been loaded into this channel.")


@hook.command("stopgame", autohelp=False, permissions=["op"])
def stop_game(chan, conn):
    """Stop Destiny in your channel. Scores will be preserved"""
    global GAME, GAME_Q
    curr_game = GAME.get(GAME_Q.channel == chan)
    if curr_game['game_on']:
        GAME.update({'game_on': False}, eids=[curr_game.eid])
        return "Destiny has been stopped."
    else:
        return "Destiny is not running in {}.".format(chan)


@hook.periodic(15, initial_interval=15)
def spawn_event(message, bot):
    global GAME, GAME_Q
    for curr_game in GAME.all():
        if not curr_game['game_on']:
            return
        conn = bot.connections[curr_game['network']]
        if curr_game['event_status'] is False and curr_game['event_time'] <= time():
            curr_game['event_status'] = True
            curr_game['event_time'] = time()
            lt, eb, rt = generate_event()
            curr_game['event_type'] = eb
            curr_game['players_linked'] = []
            GAME.update(curr_game, eids=[curr_game.eid])
            conn.message(curr_game['channel'], '{}{}{}'.format(lt, eb, rt))
        elif curr_game['event_status'] is True:
            if time() - curr_game['event_time'] >= 120:
                set_event_time(channel=curr_game['channel'])
                conn.message(curr_game['channel'], "The Darkness subsides.")


@hook.command("bang", autohelp=False)
def bang(nick, chan, message, conn, notice):
    """When there is a target on the loose use this command to shoot it."""
    global GAME, PLAYERS, GAME_Q, PLAYER_Q
    out = ""
    miss = [
        "WHOOSH! You missed the shot completely!",
        "You are out of ammo. You pop a synth instead.",
        "Error code: Baboon.",
        "You were stopped by The Architects.",
        "You had a misadventure.",
        "The Darkness consumed you."]
    player = PLAYERS.get(PLAYER_Q.nick == nick)
    curr_game = GAME.get(GAME_Q.channel == chan)
    if not player:
        player = new_player(nick)
    if not curr_game['game_on']:
        return "There is no active game right now. Use .startgame to start a game."
    elif curr_game['event_status'] is not True:
        out = "KICK {} {} Eyes up, Guardian. There is no active event! Returning to orbit.".format(chan, nick)
        PLAYERS.update({'streak': 0}, eids=[player.eid])
        conn.send(out)
        return
    else:
        correct = False
        for event_type in ['Taken', 'Pack', 'Blades']:
            if event_type in curr_game['event_type']:
                correct = True
        if not correct:
            out = "KICK {} {} You used the wrong action for this event! Returning to orbit.".format(chan, nick)
            PLAYERS.update({'streak': 0}, eids=[player.eid])
            conn.send(out)
            return
        curr_game['action_time'] = time()
        deploy = curr_game['event_time']
        shoot = curr_game['action_time']
        if player['penalty'] > shoot:
            notice("You are in a cool down period, you can try again in {} seconds.".format(player['penalty'] - shoot))
            return
        chance = hit_or_miss(deploy, shoot)
        if not random.random() <= chance and chance > .05:
            out = random.choice(miss) + " You can try again in 7 seconds."
            player['penalty'] = shoot + 7
            PLAYERS.update(player, eids=[player.eid])
            return out
        if chance == .05:
            out += "You pulled the trigger in {} seconds, that's mighty fast. Are you sure you aren't a script? Take a 2 hour cool down.".format(shoot - deploy)
            player['penalty'] = shoot + 7200
            if not random.random() <= chance:
                return random.choice(miss) + " " + out
            else:
                message(out)
        curr_game['event_status'] = False
        GAME.update(curr_game, eids=[curr_game.eid])
        PLAYERS.update(player, eids=[player.eid])
        timer = shoot - deploy
        message("{} you completed the event in {} seconds! {}".format(nick, round(timer, 2), add_xp(150, nick)))
        set_event_time(channel=curr_game['channel'])


@hook.command("defend", autohelp=False)
def defend(nick, chan, message, conn, notice):
    """When there is a skiff or warsat, use defend to help defeat it."""
    global GAME, PLAYERS, GAME_Q, PLAYER_Q
    out = ""
    player = PLAYERS.get(PLAYER_Q.nick == nick)
    curr_game = GAME.get(GAME_Q.channel == chan)
    if not player:
        player = new_player(nick)
    if not curr_game['game_on']:
        return "There is no active game right now. Use .startgame to start a game."
    elif curr_game['event_status'] is not True:
        out = "KICK {} {} Eyes up, Guardian. There is no active event! Returning to orbit.".format(chan, nick)
        PLAYERS.update({'streak': 0}, eids=[player.eid])
        conn.send(out)
        return
    else:
        correct = False
        for event_type in ['Warsat', 'Skiff']:
            if event_type in curr_game['event_type']:
                correct = True
        if not correct:
            out = "KICK {} {} You used the wrong action for this event! Returning to orbit.".format(chan, nick)
            PLAYERS.update({'streak': 0}, eids=[player.eid])
            conn.send(out)
            return
        curr_game['action_time'] = time()
        shoot = curr_game['action_time']
        if player['penalty'] > shoot:
            notice("You are in a cool down period, you can try again in {} seconds.".format(player['penalty'] - shoot))
            return
        timer = shoot - curr_game['event_time']
        if timer <= 1:
            out += "You joined in {} seconds, that's mighty fast. Are you sure you aren't a script? Take a 2 hour cool down.".format(timer)
            player['penalty'] = shoot + 7200
            message(out)

        if len(curr_game['players_linked']) >= 5:
            message("{} you are too late, the event has already ended.".format(nick))
            set_event_time(channel=curr_game['channel'])
        elif timer >= 10:
            if not curr_game['players_linked']:
                message("{} you completed the event in {} seconds! {}".format(nick, round(timer, 2), add_xp(50, nick)))
                set_event_time(channel=curr_game['channel'])
            else:
                message("{} you are too late, the event is over.".format(nick))
                set_event_time(channel=curr_game['channel'])
            set_event_time(channel=curr_game['channel'])
        elif nick in curr_game['players_linked']:
            message("You are already in the event. Padding your numbers lost you 100xp!")
            player['xp'] -= 100
        else:
            message("{} you joined the event in {} seconds! {}".format(nick, round(timer, 2), add_xp(75, nick)))
            curr_game['players_linked'].append(nick)
            GAME.update(curr_game, eids=[curr_game.eid])
        PLAYERS.update(player, eids=[player.eid])


@hook.command("assault", autohelp=False)
def assault(nick, chan, message, conn, notice):
    """When there is a high value target or walker, use assault to help defeat it."""
    global GAME, PLAYERS, GAME_Q, PLAYER_Q
    out = ""
    player = PLAYERS.get(PLAYER_Q.nick == nick)
    curr_game = GAME.get(GAME_Q.channel == chan)
    if not player:
        player = new_player(nick)
    if not curr_game['game_on']:
        return "There is no active game right now. Use .startgame to start a game."
    elif curr_game['event_status'] is not True:
        out = "KICK {} {} Eyes up, Guardian. There is no active event! Returning to orbit.".format(chan, nick)
        PLAYERS.update({'streak': 0}, eids=[player.eid])
        conn.send(out)
        return
    else:
        correct = False
        for event_type in ['Walker', 'target']:
            if event_type in curr_game['event_type']:
                correct = True
        if not correct:
            out = "KICK {} {} You used the wrong action for this event! Returning to orbit.".format(chan, nick)
            PLAYERS.update({'streak': 0}, eids=[player.eid])
            conn.send(out)
            return
        curr_game['action_time'] = time()
        shoot = curr_game['action_time']
        if player['penalty'] > shoot:
            notice("You are in a cool down period, you can try again in {} seconds.".format(player['penalty'] - shoot))
            return
        timer = shoot - curr_game['event_time']
        if timer <= 1:
            out += "You joined in {} seconds, that's mighty fast. Are you sure you aren't a script? Take a 2 hour cool down.".format(timer)
            player['penalty'] = shoot + 7200
            message(out)

        if len(curr_game['players_linked']) >= 3:
            message("{} you are too late, the event is full.".format(nick))
            set_event_time(channel=curr_game['channel'])
        elif timer >= 10:
            if not curr_game['players_linked']:
                message("{} you completed the event in {} seconds! {}".format(nick, round(timer, 2), add_xp(75, nick)))
                set_event_time(channel=curr_game['channel'])
            else:
                message("{} you are too late, the event is over.".format(nick))
                set_event_time(channel=curr_game['channel'])
        elif nick in curr_game['players_linked']:
            message("You are already in the event. Padding your numbers lost you 100xp!")
            player['xp'] -= 100
        else:
            message("{} you joined the event in {} seconds! {}".format(nick, round(timer, 2), add_xp(100, nick)))
            curr_game['players_linked'].append(nick)
            GAME.update(curr_game, eids=[curr_game.eid])
        PLAYERS.update(player, eids=[player.eid])


@hook.command("leaders", autohelp=False)
def leaders(text, chan, conn, db):
    """Print a list of the top event leaders in the channel."""
    p_list = {}
    for player in PLAYERS.all():
        p_list[player['nick']] = player['level'] * 1000 + player['xp']
    # to increase the number of leaders returned, change the last number
    p_list = sorted(p_list.items(), key=itemgetter(1), reverse=True)[:7]
    top = []
    for leader in p_list:
        top.append(leader[0])
    return "The top {} leaders are {}".format(len(top), ", ".join(top))


@hook.command("events", autohelp=False)
def events_stats(text, nick, chan, conn, message):
    """Print a user's events stats."""
    name = nick
    if text:
        name = text.split()[0]
    player = PLAYERS.get(PLAYER_Q.nick == name)
    if player:
        message("{} has completed {} events, with a streak of {}. "
                "{}xp to level {}.".format(
                    name, player['events'], player['streak'],
                    1000 - player['xp'], player['level'] + 1))
    else:
        return "{} has not completed any events.".format(name)
