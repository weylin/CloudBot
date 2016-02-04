from cloudbot import hook
from ..plugins.destiny import chars
from pickle import dump, load

SESSIONS = {}
MEMBERS = []
SHERPAS = {'xb1': [], 'xb360': [], 'ps4': [], 'ps3': []}
CONSOLES = ['\x02\x033Xbox One\x02\x03', '\x02\x0312Playstation 4\x02\x03',
            '\x02\x033Xbox 360\x02\x03', '\x02\x0312Playstation 3\x02\x03']
SESSION_COUNT = 0


def parse_command(text, delimiter='--'):
    # Takes in a command string and returns a dictionary
    arg_dict = {}
    for arg in text.split(delimiter):
        if arg != '':
            split_arg = arg.strip().split(' ')
            arg_dict[split_arg[0]] = ' '.join(split_arg[1:])
    return arg_dict


def session_info(session):
    # Return formatted information about a session
    if '1' in session['console']:
        console = '\x02\x033Xbox One\x02\x03'
    elif '4' in session['console']:
        console = '\x02\x0312Playstation 4\x02\x03'
    elif '360' in session['console']:
        console = '\x02\x033Xbox 360\x02\x03'
    else:
        console = '\x02\x0312Playstation 3\x02\x03'

    if (len(session['members']) == int(session['limit'])):
        member_count = '\x02\x034Full\x02\x03'
    else:
        member_count = '{}/{}'.format(len(session['members']), int(session['limit']))

    return ('Id: {}, Owner: {}, Title: {}, Time: {}, Date: {},'
            ' Console: {}, Members: {}, Limit: {}'.format(
                session['id'], session['owner'], session['title'],
                session['time'], session['date'],
                console, ', '.join(session['members']), member_count
            ))


@hook.on_start()
def load_data(bot):
    """Load in our pickled content"""
    global SESSIONS, MEMBERS, SHERPAS, SESSION_COUNT
    try:
        with open('destiny_lfg', 'rb') as f:
            SESSIONS = load(f)
            MEMBERS = load(f)
            SHERPAS = load(f)
            SESSION_COUNT = load(f)
    except:
        SESSIONS = {}
        MEMBERS = []
        SHERPAS = {'xb1': [], 'xb360': [], 'ps4': [], 'ps3': []}
        SESSION_COUNT = 0


@hook.command('save_lfg', autohelp=False, permissions=["op"])
def save_lfg(message):
    with open('destiny_lfg', 'wb') as f:
        dump([SESSIONS, MEMBERS, SHERPAS, SESSION_COUNT], f)
        message("Session information saved")


# @hook.periodic(11, initial_interval=11)
# def helper():
#     # This function will take care of some of the maintenance
#     # todo: remove old sessions


@hook.command('lfg')
def lfg(text, nick, bot, notice):
    # Returns open groups. Can filter by console
    for session in SESSIONS:
        if len(session['members']) < int(session['limit']):
            if text:
                if text == session['console']:
                    notice(session_info(session))
            else:
                notice(session_info(session))


@hook.command('lfm')
def lfm(text, nick, bot, notice):
    # Returns available players. Can filter by console
    for member in MEMBERS:
        notice(chars(member, nick, bot, notice))


@hook.command('sherpas')
def sherpas(text, nick, bot, notice):
    # Returns a list of channel sherpas. Can filter by console
    args = text.lower().split(' ')
    if 'add' in args:
        for console in ['xb1', 'xb360', 'ps4', 'ps3']:
            if console in args:
                SHERPAS[console].append(nick)
                notice('{} added to {} list'.format(nick, console))
    elif 'remove' in args:
        for console in ['xb1', 'xb360', 'ps4', 'ps3']:
            if console in args:
                if SHERPAS[console].get(nick, None):
                    notice('{} removed from {} list'.format(nick, console))
    else:
        for console in SHERPAS:
            if '1' in console:
                platform = '\x02\x033Xbox One\x02\x03'
            elif '4' in console:
                platform = '\x02\x0312Playstation 4\x02\x03'
            elif '360' in console:
                platform = '\x02\x033Xbox 360\x02\x03'
            else:
                platform = '\x02\x0312Playstation 3\x02\x03'
            notice('{}: {}'.format(platform, ', '.join(SHERPAS[console])))


@hook.command('newSession')
def new_session(text, nick, bot):
    # Create a new session
    session = {
        'owner': nick,
        'members': [nick],
        'title': None,
        'description': None,
        'time': None,
        'date': None,
        'console': None,
        'limit': 6,
    }
    global SESSION_COUNT
    SESSION_COUNT += 1
    args = parse_command(text)
    for arg in args:
        if arg in session:
            session[arg] = args[arg]
    session['id'] = SESSION_COUNT
    global SESSIONS
    SESSIONS[str(SESSION_COUNT)] = session
    return 'Created session {}.'.format(SESSION_COUNT)


@hook.command('editSession')
def edit_session(text, nick, bot, notice):
    # Edit an existing session
    args = parse_command(text)
    if 'id' not in args:
        notice('You must specify the session id with --id')
        return
    session = SESSIONS.get(args['id'], None)
    if not session:
        notice('Could not find session with id of {}'.format(args['id']))
        return
    if nick != session['owner']:
        notice('You are not the session owner.')
        return
    for arg in args:
        if arg in session:
            session[arg] = args[arg]
    global SESSIONS
    SESSIONS[session['id']] = session
    notice('Updated the session.')


@hook.command('deleteSession')
def delete_session(text, nick, bot, notice):
    # Delete an existing session
    session = SESSIONS.get(text, None)
    if not session:
        notice('Could not find session with id of {}'.format(text))
        return
    if nick != session['owner']:
        notice('You are not the session owner.')
        return
    global SESSIONS
    del SESSIONS[session['id']]
    notice('Deleted session {}'.format(text))


@hook.command('sessions')
def list_sessions(text, nick, bot, notice):
    # List all upcoming sessions
    if text:
        session = SESSIONS.get(text, None)
        if not session:
            notice('Could not find session with id of {}'.format(text))
            return
        else:
            notice(session_info(session))
    else:
        for session in SESSIONS:
            notice(session_info(SESSIONS[session]))


@hook.command('joinSession')
def join_session(text, nick, bot, notice):
    # Add a user to the session
    session = SESSIONS.get(text, None)
    if not session:
        notice('Could not find session with id of {}'.format(text))
    elif nick in session['members']:
        notice('You can\'t join a session twice!')
    elif len(session['members']) < int(session['limit']):
        session['members'].append(nick)
        notice('Successfully joined session {}.'.format(text))


@hook.command('leaveSession')
def leave_session(text, nick, bot, notice):
    # Remove the user from the session
    session = SESSIONS.get(text, None)
    if not session:
        notice('Could not find session with id of {}'.format(text))
        return
    if nick in session['members']:
        del session['members']['nick']
        notice('You have been removed from session {}'.format(text))


@hook.command('listme')
def listme(nick, bot, notice):
    # Add a member to the list of those available
    if nick in MEMBERS:
        notice('You are already listed.')
    else:
        global MEMBERS
        MEMBERS.append(nick)
        notice('You have been listed.')


@hook.command('unlistme')
def unlistme(text, nick, bot, notice):
    # Remove a member from the list of those available
    if nick in MEMBERS:
        del MEMBERS[nick]
        notice('You have been removed from the list.')
    else:
        notice('You are not currently listed.')


@hook.command('pingSession')
def ping_session(text, bot, notice):
    # Pings everyone in a session
    session = SESSIONS.get(text, None)
    if not session:
        notice('Could not find session with id of {}'.format(text))
        return
    return 'ping {}'.format(', '.join(session['members']))
