import os
import sys
import datetime
import importlib
import multiprocessing

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.manifold import TSNE
from sklearn.cluster import KMeans
from sklearn import metrics

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

scaler = StandardScaler()
scaled_data = pd.DataFrame(scaler.fit_transform(onehot_df))

CSV_INFO = os.path.join(DSMLAI_CSVS_DIRPATH, 'merged2.csv')
original_info_df = pd.read_csv(CSV_INFO)

############ K-MEANS BY VISUAL PERPLEXITY, TAKES A LONG TIME, FEEL FREE TO SKIP

tsne_reduced_data = TSNE(n_components=2, n_jobs=WORKERS, random_state=RS).fit_transform(scaled_data)
tsne_2d_data = pd.DataFrame(tsne_reduced_data, columns=(['reduced feature 1', 'reduced feature 2']))

# roughly without perplexity, where are the clusters? (this takes a WHILE)
NAIVE_TSNE_PNG = os.path.join(ML_DIRPATH, 'k-means-cluster-naive.png')
plt.figure(figsize=(8, 4.5))
sns.scatterplot(data=tsne_2d_data, x='reduced feature 1', y='reduced feature 2')
plt.tight_layout()
plt.savefig(NAIVE_TSNE_PNG)

# with perplexity, where are the clusters? (THIS TAKES FOREVER)
PERPLEX_TSNE_PNG = os.path.join(ML_DIRPATH, 'k-means-cluster-perplex.png')
perplexities = [1, 2, 4, 8, 16, 32, 48, 64, 96, 128, 196, 256]
cols = 4
rows = len(perplexities) / cols
plt.figure(figsize=(32, 27))
for i, perplexity in enumerate(perplexities):
    tsne = TSNE(n_components=2, perplexity=perplexity, n_jobs=WORKERS, random_state=RS)
    X_red = tsne.fit_transform(scaled_data)
    red_data_df = pd.DataFrame(data=X_red, columns=['reduced feature 1', 'reduced feature 2'])  # creating a new dataframe with reduced dimensions
    plt.subplot(rows, cols, i + 1)
    plt.title(f'perplexity={perplexity}')
    sns.scatterplot(data=red_data_df, x='reduced feature 1', y='reduced feature 2')
    plt.tight_layout(pad=2)

plt.savefig(PERPLEX_TSNE_PNG)

input('slow this down, cowboy')

# visually chosing k - looks like 3 clusters now
k = 8
cluster_model = KMeans(n_clusters=k, random_state=RS).fit(scaled_data)

CSV_MERGED = os.path.join(DSMLAI_CSVS_DIRPATH, 'merged3.csv')
perplex_merged_df = pd.read_csv(CSV_MERGED)

CSV_CLUSTER_PERPLEX = os.path.join(ML_DIRPATH, f'merged+perplexity+{k}-clusters.csv')
columns = perplex_merged_df.columns.tolist()
perplex_merged_df['cluster'] = cluster_model.labels_
perplex_merged_df.to_csv(CSV_CLUSTER_PERPLEX, index=False)

perplex_result_df = pd.DataFrame(
    zip(
        perplex_merged_df.groupby(['cluster'])['cluster'].count(),
        perplex_merged_df.groupby(['cluster'])['route_expected'].sum(),
        perplex_merged_df.groupby(['cluster'])['probably_human'].sum(),
    ),
    columns=['cluster-count', 'route_expected-sum', 'probably_human-sum']
)
CSV_CLUSTER_PERPLEX_RESULT = os.path.join(ML_DIRPATH, f'merged+perplexity+{k}-clusters-results.csv')
print(perplex_result_df)
perplex_result_df.to_csv(CSV_CLUSTER_PERPLEX_RESULT, index=False)

############ K-MEANS BY SILHOUETTE

scores = []
for i in range(2, 11):
    model = KMeans(n_clusters=i, random_state=RS).fit(scaled_data)
    score = metrics.silhouette_score(scaled_data, model.labels_)
    scores.append(score)

ELBOW_PNG = os.path.join(ML_DIRPATH, 'k-means-cluster-elbow.png')
plt.figure()
plt.plot(range(2, 11), scores, marker='o')
plt.title('silhouette')
plt.xlabel('k clusters')
plt.ylabel('score')
plt.xticks(range(2, 11))
plt.grid(True)
plt.savefig(ELBOW_PNG)
plt.show()

# chose the k based on the first elbow - looks like 9 clusters now
k = 4
cluster_model = KMeans(n_clusters=k, random_state=RS).fit(scaled_data)

CSV_MERGED = os.path.join(DSMLAI_CSVS_DIRPATH, 'merged3.csv')
elbow_merged_df = pd.read_csv(CSV_MERGED)

CSV_CLUSTER_PERPLEX = os.path.join(ML_DIRPATH, f'merged+elbow+{k}-clusters.csv')
columns = elbow_merged_df.columns.tolist()
elbow_merged_df['cluster'] = cluster_model.labels_
elbow_merged_df.to_csv(CSV_CLUSTER_PERPLEX, index=False)

elbow_result_df = pd.DataFrame(
    zip(
        elbow_merged_df.groupby(['cluster'])['cluster'].count(),
        elbow_merged_df.groupby(['cluster'])['route_expected'].sum(),
        elbow_merged_df.groupby(['cluster'])['probably_human'].sum(),
    ),
    columns=['cluster-count', 'route_expected-sum', 'probably_human-sum']
)
print(elbow_result_df)
CSV_CLUSTER_ELBOW_RESULT = os.path.join(ML_DIRPATH, f'merged+elbow+{k}-clusters-results.csv')
print(perplex_result_df)
elbow_result_df.to_csv(CSV_CLUSTER_ELBOW_RESULT, index=False)
