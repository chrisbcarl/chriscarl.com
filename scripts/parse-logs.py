import os
import re
import datetime
import gzip
import shutil
import multiprocessing

import numpy as np

try:
    SCRIPT_DIRPATH = os.path.dirname(__file__)
except Exception:
    SCRIPT_DIRPATH = 'scripts/parse-logs'
REPO_DIRPATH = os.path.abspath(os.path.join(SCRIPT_DIRPATH, '../../'))
VAR_LOG_DIRPATH = os.path.abspath(os.path.join(REPO_DIRPATH, 'ignoreme/159.54.179.175/var/log'))
IGNOREME_DIRPATH = os.path.join(REPO_DIRPATH, 'ignoreme')

RS = 0
WORKERS = multiprocessing.cpu_count() // 4 * 3

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
NGINX_ACCESS_CSV = os.path.join(IGNOREME_DIRPATH, 'nginx.csv')
IP_API_CSV = os.path.join(IGNOREME_DIRPATH, 'ip_api.csv')
LOC_NGINX_CSV = os.path.join(IGNOREME_DIRPATH, 'loc_nginx.csv')

############ PARSE ACCESS LOGS

access_logs = []
auth_logs = []
for d, _, fs in os.walk(VAR_LOG_DIRPATH):
    for f in fs:
        ext = os.path.splitext(f)[1]
        filepath = os.path.join(d, f)
        if ext.lower() == '.gz':
            txtpath = os.path.join(d, f)[:-3]
            print(filepath, txtpath)
            with gzip.open(filepath, 'rb') as f_in, open(txtpath, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
            if 'access.log' in txtpath:
                access_logs.append(txtpath)
        elif 'auth.log' in filepath:
            auth_logs.append(filepath)

# $remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"'
LOG_FORMAT = (
    r'^'
    r'(?P<remote_addr>\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}) - '
    r'(?P<remote_user>[-]) '
    r'\[(?P<time_local>\d{2}\/[A-Z][a-z]{2}\/\d{4}\:\d{2}\:\d{2}\:\d{2} \+\d{4})\] '
    r'"(?P<request>.*)" '
    r'(?P<status>\d+) '
    r'(?P<body_bytes_sent>\d+) '
    r'"(?P<http_referer>.*)" '
    r'"(?P<http_user_agent>.*)"'
    r'$'
)
LOG_FORMAT_REGEX = re.compile(LOG_FORMAT, flags=re.IGNORECASE)
import pandas as pd

rows = []
for f, filepath in enumerate(access_logs):
    with open(filepath, encoding='utf-8') as r:
        lines = r.read().splitlines()
    for l, line in enumerate(lines):
        mo = LOG_FORMAT_REGEX.match(line)
        if not mo:
            print(f'"{filepath}", line {l}: {line}')
            raise RuntimeError()
        rows.append(mo.groupdict())

############ POST PROCESS ACCESS LOGS

nginx_df = pd.DataFrame(rows)
nginx_df['time_local'] = nginx_df['time_local'].apply(lambda x: datetime.datetime.strptime(x, '%d/%b/%Y:%H:%M:%S %z'))
nginx_df[['verb', 'path']] = nginx_df['request'].str.split(' ', n=1, expand=True)
nginx_df[['route', 'protocol']] = nginx_df['path'].str.rsplit(' ', n=1, expand=True)
nginx_df['route_depth'] = nginx_df['route'].str.split('/').apply(lambda x: len(x) if isinstance(x, list) else -1)
nginx_df['route_length'] = nginx_df['route'].str.len()
nginx_df['route_asbytes'] = nginx_df['route'].apply(lambda x: 0 if not x else len(re.findall(r'[\x00-\x7F]', x)))
known_routes = set(
    [
        '/', '/assets/fontawesome/file-pdf-solid.svg', '/assets/fontawesome/linkedin-in-brands-solid.svg', '/assets/fontawesome/github-brands-solid.svg',
        '/assets/fontawesome/youtube-brands-solid.svg', '/assets/paths.js', '/favicon.ico', '/files/favicon.ico'
    ]
)
nginx_df['route_exists'] = nginx_df['route'].apply(lambda x: x in known_routes)
nginx_df['verb_length'] = nginx_df['verb'].str.len()
nginx_df['verb_asbytes'] = nginx_df['verb'].apply(lambda x: 0 if not x else len(re.findall(r'[\x00-\x7F]', x)))
nginx_df['crawler'] = nginx_df['http_user_agent'].str.contains('://')
nginx_df = nginx_df.drop(['request', 'path'], axis=1)  # might miss some stuff, we'll see
nginx_df.to_csv(NGINX_ACCESS_CSV, index=False)
# nginx_df
# nginx_df[nginx_df['route_depth'] == -1]

crawler_bots = nginx_df[nginx_df['http_user_agent'].str.contains('://')]['http_user_agent'].unique()
cleaned_crawler_bots = []
for crawler_bot in crawler_bots:
    tokens = crawler_bot.split('http')
    tokens = tokens[1].split(')')
    cleaned_crawler_bots.append('http' + tokens[0])

ips = nginx_df['remote_addr'].unique().tolist()

############ QUERY IP LOCATION DATA

# location aquired by: http://ip-api.com/batch POST ["8.8.8.8", "8.8.8.8"]
import time
import requests

session = requests.Session()
ip_dicts = []
iterations = len(ips) // 100 + 1
for i in range(iterations):
    subips = ips[i * 100:(i + 1) * 100]
    print(i + 1, '/', iterations)
    # uri = f'https://demo.ip-api.com/json/{ip}?fields=66842623&lang=en'  # get
    uri = 'http://ip-api.com/batch'  # https://ip-api.com/docs/api:batch
    with session.post(uri, headers=IP_API_HEADERS, json=subips) as resp:
        if resp.status_code != 200:
            print('bad status code:', resp.status_code, 'reason:', resp.reason, 'sleeping 30')
            time.sleep(30)
            continue
        body = resp.json()
        ip_dicts.extend(body)
    print('sleeping 5')
    time.sleep(5)

ip_api_df = pd.DataFrame(ip_dicts)
ip_api_df.to_csv(IP_API_CSV, index=False)

ip_api_df = ip_api_df.drop(['status'], axis=1)  # usually just says "success"

loc_nginx_df = nginx_df.merge(ip_api_df, how='inner', left_on=['remote_addr'], right_on=['query'])
loc_nginx_df = loc_nginx_df.drop(['query', 'message'], axis=1)
loc_nginx_df.to_csv(LOC_NGINX_CSV, index=False)

everything_df = loc_nginx_df.copy()

############ TRIM AND PREP FOR INJEST
EVERYTHING_AGENTS_CSV = os.path.join(IGNOREME_DIRPATH, 'everything+agents.csv')

everything_df['time_local'] = pd.to_datetime(everything_df['time_local'])
everything_df['time_local'] = everything_df['time_local'].astype(np.int64) // 10**9

everything_df[['route_0', 'route_1', 'route_2', 'route_3']] = everything_df['route'].str.split('/', n=3, expand=True)
everything_df = everything_df.drop(['countryCode', 'region', 'zip', 'lat', 'lon', 'timezone', 'isp', 'org', 'as'], axis=1)
everything_df = everything_df.fillna('')
categoricals = everything_df.select_dtypes(include=['object']).columns.tolist()
everything_df[categoricals] = everything_df[categoricals].astype('category')
everything_df = loc_nginx_df.copy()
everything_df.to_csv(EVERYTHING_AGENTS_CSV)

############ DEAL WITH AGENTS??? PROBABLY SKIP TBH

AGENTS_CSV = os.path.join(IGNOREME_DIRPATH, 'agents.csv')
user_agents = set()
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
for user_agent in df['http_user_agent'].unique():
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
    row = dict(user_agent=original_user_agent, agents=lst)
    if any(ele in lst for ele in questionable):
        print('!!!!!!!', user_agent, lst)
    # row.update({k: True for k in lst})
    user_agents.update(lst)
    rows.append(row)

agent_df = pd.DataFrame(rows)
cols = agent_df.columns.tolist()
agent_df[cols[1:]] = agent_df[cols[1:]].fillna(False)
# agent_df = agent_df.drop(['A', 'Brand'], axis=1)  # Not(A:Brand/24, happens when chromium is unbraneded https://github.com/WICG/ua-client-hints/issues/137
agent_df.to_csv(AGENTS_CSV, index=False)

# user_agents_ive_encountered = ['-', '8LEGS', 'Agency', 'AhrefsBot', 'Android', 'AppleWebKit', 'Applebot', 'BLEXBot', 'CCleaner', 'COMODO', 'CensysInspect', 'CheckMarkNetwork', 'Chrome', 'Chromium', 'CriOS', 'Custom-AsyncHttpClient', 'Edg', 'EdgiOS', 'Edition', 'Expanse,', 'Firefox', 'GSA', 'Gecko', 'Go-http-client', 'Googlebot', 'HTTP', 'HeadlessChrome', 'Hello', 'Hello,', 'IEMobile', 'InternetMeasurement', 'J2ME', 'KHTML', 'Linux', 'LoiLoNote', 'MJ12bot', 'MMWEBSDK', 'Macintosh', 'Minimo', 'Mobi', 'Mobile', 'ModatScanner', 'Mozilla', 'Mozlila', 'Not(A:Brand', 'OPR', 'OmniWeb', 'Opera', 'Presto', 'Puffin', 'Red', 'Safari', 'SamsungBrowser', 'Sectigo', 'SeznamBot', 'Silk', 'SiteLockSpider', 'Trident', 'Twitterbot', 'U3', 'UCBrowser', 'Ubuntu', 'Version', 'Vivaldi', 'Wget', 'WinNT', 'Windows', 'WindowsPowerShell', 'X11', 'XWEB', 'YaBrowser', 'YandexBot', 'Yowser', 'Zeno', 'bingbot', 'curl', 'fasthttp', 'fluid', 'iPhone', 'iTunes', 'konqueror', 'l9explore', 'l9scan', 'l9tcpid', 'masscan', 'python-httpx', 'python-requests', 'warc', 'zgrab']
print(len(user_agents), sorted(user_agents))
agent_dummies = pd.get_dummies(pd.DataFrame(agent_df['agents'].values.tolist()), prefix_sep='_', prefix='agent', drop_first=True)
agent_dummies

everything_df = everything_df.merge(agent_df, how='inner', left_on=['http_user_agent'], right_on=['user_agent'])
everything_df = everything_df.drop(['http_user_agent', 'user_agent'], axis=1)

agent_dummies_everything_df = pd.get_dummies(pd.DataFrame(everything_df['agents'].values.tolist()), prefix_sep='_', prefix='agent', drop_first=True)
columns = everything_df.columns.tolist()
columns.remove('agents')
other_columns_everything_df = pd.get_dummies(everything_df[columns], drop_first=True)

EVERYTHING_DUMMIES_CSV = os.path.join(IGNOREME_DIRPATH, 'everything+agents_dummies.csv')
everything_dummies = other_columns_everything_df.merge(agent_dummies_everything_df, how='inner', left_index=True, right_index=True)
everything_dummies.to_csv(EVERYTHING_DUMMIES_CSV, index=False)

############ DONT DEAL WITH AGENTS!!!!
