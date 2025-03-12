import os
import sys
import datetime
import importlib
import multiprocessing

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import RandomUnderSampler
from sklearn import metrics
from sklearn.manifold import TSNE
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

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

CSV_ONEHOT = os.path.join(DSMLAI_CSVS_DIRPATH, 'one-hot.csv')
onehot_df = pd.read_csv(CSV_ONEHOT)

############ OVERUNDER SAMPLE

X = onehot_df  # .drop(['probably_human'], axis=1)
y = onehot_df['probably_human']

# X_under, _ = RandomUnderSampler(random_state=RS, sampling_strategy=0.6).fit_resample(X, y)
X_over, _ = SMOTE(random_state=RS, sampling_strategy=0.6, k_neighbors=5).fit_resample(X, y)

############ WE ARE NEVER GOING TO USE THE y_ BECAUSE THIS IS CLUSTERING

scaler = StandardScaler()
# we actually DONT want 'probably_human' as one of the "factors"
scaled_data = pd.DataFrame(scaler.fit_transform(X.drop(['probably_human'], axis=1)))
# scaled_data_under = pd.DataFrame(scaler.fit_transform(X_under))
scaled_data_over = pd.DataFrame(scaler.fit_transform(X_over.drop(['probably_human'], axis=1)))

Xs = {
    'norm': X,
    # 'under': X_under,
    'over': X_over,
}
scaled_data_dfs = {
    'norm': scaled_data,
    # 'under': scaled_data_under,
    'over': scaled_data_over,
}

############ K-MEANS BY SILHOUETTE
for name, scaled_df in scaled_data_dfs.items():
    print('clustering and elbowing on', name)
    scores = []
    for i in range(2, 11):
        model = KMeans(n_clusters=i, random_state=RS).fit(scaled_df)
        score = metrics.silhouette_score(scaled_df, model.labels_)
        scores.append(score)

    ELBOW_PNG = os.path.join(ML_DIRPATH, f'k-means-cluster-elbow-{name}.png')
    plt.figure()
    plt.plot(range(2, 11), scores, marker='o')
    plt.title('silhouette')
    plt.xlabel('k clusters')
    plt.ylabel('score')
    plt.xticks(range(2, 11))
    plt.grid(True)
    plt.savefig(ELBOW_PNG)

input('slow down cowboy, ready?')

# chose the k based on the first elbow for each (first lowest local minimum)
scaled_data_k = {
    'norm': 4,
    # 'under': 2,
    'over': 8,
}
result_dfs = {}
for name, k in scaled_data_k.items():
    print('clustering on', name, k)
    cluster_model = KMeans(n_clusters=k, random_state=RS).fit(scaled_data_dfs[name])

    X_df = Xs[name]
    X_df['type'] = pd.Series([name] * X_df.shape[0])
    X_df['cluster'] = cluster_model.labels_
    CSV_X_DF = os.path.join(DSMLAI_CSVS_DIRPATH, f'X_df-{name}.csv')
    X_df.to_csv(CSV_X_DF, index=False)

    result_df = pd.DataFrame(
        zip(
            X_df.groupby(['cluster'])['cluster'].count(),
            X_df.groupby(['cluster'])['route_expected'].sum(),
            X_df.groupby(['cluster'])['probably_human'].sum(),
        ),
        columns=['cluster-count', 'route_expected-sum', 'probably_human-sum']
    )
    print(result_df)
    RESULT_CSV = os.path.join(ML_DIRPATH, f'merged+elbow+{name}-{k}-clusters_result.csv')
    result_df.to_csv(RESULT_CSV, index=False)
    result_dfs[name] = result_df
