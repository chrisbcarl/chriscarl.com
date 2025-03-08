import os
import re
import datetime
import gzip
import shutil
try:
    SCRIPT_DIRPATH = os.path.dirname(__file__)
except Exception:
    SCRIPT_DIRPATH = 'scripts/parse-logs'
REPO_DIRPATH = os.path.abspath(os.path.join(SCRIPT_DIRPATH, '../../'))
VAR_LOG_DIRPATH = os.path.abspath(os.path.join(REPO_DIRPATH, 'ignoreme/159.54.179.175/var/log'))
IGNOREME_DIRPATH = os.path.join(REPO_DIRPATH, 'ignoreme')

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

nginx_df = pd.DataFrame(rows)
nginx_df['time_local'] = nginx_df['time_local'].apply(lambda x: datetime.datetime.strptime(x, '%d/%b/%Y:%H:%M:%S %z'))
nginx_df.to_csv(NGINX_ACCESS_CSV, index=False)

nginx_df[['verb', 'path']] = nginx_df['request'].str.split(' ', n=1, expand=True)
nginx_df[['route', 'protocol']] = nginx_df['path'].str.rsplit(' ', n=1, expand=True)
nginx_df['route_depth'] = nginx_df['route'].str.split('/').apply(lambda x: len(x) if isinstance(x, list) else -1)
nginx_df['crawler'] = nginx_df['http_user_agent'].str.contains('://')
nginx_df = nginx_df.drop(['request', 'path'], axis=1)  # might miss some stuff, we'll see
nginx_df
nginx_df[nginx_df['route_depth'] == -1]

crawler_bots = nginx_df[nginx_df['http_user_agent'].str.contains('://')]['http_user_agent'].unique()
cleaned_crawler_bots = []
for crawler_bot in crawler_bots:
    tokens = crawler_bot.split('http')
    tokens = tokens[1].split(')')
    cleaned_crawler_bots.append('http' + tokens[0])

ips = nginx_df['remote_addr'].unique().tolist()

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
loc_nginx_df.to_csv(LOC_NGINX_CSV)

df = pd.DataFrame([{'str': f'{i}-{i * 2}'} for i in range(9)])
# n is "number of splits", axis=0 REALLY doesnt work in this case at all, and collapses all 2 new columns down
# https://stackoverflow.com/a/39358924
df[['a', 'b']] = df['str'].str.split('-', n=1, expand=True).astype(int).apply(lambda series: series.apply(lambda x: x**3 if x % 2 == 1 else x**2), axis=1)
