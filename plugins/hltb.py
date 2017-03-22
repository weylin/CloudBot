import re

import requests

from cloudbot import hook
from cloudbot.util import web
from bs4 import BeautifulSoup

@hook.command("hltb")

def hltb(text):
    game = text
    url = "http://howlongtobeat.com/search_main.php?page=1"
    payload = {"queryString": game,
               "t": "games",
               "sorthead": "popular",
               "sortd": "Normal Order",
               "length_type": "main",
               "detail": "0"}
    test = {'Content-type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.97 Safari/537.36',
            'origin': 'https://howlongtobeat.com',
            'referer': 'https://howlongtobeat.com'}

    session = requests.Session()
    session.post(url, headers=test, data=payload)
    r = session.post(url, headers=test, data=payload)

    if len(r.content) < 250:
        return bot.say("No results.")

    bs = BeautifulSoup(r.content)

    first = bs.findAll("div", {"class": "search_list_details"})[0]
    name = first.a.text

    try:
        mainStory = first.findAll('div')[2].text + ': '
    except Exception:
        mainStory = ''

    try:
        time = first.findAll('div')[3].text
    except Exception:
        time = ''

    try:
        mainExtra = '- ' + first.findAll('div')[5].text + ': '
    except Exception:
        mainExtra = ''

    try:
        time2 = first.findAll('div')[6].text
    except Exception:
        time2 = ''

    try:
        completionist = '- ' + first.findAll('div')[8].text + ': '
    except Exception:
        completionist = ''

    try:
        time3 = first.findAll('div')[9].text
    except Exception:
        time3 = ''

    return('\x02{}\x02 - \x02{}\x02 {} \x02{}\x02 {} \x02{}\x02 {}'.format(name, mainStory, time, mainExtra, time2, completionist, time3))
