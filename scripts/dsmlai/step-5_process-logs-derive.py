import os
import sys
import datetime
import importlib

import numpy as np
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

############ DERIVE SOME INTERESTING DATA

if SCRIPT_DIRPATH not in sys.path:
    sys.path.append(SCRIPT_DIRPATH)
import constants

importlib.reload(constants)

CSV_MERGED = os.path.join(DSMLAI_CSVS_DIRPATH, 'merged1.csv')
merged_df = pd.read_csv(CSV_MERGED)
merged_df['time_local'] = pd.to_datetime(merged_df['time_local'])

# this is definitely affirming the conclusion, but I want some stronger clustering, so I'll reduce the features and add some more thumb on the scale stuff, like indicators that things are bad or good or valid or invalid.
merged_df['probably_human'] = pd.Series([False] * merged_df.shape[0])
# for every ip address, find the first time it accessed /, look ahead 3 seconds, if all routes were covered, then its legit.
for group, subdf in merged_df.groupby(['remote_addr']):
    remote_addr = group[0]
    # if remote_addr != '73.93.77.135':
    #     continue
    happened = subdf[subdf['route'] == '/']
    for idx in happened.index:
        row = subdf.loc[idx]
        start = row['time_local'].to_pydatetime()
        next_3_seconds = subdf[(start <= subdf['time_local']) & (subdf['time_local'] < start + datetime.timedelta(seconds=3))]
        if len(next_3_seconds) > 4:
            # print(set(next_3_seconds['route']), EXPECTED_ROUTES)
            if set(next_3_seconds['route']).issuperset(constants.EXPECTED_ROUTES):
                # print('human at', remote_addr)
                merged_df.loc[next_3_seconds.index, ['probably_human']] = True

# TODO: THIS STILL DOESNT QUITE WORK
# requests USUALLY come right after the previous request. humans load everything at once from expected routes, bots and attackers like to space out their attacks and try random shit
merged_df['time_relative_to_last'] = pd.Series([-1] * merged_df.shape[0], dtype=float)
for group, subdf in merged_df.groupby(['remote_addr']):
    remote_addr = group[0]
    # if remote_addr == '73.93.77.135':
    #     break
    #     continue
    merged_df.loc[subdf.index, ['time_relative_to_last']] = subdf['timestamp_local'].rolling(2).apply(lambda s: s.max() - s.min())
merged_df['time_relative_to_last'] = merged_df['time_relative_to_last'].fillna(-1)  # TODO: make sure makes sense

CSV_MERGED = os.path.join(DSMLAI_CSVS_DIRPATH, 'merged2.csv')
merged_df.to_csv(CSV_MERGED, index=False)

CSV_MERGED_SORTED = os.path.join(DSMLAI_CSVS_DIRPATH, 'merged2-sorted.csv')
merged_df.sort_values(by=['remote_addr', 'timestamp_local']).to_csv(CSV_MERGED_SORTED, index=False)

# merged_df[merged_df['remote_addr'] == remote_addr]
# merged_df[merged_df['remote_addr'] == '73.93.77.135']
# merged_df[merged_df['remote_addr'] == '73.93.77.135']['timestamp_local'].rolling(2).apply(lambda s: s.max() - s.min())
# merged_df[['remote_addr', 'time_local', 'timestamp_local', 'request', 'http_user_agent', 'time_relative_to_last']][:35]
