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
merged_df['agents'] = merged_df['agents'].apply(lambda lst: eval(lst))

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
            agents_count = merged_df.loc[next_3_seconds.index, 'agents_count'].mean()
            if set(next_3_seconds['route']).issuperset(constants.HOME_PAGE_ROUTES) and agents_count > 4:
                print('human at', remote_addr, 'agent count', agents_count)
                merged_df.loc[next_3_seconds.index, ['probably_human']] = True

# export the likely humans
probably_human_vcs = merged_df.groupby(['remote_addr'])['probably_human'].sum().sort_values(ascending=False)
probably_human_vcs = probably_human_vcs[probably_human_vcs > 0]
CSV_PROBABLY_HUMANS_FREQ = os.path.join(DSMLAI_CSVS_DIRPATH, 'probably_humans-freq.csv')
probably_human_vcs.to_csv(CSV_PROBABLY_HUMANS_FREQ)
print(
    'probably only', len(probably_human_vcs), 'humans showed up, and account for', probably_human_vcs.sum(), 'or',
    probably_human_vcs.sum() / merged_df.shape[0] * 100, '% of the traffic'
)

probably_human_df = merged_df[merged_df['remote_addr'].str.contains('|'.join(probably_human_vcs.index), case=False)]
probably_human_df = probably_human_df.sort_values(by=['remote_addr', 'time_local'], ascending=[True, True])
CSV_PROBABLY_HUMANS = os.path.join(DSMLAI_CSVS_DIRPATH, 'probably_humans.csv')
probably_human_df.to_csv(CSV_PROBABLY_HUMANS, index=False)

# remove developer humans
# merged_df[merged_df['remote_addr'] == '73.93.77.135'].sort_values(by=['time_local'], ascending=[False])[0:15]
all_indexes = merged_df[merged_df['remote_addr'] == '73.93.77.135'].index
first_time_index = (merged_df['remote_addr'] == '73.93.77.135') & (merged_df['route'] == '/files/favicon.ico')
first_time_idx = merged_df[first_time_index].index[0]
route_indexes = [first_time_idx]
for route in list(constants.HOME_PAGE_ROUTES) + ['/']:
    route_idx = merged_df[(merged_df.index < first_time_idx) & (merged_df['route'] == route)].index.max()
    route_indexes.append(route_idx)

keep_subdf = merged_df.loc[sorted(route_indexes)]
merged_df = merged_df.drop(all_indexes, axis=0)
merged_df = pd.concat([merged_df, keep_subdf])

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

# # possibly display humans
# for g, subdf in nginx_df[(nginx_df['route_expected'] == True)].groupby(['remote_addr']):
#   print(g, subdf)

CSV_MERGED = os.path.join(DSMLAI_CSVS_DIRPATH, 'merged2.csv')
merged_df.to_csv(CSV_MERGED, index=False)

CSV_MERGED_SORTED = os.path.join(DSMLAI_CSVS_DIRPATH, 'merged2-sorted.csv')
merged_df.sort_values(by=['remote_addr', 'timestamp_local']).to_csv(CSV_MERGED_SORTED, index=False)

# merged_df[merged_df['remote_addr'] == remote_addr]
# merged_df[merged_df['remote_addr'] == '73.93.77.135']
# merged_df[merged_df['remote_addr'] == '73.93.77.135']['timestamp_local'].rolling(2).apply(lambda s: s.max() - s.min())
# merged_df[['remote_addr', 'time_local', 'timestamp_local', 'request', 'http_user_agent', 'time_relative_to_last']][:35]

# merged_df = merged_df.drop(['remote_addr', 'time_local', 'http_referer', 'protocol', 'verb', 'route'], axis=1)
CSV_MERGED = os.path.join(DSMLAI_CSVS_DIRPATH, 'merged3.csv')
merged_df.to_csv(CSV_MERGED, index=False)
