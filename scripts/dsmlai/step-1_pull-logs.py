import os
import gzip
import shutil

import paramiko

try:
    SCRIPT_DIRPATH = os.path.dirname(__file__)
except Exception:
    SCRIPT_DIRPATH = 'scripts/dsmlai'
REPO_DIRPATH = os.path.abspath(os.path.join(SCRIPT_DIRPATH, '../../'))
IGNOREME_DIRPATH = os.path.join(REPO_DIRPATH, 'ignoreme')
DSMLAI_DIRPATH = os.path.join(IGNOREME_DIRPATH, 'dsmlai')
DSMLAI_LOGS_DIRPATH = os.path.join(DSMLAI_DIRPATH, 'logs')
if not os.path.isdir(DSMLAI_LOGS_DIRPATH):
    os.makedirs(DSMLAI_LOGS_DIRPATH)

hostname = 'chriscarl.com'
port = 22
username = 'ubuntu'
pkey_filepath = os.path.abspath(os.path.expanduser('~/.ssh/id_rsa'))

ssh = paramiko.SSHClient()
ssh.load_system_host_keys()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(
    hostname,
    port=port,
    username=username,
    key_filename=pkey_filepath,
)

fileblobs = ['/var/log/auth.log', '/var/log/nginx/access*']
for fileblob in fileblobs:
    stdin_file, stdout_file, stderr_file = ssh.exec_command(f"ls {fileblob}")
    exit_code = stdout_file.channel.recv_exit_status()  # forces the exec_command to finish synchronously
    stderr = stderr_file.read()
    if exit_code != 0:
        print('skipping', fileblob, stderr)
        continue
    print('pulling', fileblob)
    stdout = stdout_file.read().decode('utf-8')
    sftp = ssh.open_sftp()
    for line in stdout.strip().splitlines():
        basename = line.split('/')[-1]
        print('pulling', fileblob, basename)
        sftp.get(line, os.path.join(DSMLAI_LOGS_DIRPATH, basename))
        # sftp.remove(remote_filepath)
    sftp.close()

ssh.close()  # we're done

access_logs = []
auth_logs = []
for d, _, fs in os.walk(DSMLAI_LOGS_DIRPATH):
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
