import os
import sys
import re
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

############ LITERALLY PROCESS THE ACCESS LOGS INTO A CSV

# $remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"'
NGINX_LOG_FORMAT = (
    r'^'
    r'(?P<remote_addr>\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}) - '
    r'(?P<remote_user>[-]) '
    r'\[(?P<time_local>\d{2}\/[A-Z][a-z]{2}\/\d{4}\:\d{2}\:\d{2}\:\d{2} \+\d{4})\] '
    r'"(?P<request>.*)" '
    r'(?P<status>\d+) '
    r'(?P<body_bytes_sent>\d+) '
    r'"(?P<http_referer>.*)" '
    r'"(?P<http_user_agent>.*)"'
    r'$'
)
NGINX_LOG_FORMAT_REGEX = re.compile(NGINX_LOG_FORMAT, flags=re.IGNORECASE)

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

rows = []
for f, filepath in enumerate(access_logs):
    try:
        with open(filepath, encoding='utf-8') as r:
            lines = r.read().splitlines()
        for i, line in enumerate(lines):
            mo = NGINX_LOG_FORMAT_REGEX.match(line)
            if not mo:
                print(f'"{filepath}", line {i}: {line}')
                raise RuntimeError()
            rows.append(mo.groupdict())
    except Exception:
        print('failed on file', f, f'"{filepath}"')
        raise

CSV_ACCESS = os.path.join(DSMLAI_CSVS_DIRPATH, 'access.csv')
df = pd.DataFrame(rows)
df.to_csv(CSV_ACCESS, index=False)

############ DERIVE SOME INTERESTING DATA

if SCRIPT_DIRPATH not in sys.path:
    sys.path.append(SCRIPT_DIRPATH)
import constants

importlib.reload(constants)

nginx_df = df.copy()
nginx_df['time_local'] = nginx_df['time_local'].apply(lambda x: datetime.datetime.strptime(x, '%d/%b/%Y:%H:%M:%S %z'))
nginx_df['timestamp_local'] = nginx_df['time_local'].astype(np.int64) // 10**9
nginx_df[['verb', 'path']] = nginx_df['request'].str.split(' ', n=1, expand=True)
nginx_df[['route', 'protocol']] = nginx_df['path'].str.rsplit(' ', n=1, expand=True)
nginx_df['referer_expected'] = nginx_df['http_referer'].apply(lambda x: x in constants.EXPECTED_REFERERS)
nginx_df['route_depth'] = nginx_df['route'].str.split('/').apply(lambda x: len(x) if isinstance(x, list) else -1)
nginx_df['route_length'] = nginx_df['route'].str.len()
nginx_df['route_length'] = nginx_df['route_length'].fillna(0)
nginx_df['route_asbytes'] = nginx_df['route'].apply(lambda x: 0 if not x else len(re.findall(r'[\x00-\x7F]', x)))
nginx_df['route_expected'] = nginx_df['route'].apply(lambda x: x in constants.EXPECTED_ROUTES)
nginx_df['verb_length'] = nginx_df['verb'].str.len()
nginx_df['verb_asbytes'] = nginx_df['verb'].apply(lambda x: 0 if not x else len(re.findall(r'[\x00-\x7F]', x)))
nginx_df['verb_expected'] = nginx_df['verb'].apply(lambda x: x in constants.EXPECTED_VERBS)
nginx_df['protocol_expected'] = nginx_df['protocol'].apply(lambda x: x in constants.EXPECTED_PROTOCOLS)
nginx_df['crawler'] = nginx_df['http_user_agent'].str.contains('://')

############ SAVE IT OFF FOR LATER USE

CSV_ACCESS1 = os.path.join(DSMLAI_CSVS_DIRPATH, 'access1.csv')
nginx_df.to_csv(CSV_ACCESS1, index=False)
