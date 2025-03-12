import os
import sys
import re
import datetime
import importlib
import multiprocessing

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn import metrics
from sklearn.model_selection import train_test_split
from imblearn.under_sampling import RandomUnderSampler
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import RandomizedSearchCV
from imblearn.over_sampling import SMOTE

try:
    SCRIPT_DIRPATH = os.path.dirname(__file__)
except Exception:
    SCRIPT_DIRPATH = 'scripts/dsmlai'
REPO_DIRPATH = os.path.abspath(os.path.join(SCRIPT_DIRPATH, '../../'))
IGNOREME_DIRPATH = os.path.join(REPO_DIRPATH, 'ignoreme')
DSMLAI_DIRPATH = os.path.join(IGNOREME_DIRPATH, 'dsmlai')
DSMLAI_LOGS_DIRPATH = os.path.join(DSMLAI_DIRPATH, 'logs')
DSMLAI_CSVS_DIRPATH = os.path.join(DSMLAI_DIRPATH, 'csvs')
ML_DIRPATH = os.path.join(DSMLAI_DIRPATH, 'ml')
if not os.path.isdir(DSMLAI_LOGS_DIRPATH):
    os.makedirs(DSMLAI_LOGS_DIRPATH)
if not os.path.isdir(DSMLAI_CSVS_DIRPATH):
    os.makedirs(DSMLAI_CSVS_DIRPATH)
if not os.path.isdir(ML_DIRPATH):
    os.makedirs(ML_DIRPATH)
WORKERS = multiprocessing.cpu_count() // 4 * 3
RS = 69

############ LOAD AND MANGLE AND ENCODE BUT ONLY FROM WHAT I CAN SEE IN THE ACCESS SINCE THATS ALL I WILL HAVE IN PRODUCTION

if SCRIPT_DIRPATH not in sys.path:
    sys.path.append(SCRIPT_DIRPATH)
import constants

importlib.reload(constants)

access_logs = []
auth_logs = []
for d, _, fs in os.walk(DSMLAI_LOGS_DIRPATH):
    for f in fs:
        ext = os.path.splitext(f)[1].lower()
        if ext == '.gz':
            continue
        filepath = os.path.join(d, f)
        if 'access.log' in f:
            access_logs.append(filepath)
        elif 'auth.log' in f:
            auth_logs.append(filepath)

access_rows = []
for access_log in access_logs:
    with open(access_log, encoding='utf-8') as r:
        lines = r.read().splitlines()
        access_rows.extend([constants.access_log_line_to_dict(line) for line in lines])

in_situ_df = pd.DataFrame(access_rows)

# this is definitely affirming the conclusion, but I want some stronger clustering, so I'll reduce the features and add some more thumb on the scale stuff, like indicators that things are bad or good or valid or invalid.
in_situ_df['probably_human'] = pd.Series([False] * in_situ_df.shape[0])
# for every ip address, find the first time it accessed /, look ahead 3 seconds, if all routes were covered, then its legit.
for group, subdf in in_situ_df.groupby(['remote_addr']):
    remote_addr = group[0]
    # if remote_addr != '73.93.77.135':
    #     continue
    happened = subdf[subdf['route_home']]
    for idx in happened.index:
        row = subdf.loc[idx]
        start = row['timestamp_local']
        next_3_seconds = subdf[(start <= subdf['timestamp_local']) & (subdf['timestamp_local'] < start + 3)]
        if len(next_3_seconds) > 4:
            # print(set(next_3_seconds['route']), EXPECTED_ROUTES)
            agents_count = in_situ_df.loc[next_3_seconds.index, 'agents_count'].mean()
            if next_3_seconds['route_expected'].all() and agents_count > 4:
                print('human at', remote_addr, 'agent count', agents_count)
                in_situ_df.loc[next_3_seconds.index, ['probably_human']] = True

# remove developer humans
# in_situ_df[in_situ_df['remote_addr'] == '73.93.77.135'].sort_values(by=['time_local'], ascending=[False])[0:15]
all_indexes = in_situ_df[in_situ_df['remote_addr'] == '73.93.77.135'].index
first_time_index = (in_situ_df['remote_addr'] == '73.93.77.135') & (in_situ_df['route'] == '/files/favicon.ico')
first_time_idx = in_situ_df[first_time_index].index[0]
route_indexes = [first_time_idx]
for route in list(constants.HOME_PAGE_ROUTES) + ['/']:
    route_idx = in_situ_df[(in_situ_df.index < first_time_idx) & (in_situ_df['route'] == route)].index.max()
    route_indexes.append(route_idx)

print('prior to removing dev user:', in_situ_df.shape)
keep_subdf = in_situ_df.loc[sorted(route_indexes)]
in_situ_df = in_situ_df.drop(all_indexes, axis=0)
in_situ_df = pd.concat([in_situ_df, keep_subdf])
print('posterior to removing dev user:', in_situ_df.shape)

# removing any last columns that were useful:
in_situ_df = in_situ_df.drop(['time_local', 'verb', 'path', 'route', 'protocol'], axis=1)

CSV_IN_SITU = os.path.join(DSMLAI_CSVS_DIRPATH, 'in-situ.csv')
in_situ_df.to_csv(CSV_IN_SITU, index=False)

############ DATA PREP FOR TRAINING

categoricals = in_situ_df.select_dtypes(include=['object']).columns.tolist()
in_situ_df[categoricals] = in_situ_df[categoricals].astype('category')

onehot_df = pd.get_dummies(in_situ_df, drop_first=True)
CSV_IN_SITU_DUMMIES = os.path.join(DSMLAI_CSVS_DIRPATH, 'in-situ-dummies.csv')
onehot_df.to_csv(CSV_IN_SITU_DUMMIES, index=False)

X = onehot_df.drop(['probably_human'], axis=1)
y = onehot_df['probably_human']
X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.4, random_state=RS, stratify=y)
X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=RS, stratify=y_temp)

Ys = {'all': y, 'train': y_train, 'val': y_val, 'test': y_test}
Xs = {'all': X, 'train': X_train, 'val': X_val, 'test': X_test}

X_train_under, y_train_under = RandomUnderSampler(random_state=RS, sampling_strategy=0.6).fit_resample(X_train, y_train)
X_train_over, y_train_over = SMOTE(random_state=RS, sampling_strategy=0.6, k_neighbors=5).fit_resample(X_train, y_train)

############ TRAINING

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
search_under = RandomizedSearchCV(rfc, search_parameters, n_iter=150, scoring=recall, cv=5, n_jobs=WORKERS).fit(X_train_under, y_train_under)  # , verbose=2
search_over = RandomizedSearchCV(rfc, search_parameters, n_iter=150, scoring=recall, cv=5, n_jobs=WORKERS).fit(X_train_over, y_train_over)  # , verbose=2

rfc_norm = RandomForestClassifier(**search_norm.best_params_).fit(X_train, y_train)
rfc_under = RandomForestClassifier(**search_under.best_params_).fit(X_train_under, y_train_under)
rfc_over = RandomForestClassifier(**search_over.best_params_).fit(X_train_over, y_train_over)

constants.plot_important_features('norm', rfc_norm, X, ML_DIRPATH, greater_than=0.001)
constants.plot_important_features('under', rfc_under, X, ML_DIRPATH, greater_than=0.001)
constants.plot_important_features('over', rfc_over, X, ML_DIRPATH, greater_than=0.001)

############ EVALUATION

rfc_norm_score = metrics.recall_score(y_test, rfc_norm.predict(X_test))
rfc_under_score = metrics.recall_score(y_test, rfc_under.predict(X_test))
rfc_over_score = metrics.recall_score(y_test, rfc_over.predict(X_test))
print('norm best', search_norm.best_score_, 'under best', search_under.best_score_, 'over best', search_over.best_score_)
print('rfc_norm_score', rfc_norm_score, 'rfc_under_score', rfc_under_score, 'rfc_over_score', rfc_over_score)

############ PREDICTION

# for prediction
# with open(r'ignoreme\dsmlai\logs\access.log.7') as r:
#     lines = r.read().splitlines()
# badd = lines[369]
# good = lines[343]  # to 348
# constants.access_log_line_to_dict(badd)
# constants.access_log_line_to_dict(good)
KNOWN_BAD_LINE = '65.49.20.69 - - [03/Mar/2025:12:38:05 +0000] "GET /.git/config HTTP/1.1" 404 134 "-" "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0"'
KNOWN_GOOD_LINE = '73.93.77.135 - - [03/Mar/2025:12:02:40 +0000] "GET /assets/fontawesome/file-pdf-solid.svg HTTP/1.1" 304 0 "http://chriscarl.com/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0"'

known_bad = constants.access_log_line_to_dict(KNOWN_BAD_LINE)
known_good = constants.access_log_line_to_dict(KNOWN_GOOD_LINE)

rows = [constants.access_log_line_to_dict(line) for line in lines]
df = pd.DataFrame(rows)
df

CSV_MERGED = os.path.join(DSMLAI_CSVS_DIRPATH, 'merged.csv')
merged_df = pd.read_csv(CSV_MERGED)  # contains nginx + agents pretty well derived
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
            agents_count = merged_df.loc[next_3_seconds.index, 'agents_count'].mean()
            if set(next_3_seconds['route']).issuperset(constants.HOME_PAGE_ROUTES) and agents_count > 4:
                print('human at', remote_addr, 'agent count', agents_count)
                merged_df.loc[next_3_seconds.index, ['probably_human']] = True

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

# nginx_df = nginx_df.drop(['remote_user', 'request', 'path'], axis=1)

# export the likely humans
probably_human_vcs = merged_df.groupby(['remote_addr'])['probably_human'].sum().sort_values(ascending=False)
probably_human_vcs = probably_human_vcs[probably_human_vcs > 0]
CSV_PROBABLY_HUMANS_FREQ = os.path.join(DSMLAI_CSVS_DIRPATH, 'probably_humans-freq.csv')
probably_human_vcs.to_csv(CSV_PROBABLY_HUMANS_FREQ)
print(
    'probably only', len(probably_human_vcs), 'humans showed up, and account for', probably_human_vcs.sum(), 'or',
    probably_human_vcs.sum() / merged_df.shape[0] * 100, '% of the traffic'
)

CSV_ONEHOT = os.path.join(DSMLAI_CSVS_DIRPATH, 'one-hot.csv')
onehot_df = pd.read_csv(CSV_ONEHOT)

X = onehot_df.drop(['probably_human'], axis=1)
y = onehot_df['probably_human']
X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.4, random_state=RS, stratify=y)
X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=RS, stratify=y_temp)

Ys = {'all': y, 'train': y_train, 'val': y_val, 'test': y_test}
Xs = {'all': X, 'train': X_train, 'val': X_val, 'test': X_test}

X_train_under, y_train_under = RandomUnderSampler(random_state=RS, sampling_strategy=0.6).fit_resample(X_train, y_train)
X_train_over, y_train_over = SMOTE(random_state=RS, sampling_strategy=0.6, k_neighbors=5).fit_resample(X_train, y_train)

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
search_under = RandomizedSearchCV(rfc, search_parameters, n_iter=150, scoring=recall, cv=5, n_jobs=WORKERS).fit(X_train_under, y_train_under)  # , verbose=2
search_over = RandomizedSearchCV(rfc, search_parameters, n_iter=150, scoring=recall, cv=5, n_jobs=WORKERS).fit(X_train_over, y_train_over)  # , verbose=2

rfc_norm = RandomForestClassifier(**search_norm.best_params_).fit(X_train, y_train)
rfc_under = RandomForestClassifier(**search_under.best_params_).fit(X_train_under, y_train_under)
rfc_over = RandomForestClassifier(**search_over.best_params_).fit(X_train_over, y_train_over)

constants.plot_important_features('norm', rfc_norm, X, ML_DIRPATH, greater_than=0.001)
constants.plot_important_features('under', rfc_under, X, ML_DIRPATH, greater_than=0.001)
constants.plot_important_features('over', rfc_over, X, ML_DIRPATH, greater_than=0.001)

rfc_norm_score = metrics.recall_score(y_test, rfc_norm.predict(X_test))
rfc_under_score = metrics.recall_score(y_test, rfc_under.predict(X_test))
rfc_over_score = metrics.recall_score(y_test, rfc_over.predict(X_test))
print('norm best', search_norm.best_score_, 'under best', search_under.best_score_, 'over best', search_over.best_score_)
print('rfc_norm_score', rfc_norm_score, 'rfc_under_score', rfc_under_score, 'rfc_over_score', rfc_over_score)

# holy shit... search_over.best_score_ == 0.9992063492063492
# so i'd better be REALLY FKCING SURE THAT MY PROBABLY_HUMAN LABEL IS CORRECT...
# note, xtrain under has only 296 rows... I dont like it.
# xtrain over has 10089, i like it.
