import random
from cloudbot import hook
from time import time
from operator import itemgetter
from pickle import dump, load

PLAYERS = {}  # {'DoctorRaptorMD[XB1]': {'events', 'xp', 'level'}}
GAME = {
    'network': None,
    'channel': None,
    'game_on': False,
    'next_event': None,
    'event_status': False,
    'players_linked': [],
    'event_time': 0.0,
    'action_time': None}
SPACE_MAGIC = "☆*✲ﾟ*｡｡*ﾟ✲*☆"
EVENTS = [
    "A Taken Lieutenant is corrupting the area",
    "A Pack of Wolves is prowling",
    "The Blades of Crota have invaded this world",
    "A Warsat has dropped from orbit",
    "Fallen Skiffs inbound",
    "A high value target has been spotted nearby",
    "A Devil Walker has dropped"]
SCRIPTERS = {}


def new_player(nick):
    PLAYERS[nick] = {'events': 0, 'xp': 0, 'level': 0, 'streak': 0}


def add_xp(xp, user):
    global PLAYERS
    if not PLAYERS.get(user, None):
        new_player(user)

    PLAYERS[user]['xp'] += xp
    PLAYERS[user]['events'] += 1
    PLAYERS[user]['streak'] += 1
    levelled_up = False
    if PLAYERS[user]['xp'] >= 1000:
        levelled_up = True
        PLAYERS[user]['level'] += 1
        PLAYERS[user]['xp'] -= 1000
    return "{} gained {}xp{}!".format(
        user, xp, " and levelled up!" if levelled_up else "")


def hit_or_miss(deploy, shoot):
    """This function calculates if the action will be successful."""
    if shoot - deploy < 1:
        return .05
    elif 1 <= shoot - deploy <= 7:
        out = random.uniform(.60, .75)
        return out
    else:
        return 1


def set_event_time():
    global GAME
    GAME['event_time'] = random.randint(int(time()) + 900, int(time()) + 3600)
    GAME['event_status'] = False
    return


def generate_event():
    """Try and randomize the event message so people can't highlight on it/script against it."""
    lt = SPACE_MAGIC[:random.randint(1, len(SPACE_MAGIC) - 1)] + ' '
    rt = ' ' + SPACE_MAGIC[random.randint(1, len(SPACE_MAGIC) - 1):]
    eb = random.choice(EVENTS)
    return (lt, eb, rt)


@hook.on_start()
def load_cache(bot):
    """Load in our pickled content"""
    try:
        with open('destiny_rpg', 'rb') as f:
            global PLAYERS
            PLAYERS = load(f)  # and the pickles!!!
    except EOFError:
        PLAYERS = {}


@hook.command('save_game', autohelp=False, permissions=["op"])
def save_game(message):
    with open('destiny_rpg', 'wb') as f:
        dump(PLAYERS, f)
        message("Game Saved")


@hook.command("startgame", autohelp=False, permissions=["op"])
def start_game(bot, chan, message, conn):
    """This command starts Destiny in your channel, to stop the game use .stopgame"""
    global GAME
    if not chan.startswith("#"):
        return "Where is your fireteam guardian?"
    if GAME['game_on']:
        return "there is already a game running in {}.".format(chan)
    else:
        GAME['game_on'] = True
        GAME['network'] = conn.name
        GAME['channel'] = chan
    set_event_time()
    message("Destiny has been loaded into this channel.")


@hook.command("stopgame", autohelp=False, permissions=["op"])
def stop_game(chan, conn):
    """This command stops Destiny in your channel. Scores will be preserved"""
    global GAME
    if GAME['game_on']:
        GAME['game_on'] = False
        return "Destiny has been stopped."
    else:
        return "Destiny is not running in {}.".format(chan)


@hook.periodic(11, initial_interval=11)
def spawn_event(message, bot):
    global GAME
    active = GAME['game_on']
    event_status = GAME['event_status']
    next_event = GAME['event_time']
    if active is True and event_status is False and next_event <= time():
        GAME['event_status'] = True
        GAME['event_time'] = time()
        lt, eb, rt = generate_event()
        GAME['event_type'] = eb
        GAME['players_linked'] = []
        conn = bot.connections[GAME['network']]
        conn.message(GAME['channel'], '{}{}{}'.format(lt, eb, rt))


@hook.command("bang", autohelp=False)
def bang(nick, chan, message, conn, notice):
    """when there is a target on the loose use this command to shoot it."""
    global GAME, SCRIPTERS
    out = ""
    miss = [
        "WHOOSH! You missed the shot completely!",
        "You are out of ammo. You pop a synth instead.",
        "Error code: Baboon.",
        "You were stopped by The Architects.",
        "You had a misadventure.",
        "The Darkness consumed you."]
    if not GAME['game_on']:
        return "There is no active game right now. Use .startgame to start a game."
    elif GAME['event_status'] is not True:
        out = "KICK {} {} Eyes up, Guardian. There is no active event! Returning to orbit.".format(chan, nick)
        if PLAYERS.get(nick, None):
            PLAYERS[nick]['streak'] = 0
        conn.send(out)
        return
    else:
        correct = False
        for event_type in ['Taken', 'Pack', 'Blades']:
            if event_type in GAME['event_type']:
                correct = True
        if not correct:
            out = "KICK {} {} You used the wrong action for this event! Returning to orbit.".format(chan, nick)
            if PLAYERS.get(nick, None):
                PLAYERS[nick]['streak'] = 0
            conn.send(out)
            return
        GAME['action_time'] = time()
        deploy = GAME['event_time']
        shoot = GAME['action_time']
        if nick.lower() in SCRIPTERS:
            if SCRIPTERS[nick.lower()] > shoot:
                notice("You are in a cool down period, you can try again in {} seconds.".format(SCRIPTERS[nick.lower()] - shoot))
                return
        chance = hit_or_miss(deploy, shoot)
        if not random.random() <= chance and chance > .05:
            out = random.choice(miss) + " You can try again in 7 seconds."
            SCRIPTERS[nick.lower()] = shoot + 7
            return out
        if chance == .05:
            out += "You pulled the trigger in {} seconds, that's mighty fast. Are you sure you aren't a script? Take a 2 hour cool down.".format(shoot - deploy)
            SCRIPTERS[nick.lower()] = shoot + 7200
            if not random.random() <= chance:
                return random.choice(miss) + " " + out
            else:
                message(out)
        GAME['event_status'] = False
        timer = shoot - deploy
        message("{} you completed the event in {} seconds! {}".format(nick, round(timer, 2), add_xp(150, nick)))
        set_event_time()


@hook.command("defend", autohelp=False)
def defend(nick, chan, message, conn, notice):
    """when there is a skiff or warsat, use defend to help defeat it."""
    global GAME, SCRIPTERS
    out = ""
    if not GAME['game_on']:
        return "There is no active game right now. Use .startgame to start a game."
    elif GAME['event_status'] is not True:
        out = "KICK {} {} Eyes up, Guardian. There is no active event! Returning to orbit.".format(chan, nick)
        if PLAYERS.get(nick, None):
            PLAYERS[nick]['streak'] = 0
        conn.send(out)
        return
    else:
        correct = False
        for event_type in ['Warsat', 'Skiff']:
            if event_type in GAME['event_type']:
                correct = True
        if not correct:
            out = "KICK {} {} You used the wrong action for this event! Returning to orbit.".format(chan, nick)
            if PLAYERS.get(nick, None):
                PLAYERS[nick]['streak'] = 0
            conn.send(out)
            return
        GAME['action_time'] = time()
        deploy = GAME['event_time']
        shoot = GAME['action_time']
        if nick.lower() in SCRIPTERS:
            if SCRIPTERS[nick.lower()] > shoot:
                notice("You are in a cool down period, you can try again in {} seconds.".format(str(SCRIPTERS[nick.lower()] - shoot)))
                return
        timer = shoot - deploy
        if timer <= 1:
            out += "You joined in {} seconds, that's mighty fast. Are you sure you aren't a script? Take a 2 hour cool down.".format(timer)
            SCRIPTERS[nick.lower()] = shoot + 7200
            message(out)

        if len(GAME['players_linked']) >= 5:
            message("{} you are too late, the event has already ended.".format(nick))
            GAME['event_status'] = False
            set_event_time()
        elif timer >= 10:
            if not GAME['players_linked']:
                message("{} you completed the event in {} seconds! {}".format(nick, round(timer, 2), add_xp(50, nick)))
                GAME['event_status'] = False
                set_event_time()
            else:
                message("{} you are too late, the event is over.".format(nick))
                GAME['event_status'] = False
                set_event_time()
            set_event_time()
        elif nick in GAME['players_linked']:
            message("You are already in the event. Padding your numbers lost you 100xp!")
            PLAYERS[nick]['xp'] -= 100
        else:
            message("{} you joined the event in {} seconds! {}".format(nick, round(timer, 2), add_xp(75, nick)))
            GAME['players_linked'].append(nick)


@hook.command("assault", autohelp=False)
def assault(nick, chan, message, conn, notice):
    """when there is a high value target or walker, use assault to help defeat it."""
    global GAME, SCRIPTERS
    out = ""
    if not GAME['game_on']:
        return "There is no active game right now. Use .startgame to start a game."
    elif GAME['event_status'] is not True:
        out = "KICK {} {} Eyes up, Guardian. There is no active event! Returning to orbit.".format(chan, nick)
        if PLAYERS.get(nick, None):
            PLAYERS[nick]['streak'] = 0
        conn.send(out)
        return
    else:
        correct = False
        for event_type in ['Walker', 'target']:
            if event_type in GAME['event_type']:
                correct = True
        if not correct:
            out = "KICK {} {} You used the wrong action for this event! Returning to orbit.".format(chan, nick)
            if PLAYERS.get(nick, None):
                PLAYERS[nick]['streak'] = 0
            conn.send(out)
            return
        GAME['action_time'] = time()
        deploy = GAME['event_time']
        shoot = GAME['action_time']
        if nick.lower() in SCRIPTERS:
            if SCRIPTERS[nick.lower()] > shoot:
                notice("You are in a cool down period, you can try again in {} seconds.".format(str(SCRIPTERS[nick.lower()] - shoot)))
                return
        timer = shoot - deploy
        if timer <= 1:
            out += "You joined in {} seconds, that's mighty fast. Are you sure you aren't a script? Take a 2 hour cool down.".format(timer)
            SCRIPTERS[nick.lower()] = shoot + 7200
            message(out)

        if len(GAME['players_linked']) >= 3:
            message("{} you are too late, the event is full.".format(nick))
            GAME['event_status'] = False
            set_event_time()
        elif timer >= 10:
            if not GAME['players_linked']:
                message("{} you completed the event in {} seconds! {}".format(nick, round(timer, 2), add_xp(75, nick)))
                GAME['event_status'] = False
                set_event_time()
            else:
                message("{} you are too late, the event is over.".format(nick))
                GAME['event_status'] = False
                set_event_time()
        elif nick in GAME['players_linked']:
            message("You are already in the event. Padding your numbers lost you 100xp!")
            PLAYERS[nick]['xp'] -= 100
        else:
            message("{} you joined the event in {} seconds! {}".format(nick, round(timer, 2), add_xp(100, nick)))
            GAME['players_linked'].append(nick)


@hook.command("leaders", autohelp=False)
def leaders(text, chan, conn, db):
    """Prints a list of the top event leaders in the channel."""
    p_list = {}
    for player in PLAYERS:
        p_list[player] = PLAYERS[player]['level'] * 1000 + PLAYERS[player]['xp']
    # to increase the number of leaders returned, change the last number
    p_list = sorted(p_list.items(), key=itemgetter(1), reverse=True)[:7]
    top = []
    for leader in p_list:
        top.append(leader[0])
    return "The top {} leaders are {}".format(len(top), ", ".join(top))


@hook.command("events", autohelp=False)
def events_stats(text, nick, chan, conn, message):
    """Prints a user's events stats."""
    name = nick
    if text:
        name = text.split()[0]
    if PLAYERS.get(name, None):
        message("{} has completed {} events, with a streak of {}. "
                "{}xp to level {}.".format(
                    name, PLAYERS[name]['events'], PLAYERS[name]['streak'],
                    1000 - PLAYERS[name]['xp'], PLAYERS[name]['level'] + 1))
    else:
        return "{} has not completed any events.".format(name)
