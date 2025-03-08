import os
import re
import datetime
import gzip
import shutil
try:
    SCRIPT_DIRPATH = os.path.dirname(__file__)
except Exception:
    SCRIPT_DIRPATH = 'scripts/parse-logs'
REPO_DIRPATH = os.path.abspath(os.path.join(SCRIPT_DIRPATH, '../../'))
VAR_LOG_DIRPATH = os.path.abspath(os.path.join(REPO_DIRPATH, 'ignoreme/159.54.179.175/var/log'))

access_logs = []
auth_logs = []
for d, _, fs in os.walk(VAR_LOG_DIRPATH):
    for f in fs:
        ext = os.path.splitext(f)[1]
        filepath = os.path.join(d, f)
        if ext.lower() == '.gz':
            txtpath = os.path.join(d, f)[:-3]
            print(filepath, txtpath)
            with gzip.open(filepath, 'rb') as f_in, open(txtpath, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
            if 'access.log' in txtpath:
                access_logs.append(txtpath)
        elif 'auth.log' in filepath:
            auth_logs.append(filepath)

# $remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"'
LOG_FORMAT = (
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
LOG_FORMAT_REGEX = re.compile(LOG_FORMAT, flags=re.IGNORECASE)
import pandas as pd
rows = []
for f, filepath in enumerate(access_logs):
    with open(filepath, encoding='utf-8') as r:
        lines = r.read().splitlines()
    for l, line in enumerate(lines):
        mo = LOG_FORMAT_REGEX.match(line)
        if not mo:
            print(f'"{filepath}", line {l}: {line}')
            raise RuntimeError()
        rows.append(mo.groupdict())

df = pd.DataFrame(rows)
print(df)
