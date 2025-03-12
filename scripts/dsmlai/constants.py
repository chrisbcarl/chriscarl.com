import os
import re
import datetime
import importlib
import multiprocessing

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

HOME_PAGE_ROUTES = set(
    # omitting '/', '/favicon.ico', '/files/favicon.ico' because everyone has those routes
    [
        # less common
        '/assets/fontawesome/file-pdf-solid.svg',
        '/assets/fontawesome/linkedin-in-brands-solid.svg',
        '/assets/fontawesome/github-brands-solid.svg',
        '/assets/fontawesome/youtube-brands-solid.svg',
        '/assets/paths.js',
    ]
)
EXPECTED_ROUTES = set([ele for ele in HOME_PAGE_ROUTES])
EXPECTED_ROUTES.update([
    '/files/resume-2025.02.13-D5.pdf',
    # # way too common ones
    '/',
    '/favicon.ico',
    '/files/favicon.ico',
])
EXPECTED_PROTOCOLS = set(['HTTP/1.1', 'HTTP/1.0'])
EXPECTED_VERBS = set(['GET'])
EXPECTED_REFERERS = set(['http://chriscarl.com', 'http://www.chriscarl.com', 'http://159.54.179.175'])
EXPECTED_REFERERS.update([f'{uri}/' for uri in EXPECTED_REFERERS])
EXPECTED_REFERERS.update([ele.replace('http:', 'https:') for ele in EXPECTED_REFERERS])
EXPECTED_REFERERS.update(['https://www.google.com/', 'https://www.bing.com/', 'https://duckduckgo.com/', 'https://www.linkedin.com/'])
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

OSES = ['CentOS', 'Debian', 'Debian-2', 'Debian-3', 'Fedora', 'Kubuntu', 'Linux', 'Macintosh', 'Ubuntu', 'WinNT', 'Windows', 'X11']
MOBILE = ['Android', 'iPad', 'iPhone', 'iPod']
USER_AGENTS = {}
KNOWN_WORTHLESS = [
    'https',
    'compatible',
    'Mini',  # opera mini
    'Mobi',  # opera mobi
    'Version',  # Version/4.0
    'Hello',  # hello world stuff
    'Hello,',  # hello world stuff
]
QUESTIONABLE = ['Edition', 'Mobi', '0x27000634', '2', '2009', '5', 'Debian-2', 'Debian-3']


def pick_os(lst):
    for ele in lst:
        if ele in OSES:
            return ele
    return None


def pick_mobile(lst):
    for ele in lst:
        if ele in MOBILE:
            return ele
    return None


def parse_user_agent(user_agent):
    original_user_agent = user_agent
    first = user_agent.split(' ')[0]
    lst = [first.split('/')[0]]
    user_agent = user_agent.replace(first, '')
    user_agent = re.sub(r'g\(\d+\)', '', user_agent)  # moto g(7)
    if 'Not(A:Brand' in user_agent:
        lst.append('Not(A:Brand')
        user_agent = user_agent.replace('Not(A:Brand', '')
    # companies = re.findall(r'([\w-]+),', user_agent)
    # if 'Expanse' in companies:
    #     companies = ['Expanse']
    parenthesis = re.findall(r'\(([\w-]+)', user_agent)
    clients = re.findall(r' ([A-za-z\d-]+)\/v?[\d\/\.]+', user_agent)
    lst += parenthesis + clients
    for ele in KNOWN_WORTHLESS:
        if ele in lst:
            lst.remove(ele)
    if lst == ['-']:  # no agent provided:
        lst = [None]
    row = dict(
        http_user_agent=original_user_agent,
        agents=lst,
        agent_os=pick_os(lst),
        agent_mobile=pick_mobile(lst),
        agent_str_ascending='-'.join(sorted([str(ele) for ele in lst], key=lambda ele: USER_AGENTS.get(ele, 0), reverse=True)),
        agent_str_descending='-'.join(sorted([str(ele) for ele in lst], key=lambda ele: USER_AGENTS.get(ele, 0), reverse=False)),
        agents_count=len(lst),
    )
    if any(ele in lst for ele in QUESTIONABLE):
        print('!!!!!!!', user_agent, lst)
    # row.update({k: True for k in lst})
    for k in lst:
        if k not in USER_AGENTS:
            USER_AGENTS[k] = 0
        USER_AGENTS[k] += 1

    return row


def access_log_line_to_dict(line):
    mo = NGINX_LOG_FORMAT_REGEX.match(line)
    if not mo:
        raise RuntimeError()
    access_dick = mo.groupdict()

    remote_addr = access_dick['remote_addr']
    remote_user = access_dick['remote_user']
    time_local = access_dick['time_local']
    request = access_dick['request']
    status = access_dick['status']
    body_bytes_sent = access_dick['body_bytes_sent']
    http_referer = access_dick['http_referer']
    http_user_agent = access_dick['http_user_agent']

    time_local = datetime.datetime.strptime(time_local, '%d/%b/%Y:%H:%M:%S %z')
    timestamp_local = int(time_local.timestamp())
    verb_path = request.split(' ', maxsplit=1)
    if len(verb_path) == 2:
        verb, path = verb_path
    else:
        verb, path = verb_path[0], ''
    route_protocol = path.split(' ', maxsplit=1)
    if len(route_protocol) == 2:
        route, protocol = route_protocol
    else:
        route, protocol = route_protocol[0], ''
    referer_expected = http_referer in EXPECTED_REFERERS
    route_depth = len(route.split('/'))
    route_length = len(route)
    route_asbytes = len(re.findall(r'[\x00-\x7F]', route))
    route_expected = route in EXPECTED_ROUTES
    route_home = route == '/'
    verb_length = len(verb)
    verb_asbytes = len(re.findall(r'[\x00-\x7F]', verb))
    verb_expected = verb in EXPECTED_VERBS
    protocol_expected = protocol in EXPECTED_PROTOCOLS
    crawler = '://' in http_user_agent

    row = dict(
        # can be deleted in later steps due to being compound and long
        time_local=time_local,
        verb=verb,
        path=path,
        route=route,
        protocol=protocol,
        # as atomic as possible
        remote_addr=remote_addr,
        remote_user=remote_user,
        timestamp_local=timestamp_local,
        status=status,
        body_bytes_sent=body_bytes_sent,
        referer_expected=referer_expected,
        route_depth=route_depth,
        route_length=route_length,
        route_asbytes=route_asbytes,
        route_expected=route_expected,
        route_home=route_home,
        verb_length=verb_length,
        verb_asbytes=verb_asbytes,
        verb_expected=verb_expected,
        protocol_expected=protocol_expected,
        crawler=crawler,
    )

    agents_dick = parse_user_agent(http_user_agent)
    del agents_dick['http_user_agent']
    del agents_dick['agents']

    row.update(agents_dick)
    return row


def plot_important_features(name, model, X, dirpath, greater_than=0.001):
    importances = model.feature_importances_
    indices = np.argsort(importances)
    feature_names = list(X.columns)

    importance_df = pd.DataFrame(zip(feature_names, importances), columns=['name', 'importance'], index=indices)
    importance_df = importance_df[importance_df['importance'] > greater_than].reset_index(drop=True)

    plt.figure(figsize=(12, 12))
    plt.title(f'{model.__class__.__name__} Feature Importances > {greater_than * 100:0.2f}%')
    plt.barh(importance_df.index, importance_df['importance'], color='violet', align='center')
    plt.yticks(importance_df.index, importance_df['name'])
    plt.xlabel(f'{name} Relative Importance')
    plt.savefig(os.path.join(dirpath, f'{name}_important-features.png'))
