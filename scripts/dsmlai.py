'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2025-03-08

Description:
    given this copius amount of shit data people are just giving me for free, why not make lemonade out of it?

Updates:
    2025-03-08 - chrisbcarl - poc model created, works, yipee
'''
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
KNOWN_VERBS = set(['GET'])
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
    # omitting '/', '/favicon.ico', '/files/favicon.ico' because everyone has those routes
    [
        # # way too common ones
        # '/',
        # '/favicon.ico',
        # '/files/favicon.ico',
        # less common
        '/assets/fontawesome/file-pdf-solid.svg',
        '/assets/fontawesome/linkedin-in-brands-solid.svg',
        '/assets/fontawesome/github-brands-solid.svg',
        '/assets/fontawesome/youtube-brands-solid.svg',
        '/assets/paths.js',
    ]
)
nginx_df['route_exists'] = nginx_df['route'].apply(lambda x: x in known_routes)
nginx_df['verb_length'] = nginx_df['verb'].str.len()
nginx_df['verb_asbytes'] = nginx_df['verb'].apply(lambda x: 0 if not x else len(re.findall(r'[\x00-\x7F]', x)))
nginx_df['verb_supported'] = nginx_df['verb'].str == 'GET'
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

############ DEAL WITH AGENTS??? PROBABLY SKIP TBH
############ TRIM AND PREP FOR INJEST
EVERYTHING_AGENTS_CSV = os.path.join(IGNOREME_DIRPATH, 'everything+agents.csv')
EVERYTHING_CSV = os.path.join(IGNOREME_DIRPATH, 'everything.csv')

everything_df = loc_nginx_df.copy()

everything_df['time_local'] = pd.to_datetime(everything_df['time_local'])
everything_df['time_local'] = everything_df['time_local'].astype(np.int64) // 10**9
# everything_df[['route_0', 'route_1', 'route_2', 'route_3']] = everything_df['route'].str.split('/', n=3, expand=True)
everything_df = everything_df.drop(['countryCode', 'region', 'zip', 'lat', 'lon', 'timezone', 'isp', 'org', 'as'], axis=1)
everything_df = everything_df.fillna('')
categoricals = everything_df.select_dtypes(include=['object']).columns.tolist()
everything_df[categoricals] = everything_df[categoricals].astype('category')
everything_df = loc_nginx_df.copy()
everything_df.to_csv(EVERYTHING_AGENTS_CSV, index=False)
everything_df.to_csv(EVERYTHING_CSV, index=False)

############ DEAL WITH AGENTS??? PROBABLY SKIP TBH

AGENTS_CSV = os.path.join(IGNOREME_DIRPATH, 'agents.csv')
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
for user_agent in everything_df['http_user_agent'].unique():
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
    for k in lst:
        if k not in user_agents:
            user_agents[k] = 0
        user_agents[k] += 1
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

user_agents_df = pd.DataFrame(zip(user_agents.keys(), user_agents.values()), columns=['name', 'value']).sort_values(by=['value'], ascending=[False]).reset_index(drop=True)

# everything_df = everything_df.merge(agent_df, how='inner', left_on=['http_user_agent'], right_on=['user_agent'])
# everything_df = everything_df.drop(['http_user_agent', 'user_agent'], axis=1)

# agent_dummies_everything_df = pd.get_dummies(pd.DataFrame(everything_df['agents'].values.tolist()), prefix_sep='_', prefix='agent', drop_first=True)
# columns = everything_df.columns.tolist()
# columns.remove('agents')
# other_columns_everything_df = pd.get_dummies(everything_df[columns], drop_first=True)

# EVERYTHING_DUMMIES_CSV = os.path.join(IGNOREME_DIRPATH, 'everything+agents_dummies.csv')
# everything_dummies = other_columns_everything_df.merge(agent_dummies_everything_df, how='inner', left_index=True, right_index=True)
# everything_dummies.to_csv(EVERYTHING_DUMMIES_CSV, index=False)

############ DONT DEAL WITH AGENTS!!!!

# this is definitely affirming the conclusion, but I want some stronger clustering, so I'll reduce the features and add some more thumb on the scale stuff, like indicators that things are bad or good or valid or invalid.

EVERYTHING_CSV = os.path.join(IGNOREME_DIRPATH, 'everything.csv')
everything_df['probably_human'] = pd.Series([False] * everything_df.shape[0])

# for every ip address, find the first time it accessed /, look ahead 3 seconds, if all routes were covered, then its legit.
for group, subdf in everything_df.groupby(['remote_addr']):
    remote_addr = group[0]
    # if remote_addr != '73.93.77.135':
    #     continue
    happened = subdf[subdf['route'] == '/']
    for idx in happened.index:
        row = subdf.loc[idx]
        start = row['time_local'].to_pydatetime()
        next_3_seconds = subdf[(start <= subdf['time_local']) & (subdf['time_local'] < start + datetime.timedelta(seconds=3))]
        if len(next_3_seconds) > 4:
            # print(set(next_3_seconds['route']), known_routes)
            if set(next_3_seconds['route']).issuperset(known_routes):
                print('human at', remote_addr)
                everything_df.loc[next_3_seconds.index, ['probably_human']] = True

everything_df[everything_df['remote_addr'] == '73.93.77.135']
everything_df.to_csv(EVERYTHING_CSV)

rows_that_are_probably_ok = everything_df[everything_df['http_referer'].str.contains('chriscarl.com')].copy().reset_index(drop=True)
PROBABLY_OK_CSV = os.path.join(IGNOREME_DIRPATH, 'probably.csv')
rows_that_are_probably_ok.to_csv(PROBABLY_OK_CSV, index=False)

rows_i_know_are_ok = everything_df[everything_df['remote_addr'] == '73.93.77.135'].copy()
OK_CSV = os.path.join(IGNOREME_DIRPATH, '73.93.77.135.csv')
rows_i_know_are_ok.to_csv(OK_CSV, index=False)

vcs = everything_df.groupby(['remote_addr'])['probably_human'].sum().sort_values(ascending=False)
vcs = vcs[vcs > 0]
HUMANS_CSV = os.path.join(IGNOREME_DIRPATH, 'humans.csv')
vcs.to_csv(HUMANS_CSV)
print('probably only', len(vcs), 'humans showed up, and account for', vcs.sum(), 'or', vcs.sum() / everything_df.shape[0] * 100, '% of the traffic')

# the only legitimate rows are the following (i think):
# they first start with http://chriscarl.com or https://chriscarl.com or http://chriscarl.com/ or https://chriscarl.com/
# within the same second or so, load /, assets/fontawesome..., assets/paths.js, favicon.ico everybody else is bullshit

# maybe better to just do the data analysis, get clusters, then go from there.

# 833,73.93.77.135,-,2025-03-06 08:20:10+00:00,200,2527,-,"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",GET,/,HTTP/1.1,2,3,1,False,United States,US,CA,California,Union City,94587,37.5958,-122.0191,America/Los_Angeles,Comcast Cable Communications,"Comcast IP Services, L.L.C.","AS7922 Comcast Cable Communications, LLC"
# 834,73.93.77.135,-,2025-03-06 08:20:10+00:00,200,1041,https://chriscarl.com/,"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",GET,/assets/fontawesome/file-pdf-solid.svg,HTTP/1.1,4,3,38,False,United States,US,CA,California,Union City,94587,37.5958,-122.0191,America/Los_Angeles,Comcast Cable Communications,"Comcast IP Services, L.L.C.","AS7922 Comcast Cable Communications, LLC"
# 835,73.93.77.135,-,2025-03-06 08:20:10+00:00,200,512,https://chriscarl.com/,"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",GET,/assets/fontawesome/linkedin-in-brands-solid.svg,HTTP/1.1,4,3,48,False,United States,US,CA,California,Union City,94587,37.5958,-122.0191,America/Los_Angeles,Comcast Cable Communications,"Comcast IP Services, L.L.C.","AS7922 Comcast Cable Communications, LLC"
# 836,73.93.77.135,-,2025-03-06 08:20:10+00:00,200,1545,https://chriscarl.com/,"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",GET,/assets/fontawesome/github-brands-solid.svg,HTTP/1.1,4,3,43,False,United States,US,CA,California,Union City,94587,37.5958,-122.0191,America/Los_Angeles,Comcast Cable Communications,"Comcast IP Services, L.L.C.","AS7922 Comcast Cable Communications, LLC"
# 837,73.93.77.135,-,2025-03-06 08:20:10+00:00,200,587,https://chriscarl.com/,"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",GET,/assets/fontawesome/youtube-brands-solid.svg,HTTP/1.1,4,3,44,False,United States,US,CA,California,Union City,94587,37.5958,-122.0191,America/Los_Angeles,Comcast Cable Communications,"Comcast IP Services, L.L.C.","AS7922 Comcast Cable Communications, LLC"
# 838,73.93.77.135,-,2025-03-06 08:20:10+00:00,200,5735878,https://chriscarl.com/,"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",GET,/assets/paths.js,HTTP/1.1,3,3,16,False,United States,US,CA,California,Union City,94587,37.5958,-122.0191,America/Los_Angeles,Comcast Cable Communications,"Comcast IP Services, L.L.C.","AS7922 Comcast Cable Communications, LLC"
# 839,73.93.77.135,-,2025-03-06 08:20:10+00:00,404,196,https://chriscarl.com/,"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",GET,/favicon.ico,HTTP/1.1,2,3,12,False,United States,US,CA,California,Union City,94587,37.5958,-122.0191,America/Los_Angeles,Comcast Cable Communications,"Comcast IP Services, L.L.C.","AS7922 Comcast Cable Communications, LLC"


############ TRIM AND PREP FOR INJEST - NO AGENTS
def top_agents(long_agent):
    for agent in user_agents_df['name'][:15]:
        if agent in long_agent:
            return agent
    return '???'


EVERYTHING_BETTER_CSV = os.path.join(IGNOREME_DIRPATH, 'everything-no-agents.csv')
everything_better_df = everything_df.copy()
everything_better_df['time_local'] = pd.to_datetime(everything_better_df['time_local'])
everything_better_df['user_agent'] = everything_better_df['http_user_agent'].apply(top_agents)
everything_better_df['time_local'] = everything_better_df['time_local'].astype(np.int64) // 10**9
everything_better_df['verb'] = everything_better_df['verb'].apply(lambda x: x if x in KNOWN_VERBS else '???')
everything_better_df['route'] = everything_better_df['route'].apply(lambda x: x if x in known_routes else '???')
# everything_better_df[['route_0', 'route_1', 'route_2', 'route_3']] = everything_better_df['route'].str.split('/', n=3, expand=True)
everything_better_df = everything_better_df.drop(['remote_user', 'http_user_agent', 'countryCode', 'region', 'city', 'zip', 'lat', 'lon', 'timezone', 'isp', 'org', 'as'], axis=1)
everything_better_df = everything_better_df.fillna('')
categoricals = everything_better_df.select_dtypes(include=['object']).columns.tolist()
everything_better_df[categoricals] = everything_better_df[categoricals].astype('category')
everything_better_df.to_csv(EVERYTHING_BETTER_CSV, index=False)
everything_better_df

everything_better_df_onehot = pd.get_dummies(everything_better_df, drop_first=True)

from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
scaled_data = pd.DataFrame(scaler.fit_transform(everything_better_df_onehot))

############ K-MEANS CLUSTER BY VISUAL PERPLEXITY, TAKES A LONG TIME, FEEL FREE TO SKIP

import multiprocessing
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE

WORKERS = multiprocessing.cpu_count() // 4 * 3

tsne_reduced_data = TSNE(n_components=2, n_jobs=WORKERS, random_state=RS).fit_transform(scaled_data)
tsne_2d_data = pd.DataFrame(tsne_reduced_data, columns=(['reduced feature 1', 'reduced feature 2']))

# roughly without perplexity, where are the clusters?
sns.scatterplot(data=tsne_2d_data, x='reduced feature 1', y='reduced feature 2')
NAIVE_TSNE_PNG = os.path.join(IGNOREME_DIRPATH, 'k-means-cluster-naive.png')
plt.tightlayout()
plt.savefig(NAIVE_TSNE_PNG)
plt.show()

# with perplexity, where are the clusters?
perplexities = [5, 10, 20, 40, 50, 75, 100, 150]
plt.figure(figsize=(20, 15))
for i, perplexity in enumerate(perplexities):
    tsne = TSNE(n_components=2, perplexity=perplexity, n_jobs=WORKERS, random_state=RS)
    X_red = tsne.fit_transform(scaled_data)
    red_data_df = pd.DataFrame(data=X_red, columns=['reduced feature 1', 'reduced feature 2'])  # creating a new dataframe with reduced dimensions
    plt.subplot(2, 4, i + 1)
    plt.title(f'perplexity={perplexity}')
    sns.scatterplot(data=red_data_df, x='reduced feature 1', y='reduced feature 2')
    plt.tight_layout(pad=2)

PERPLEX_TSNE_PNG = os.path.join(IGNOREME_DIRPATH, 'k-means-cluster-perplex.png')
plt.savefig(PERPLEX_TSNE_PNG)
plt.show()

############ K-MEANS BY SILHOUETTE

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

scores = []
for i in range(2, 11):
    model = KMeans(n_clusters=i, random_state=RS).fit(scaled_data)
    score = silhouette_score(scaled_data, model.labels_)
    scores.append(score)

plt.plot(range(2, 11), scores, marker='o')
plt.title('silhouette')
plt.xlabel('k clusters')
plt.ylabel('score')
plt.xticks(range(2, 11))
plt.grid(True)
ELBOW_PNG = os.path.join(IGNOREME_DIRPATH, 'k-means-cluster-elbow.png')
plt.savefig(ELBOW_PNG)
plt.show()

# looks like 5 clusters
cluster_5 = KMeans(n_clusters=5, random_state=RS).fit(scaled_data)
EVERYTHING_CLUSTER_CSV = os.path.join(IGNOREME_DIRPATH, 'everything+cluster.csv')
everything_cluster_df = everything_better_df.copy()
columns = everything_cluster_df.columns.tolist()
everything_cluster_df['cluster'] = cluster_5.labels_
everything_cluster_df.to_csv(EVERYTHING_CLUSTER_CSV, index=False)

############ DECISION TREE, THE KMEANS REALLY ISNT WORKING FOR ME

from sklearn import metrics
from sklearn.model_selection import train_test_split
from imblearn.under_sampling import RandomUnderSampler
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import RandomizedSearchCV

X = everything_better_df_onehot.drop(['probably_human'], axis=1)
y = everything_better_df_onehot['probably_human']
X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.4, random_state=RS, stratify=y)
X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=RS, stratify=y_temp)

Ys = {'all': y, 'train': y_train, 'val': y_val, 'test': y_test}
Xs = {'all': X, 'train': X_train, 'val': X_val, 'test': X_test}

X_train_under, y_train_under = RandomUnderSampler(random_state=RS, sampling_strategy=0.6).fit_resample(X_train, y_train)

search_parameters = {
    "n_estimators": [150, 200, 250],
    "min_samples_leaf": np.arange(5, 10),
    "max_features": np.arange(0.2, 0.7, 0.1),
    "max_samples": np.arange(0.3, 0.7, 0.1),
    "class_weight": ['balanced', 'balanced_subsample'],
    "max_depth": np.arange(2, 8),
    "min_impurity_decrease": [0.001, 0.002, 0.003]
}
rfc = RandomForestClassifier(random_state=RS)
recall = metrics.make_scorer(metrics.recall_score)

search_norm = RandomizedSearchCV(rfc, search_parameters, n_iter=150, scoring=recall, cv=5, n_jobs=WORKERS).fit(X_train, y_train)  # , verbose=2
best_params_norm = search_norm.best_params_
best_score_norm = search_norm.best_score_
print('best_score_norm', best_score_norm, 'best_params_norm', best_params_norm)

search_under = RandomizedSearchCV(rfc, search_parameters, n_iter=150, scoring=recall, cv=5, n_jobs=WORKERS).fit(X_train_under, y_train_under)  # , verbose=2
best_params_under = search_under.best_params_
best_score_under = search_under.best_score_
print('best_score_under', best_score_under, 'best_params_under', best_params_under)

rfc_norm = RandomForestClassifier(**best_params_norm).fit(X_train, y_train)
rfc_norm_score = metrics.recall_score(y_test, rfc_norm.predict(X_test))

rfc_under = RandomForestClassifier(**best_params_under).fit(X_train_under, y_train_under)
rfc_under_score = metrics.recall_score(y_test, rfc_under.predict(X_test))
print('rfc_norm_score', rfc_norm_score, 'rfc_under_score', rfc_under_score)


def plot_important_features(model, greater_than=0.001):
    importances = model.feature_importances_
    indices = np.argsort(importances)
    feature_names = list(X.columns)

    importance_df = pd.DataFrame(zip(feature_names, importances), columns=['name', 'importance'], index=indices)
    importance_df = importance_df[importance_df['importance'] > greater_than].reset_index(drop=True)

    plt.figure(figsize=(12, 12))
    plt.title(f'{model.__class__.__name__} Feature Importances > {greater_than * 100:0.2f}%')
    plt.barh(importance_df.index, importance_df['importance'], color='violet', align='center')
    plt.yticks(importance_df.index, importance_df['name'])
    plt.xlabel('Relative Importance')
    plt.show()


plot_important_features(rfc_under)
