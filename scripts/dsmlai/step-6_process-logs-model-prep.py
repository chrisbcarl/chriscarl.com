import os
import sys
import importlib

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

############ LOAD AND CORRECTLY TYPE ALL DATA

CSV_MERGED = os.path.join(DSMLAI_CSVS_DIRPATH, 'merged3.csv')
merged_df = pd.read_csv(CSV_MERGED)
merged_df['time_local'] = pd.to_datetime(merged_df['time_local'])
# merged_df['agents'] = merged_df['agents'].apply(lambda lst: eval(lst))

############ DROP / REANAME ALL UNINTERESTING DATA

merged_df = merged_df.drop(
    ['remote_addr', 'time_local', 'remote_user', 'request', 'path', 'protocol', 'verb', 'route', 'http_referer', 'http_user_agent'], axis=1
)  # comes from nginx_df
merged_df = merged_df.rename({'status_x': 'status'})  # comes from nginx_df status but gets renamed after joining
merged_df = merged_df.drop(['status_y'], axis=1)  # came from ip_api_df status but gets renamed after joining
merged_df = merged_df.drop(['query', 'countryCode', 'region', 'zip', 'lat', 'lon', 'timezone', 'isp', 'org', 'as'], axis=1)  # comes from ip_api_df
# merged_df = merged_df.drop(['agents'], axis=1)

categoricals = merged_df.select_dtypes(include=['object']).columns.tolist()
merged_df[categoricals] = merged_df[categoricals].astype('category')

onehot_df = pd.get_dummies(merged_df, drop_first=True)
CSV_ONEHOT = os.path.join(DSMLAI_CSVS_DIRPATH, 'one-hot.csv')
onehot_df.to_csv(CSV_ONEHOT, index=False)
