import os
import re
import time
import json

import requests
import pandas as pd

try:
    SCRIPT_DIRPATH = os.path.dirname(__file__)
except Exception:
    SCRIPT_DIRPATH = 'scripts/dsmlai'
REPO_DIRPATH = os.path.abspath(os.path.join(SCRIPT_DIRPATH, '../../'))
IGNOREME_DIRPATH = os.path.join(REPO_DIRPATH, 'ignoreme')
DSMLAI_DIRPATH = os.path.join(IGNOREME_DIRPATH, 'dsmlai')
DSMLAI_LOGS_DIRPATH = os.path.join(DSMLAI_DIRPATH, 'logs')
DSMLAI_CSVS_DIRPATH = os.path.join(DSMLAI_DIRPATH, 'csvs')
if not os.path.isdir(DSMLAI_LOGS_DIRPATH):
    os.makedirs(DSMLAI_LOGS_DIRPATH)
if not os.path.isdir(DSMLAI_CSVS_DIRPATH):
    os.makedirs(DSMLAI_CSVS_DIRPATH)

############ USE THE BASIC DATA TO DERIVE LOCATION, AGENT, ETC AND JOIN THEM

CSV_ACCESS1 = os.path.join(DSMLAI_CSVS_DIRPATH, 'access1.csv')
nginx_df = pd.read_csv(CSV_ACCESS1)
nginx_df['time_local'] = pd.to_datetime(nginx_df['time_local'])
ips = nginx_df['remote_addr'].unique().tolist()

############ QUERY IP LOCATION DATA

IP_API_HEADERS = {
    'accept': '*/*',
    'accept-encoding': 'gzip, deflate, br, zstd',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'connection': 'keep-alive',
    'host': 'demo.ip-api.com',
    'origin': 'https://ip-api.com',
    'pragma': 'no-cache',
    'referer': 'https://ip-api.com/',
    'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Microsoft Edge";v="134"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
}

session = requests.Session()
ip_dicts = []
iterations = list(range(len(ips) // 100 + 1))
count = len(iterations)
while iterations:
    i = iterations.pop(0)
    subips = ips[i * 100:(i + 1) * 100]
    print(i + 1, '/', count)
    # uri = f'https://demo.ip-api.com/json/{ip}?fields=66842623&lang=en'  # get
    uri = 'http://ip-api.com/batch'  # https://ip-api.com/docs/api:batch
    with session.post(uri, headers=IP_API_HEADERS, json=subips) as resp:
        if resp.status_code != 200:
            # 429 too many requests will happen...
            print('bad status code:', resp.status_code, 'reason:', resp.reason, 'sleeping 30')
            time.sleep(30)
            iterations.insert(0, i)
            continue
        body = resp.json()
        ip_dicts.extend(body)
    time.sleep(3)

localhost = {
    'status': 'success',
    'country': 'localhost',
    'countryCode': 'LH',
    'region': 'LH',
    'regionName': 'localhost',
    'city': 'localhost',
    'zip': '0',
    'lat': 0,
    'lon': 0,
    'timezone': 'America/Los_Angeles',
    'isp': 'localhost',
    'org': 'localhost',
    'as': 'localhost',
    'query': '127.0.0.1'
}
ip_dicts.append(localhost)  # for fun
ip_api_df = pd.DataFrame(ip_dicts)

CSV_IP_API = os.path.join(IGNOREME_DIRPATH, 'ip_api.csv')
ip_api_df.to_csv(CSV_IP_API, index=False)

############ HTTP AGENTS GET CRAWLERS

crawler_bots = nginx_df[nginx_df['http_user_agent'].str.contains('://')]['http_user_agent'].unique()
cleaned_crawler_bots = []
for crawler_bot in crawler_bots:
    tokens = crawler_bot.split('http')
    tokens = tokens[1].split(')')
    cleaned_crawler_bots.append('http' + tokens[0])
CRAWLERS_TXT = os.path.join(DSMLAI_DIRPATH, 'crawlers.txt')
with open(CRAWLERS_TXT, 'w', encoding='utf-8') as w:
    w.write('\n'.join(sorted(set(cleaned_crawler_bots))))

############ HTTP AGENTS

user_agents = {}
rows = []
known_worthless = [
    'https',
    'compatible',
    'Mini',  # opera mini
    'Mobi',  # opera mobi
    'Version',  # Version/4.0
    'Hello',  # hello world stuff
    'Hello,',  # hello world stuff
]
questionable = ['Edition', 'Mobi']
for user_agent in nginx_df['http_user_agent'].unique():
    original_user_agent = user_agent
    first = user_agent.split(' ')[0]
    lst = [first.split('/')[0]]
    user_agent = user_agent.replace(first, '')
    user_agent = re.sub(r'g\(\d+\)', '', user_agent)  # moto g(7)
    if 'Not(A:Brand' in user_agent:
        lst.append('Not(A:Brand')
        user_agent = user_agent.replace('Not(A:Brand', '')
    # companies = re.findall(r'([\w-]+),', user_agent)
    # if 'Expanse' in companies:
    #     companies = ['Expanse']
    parenthesis = re.findall(r'\(([\w-]+)', user_agent)
    clients = re.findall(r' ([A-za-z\d-]+)\/v?[\d\/\.]+', user_agent)
    lst += parenthesis + clients
    for ele in known_worthless:
        if ele in lst:
            lst.remove(ele)
    if lst == ['-']:  # no agent provided:
        lst = [None]
    row = dict(http_user_agent=original_user_agent, agents=lst)
    if any(ele in lst for ele in questionable):
        print('!!!!!!!', user_agent, lst)
    # row.update({k: True for k in lst})
    for k in lst:
        if k not in user_agents:
            user_agents[k] = 0
        user_agents[k] += 1
    rows.append(row)

agent_df = pd.DataFrame(rows)
cols = agent_df.columns.tolist()
agent_df[cols[1:]] = agent_df[cols[1:]].fillna(False)
# agent_df = agent_df.drop(['A', 'Brand'], axis=1)  # Not(A:Brand/24, happens when chromium is unbraneded https://github.com/WICG/ua-client-hints/issues/137

CSV_AGENTS = os.path.join(DSMLAI_CSVS_DIRPATH, 'agents.csv')
agent_df.to_csv(CSV_AGENTS, index=False)

JSON_AGENTS = os.path.join(DSMLAI_CSVS_DIRPATH, 'agents.json')
with open(JSON_AGENTS, 'w', encoding='utf-8') as w:
    json.dump(user_agents, w, indent=4)
