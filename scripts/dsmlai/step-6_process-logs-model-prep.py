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

CSV_MERGED = os.path.join(DSMLAI_CSVS_DIRPATH, 'merged2.csv')
merged_df = pd.read_csv(CSV_MERGED)
merged_df['time_local'] = pd.to_datetime(merged_df['time_local'])

merged_df = merged_df.drop(['remote_addr', 'time_local', 'http_referer', 'protocol', 'verb', 'route'], axis=1)

CSV_MERGED = os.path.join(DSMLAI_CSVS_DIRPATH, 'merged3.csv')
merged_df.to_csv(CSV_MERGED, index=False)
