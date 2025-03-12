import os
import json

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

############ MERGING

CSV_NGINX = os.path.join(DSMLAI_CSVS_DIRPATH, 'nginx.csv')
nginx_df = pd.read_csv(CSV_NGINX)
nginx_df['time_local'] = pd.to_datetime(nginx_df['time_local'])  # unnecessary, but good practice
# nginx_df = nginx_df.drop(['remote_user', 'request', 'path'], axis=1)

CSV_IP_API = os.path.join(IGNOREME_DIRPATH, 'ip_api.csv')
ip_api_df = pd.read_csv(CSV_IP_API)
# ip_api_df = ip_api_df.drop(['status'], axis=1)  # usually just says "success", not sure where "message" came from
# ip_api_df = ip_api_df.drop(['countryCode', 'region', 'zip', 'lat', 'lon', 'timezone', 'isp', 'org', 'as'], axis=1)

CSV_AGENTS = os.path.join(DSMLAI_CSVS_DIRPATH, 'agents.csv')
agents_df = pd.read_csv(CSV_AGENTS)
agents_df['agents'] = agents_df['agents'].apply(lambda lst: eval(lst))
agents_df['agents_count'] = agents_df['agents'].apply(lambda lst: len(lst))
JSON_AGENTS = os.path.join(DSMLAI_CSVS_DIRPATH, 'agents.json')
with open(JSON_AGENTS, 'r', encoding='utf-8') as r:
    agent_frequency = json.load(r)

merged_df = pd.merge(nginx_df, agents_df, how='inner', on='http_user_agent')
# merged_df = merged_df.drop(['http_user_agent'], axis=1)
CSV_MERGED = os.path.join(DSMLAI_CSVS_DIRPATH, 'merged.csv')
merged_df.to_csv(CSV_MERGED, index=False)

merged_df = merged_df.merge(ip_api_df, how='inner', left_on=['remote_addr'], right_on=['query'])
# merged_df['agents'] = merged_df['agents'].apply(lambda lst: '_'.join(sorted([str(ele) for ele in lst], key=lambda x: agent_frequency.get(x, -1))))
merged_df['agents_count'] = merged_df['agents'].apply(lambda lst: len(lst))
# merged_df = merged_df.drop(['query', 'agents'], axis=1)
CSV_MERGED = os.path.join(DSMLAI_CSVS_DIRPATH, 'merged1.csv')
merged_df.to_csv(CSV_MERGED, index=False)
