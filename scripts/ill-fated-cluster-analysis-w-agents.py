'''
I swear to god this worked like 30 mins ago, clearly stale dfs somewhere
the point is this overal shape is fine so i can refer back to it.
'''

import os
import pandas as pd
import numpy as np

try:
    SCRIPT_DIRPATH = os.path.dirname(__file__)
except Exception:
    SCRIPT_DIRPATH = 'scripts/parse-logs'
REPO_DIRPATH = os.path.abspath(os.path.join(SCRIPT_DIRPATH, '../../'))
VAR_LOG_DIRPATH = os.path.abspath(os.path.join(REPO_DIRPATH, 'ignoreme/159.54.179.175/var/log'))
IGNOREME_DIRPATH = os.path.join(REPO_DIRPATH, 'ignoreme')
EVERYTHING_DUMMIES_CSV = os.path.join(IGNOREME_DIRPATH, 'everything+agents_dummies.csv')
RS = 0

everything_dummies = pd.read_csv(EVERYTHING_DUMMIES_CSV)
everything_dummies['time_local'] = pd.to_datetime(everything_dummies['time_local'])
everything_dummies['time_local'] = everything_dummies['time_local'].astype(np.int64) // 10**9
everything_dummies = everything_dummies.fillna('')
categoricals = everything_dummies.select_dtypes(include=['object']).columns.tolist()
everything_dummies[categoricals] = everything_dummies[categoricals].astype('category')

from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
scaled_data = pd.DataFrame(scaler.fit_transform(everything_dummies))

# VISUALLY REPRESENTING CLUSTERS
import multiprocessing
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE

WORKERS = multiprocessing.cpu_count() // 4 * 3

tsne_reduced_data = TSNE(n_components=2, n_jobs=WORKERS, random_state=RS).fit_transform(scaled_data)
tsne_2d_data = pd.DataFrame(tsne_reduced_data, columns=(['reduced feature 1', 'reduced feature 2']))

# roughly without perplexity, where are the clusters?
sns.scatterplot(data=tsne_2d_data, x='reduced feature 1', y='reduced feature 2')
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

plt.show()

# END VISUALLY REPRESENTING

# scanning
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
plt.show()

# looks like 3,7,8 clusters
cluster_3 = KMeans(n_clusters=3, random_state=RS).fit(scaled_data)
cluster_7 = KMeans(n_clusters=7, random_state=RS).fit(scaled_data)
cluster_8 = KMeans(n_clusters=8, random_state=RS).fit(scaled_data)

EVERYTHING_AGENTS_CSV = os.path.join(IGNOREME_DIRPATH, 'everything+agents.csv')
everything_df = pd.read_csv(EVERYTHING_AGENTS_CSV)
columns = everything_df.columns.tolist()
columns.remove('agents')
everything_df_simpler = everything_df[columns].copy()
everything_df_simpler['3cluster'] = cluster_3.labels_
everything_df_simpler['7cluster'] = cluster_7.labels_
everything_df_simpler['8cluster'] = cluster_8.labels_

EVERYTHING_AGENTS_CLUSTERS_CSV = os.path.join(IGNOREME_DIRPATH, 'everything+agents-clusters.csv')
everything_df_simpler.to_csv(EVERYTHING_AGENTS_CLUSTERS_CSV)
