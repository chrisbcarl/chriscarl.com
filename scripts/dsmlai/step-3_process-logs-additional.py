import os
import sys
import time
import json
import importlib

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

if SCRIPT_DIRPATH not in sys.path:
    sys.path.append(SCRIPT_DIRPATH)
import constants

importlib.reload(constants)

CSV_NGINX = os.path.join(DSMLAI_CSVS_DIRPATH, 'nginx.csv')
nginx_df = pd.read_csv(CSV_NGINX)
nginx_df['time_local'] = pd.to_datetime(nginx_df['time_local'])
ips = nginx_df['remote_addr'].unique().tolist()

ip_vcs = nginx_df['remote_addr'].value_counts().sort_values(ascending=False)
ip_vcs_df = pd.DataFrame({'ip': ip_vcs.index, 'count': ip_vcs.values})
JSON_IPS = os.path.join(DSMLAI_CSVS_DIRPATH, 'ips.json')
with open(JSON_IPS, 'w', encoding='utf-8') as w:
    json.dump([dict(row) for _, row in ip_vcs_df.iterrows()], w, indent=2)

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

ips.remove('127.0.0.1')  # we re-add it later
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

# the usual demo.ip-api isnt helpful, this is "more" helpful
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

importlib.reload(constants)
agent_rows = []
for user_agent in nginx_df['http_user_agent'].unique():
    row = constants.parse_user_agent(user_agent)
    agent_rows.append(row)

print(list(sorted([str(ele) for ele in constants.USER_AGENTS])))

agent_df = pd.DataFrame(agent_rows)
# cols = agent_df.columns.tolist()
# agent_df[cols[1:]] = agent_df[cols[1:]].fillna([None])
# agent_df = agent_df.drop(['A', 'Brand'], axis=1)  # Not(A:Brand/24, happens when chromium is unbraneded https://github.com/WICG/ua-client-hints/issues/137

CSV_AGENTS = os.path.join(DSMLAI_CSVS_DIRPATH, 'agents.csv')
agent_df.to_csv(CSV_AGENTS, index=False)

JSON_AGENTS = os.path.join(DSMLAI_CSVS_DIRPATH, 'agents.json')
with open(JSON_AGENTS, 'w', encoding='utf-8') as w:
    json.dump(constants.USER_AGENTS, w, indent=4)
