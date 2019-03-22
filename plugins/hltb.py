import requests
from bs4 import BeautifulSoup
from cloudbot import hook

@hook.command("hltb")
def hltb(text):
    url = "https://howlongtobeat.com/search_results.php?page=1"
    payload = {'queryString': text,
               't': 'games',
               'sorthead': 'popular',
               'sortd': 'Normal Order',
               'length_type': 'main',
               'detail': '0'}
    headers = {'Content-type': 'application/x-www-form-urlencoded',
               'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36',
               'Origin': 'https://howlongtobeat.com',
               'Referer': 'https://howlongtobeat.com/'}

    session = requests.Session()
    session.post(url, headers=headers, data=payload)
    r = session.post(url, headers=headers, data=payload)

    if len(r.content) < 250:
        return "No results."

    bs = BeautifulSoup(r.content, 'lxml')

    first = bs.findAll("div", {"class": "search_list_details"})[0]    
    output = ["\x02{}\x02 -".format(first.a.text)]
    rest = first.findAll('div')
    
    entries = {2: '\x02{}\x02:', 3: '{}', 6: '\x02{}:\x02', 7: '{}'}
    for i in range(len(rest)):
        if i in entries:
            output.append(entries[i].format(rest[i].text))

    return ' '.join(output)
