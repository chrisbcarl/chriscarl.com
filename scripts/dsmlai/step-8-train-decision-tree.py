import os
import sys
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

############ LOAD AND ENCODE

if SCRIPT_DIRPATH not in sys.path:
    sys.path.append(SCRIPT_DIRPATH)
import constants

importlib.reload(constants)

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
# search_over.best_score_  had 0.99... not even trolling.
