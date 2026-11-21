"""Opt-in real Docker/Compose smoke test. Uses only disposable synthetic data.

Build first: docker build -t chatidy:auth-integration-v1 .
Run: python tests/container_smoke.py
No host ports, real provider, live host or existing volumes are used.
"""
import json
from pathlib import Path
import subprocess
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]


def run(*args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs).strip()


def main():
    suffix = uuid.uuid4().hex[:12]
    network = 'dnet_chatidy_smoke_' + suffix
    volume = 'chatidy_smoke_' + suffix
    with tempfile.TemporaryDirectory(prefix='chatidy-synthetic-') as directory:
        env = Path(directory) / 'review.env'
        secret = Path(directory) / 'synthetic-secret'
        secret.write_text('synthetic-only-container-secret')
        # Parent stays private; Compose file secrets are read-only bind mounts.
        secret.chmod(0o444)
        env.write_text('\n'.join([
            'CHATIDY_PUBLIC_ORIGIN=https://app.example.invalid',
            'CHATIDY_TRUSTED_PROXIES=127.0.0.1/32',
            'CHATIDY_OIDC_ISSUER=https://idp.example.invalid/issuer/',
            'CHATIDY_OIDC_AUTHORIZE=https://idp.example.invalid/authorize',
            'CHATIDY_OIDC_TOKEN=https://idp.example.invalid/token',
            'CHATIDY_OIDC_JWKS=https://idp.example.invalid/jwks',
            'CHATIDY_OIDC_CLIENT_ID=synthetic-client',
            'CHATIDY_OIDC_END_SESSION=https://idp.example.invalid/logout',
            'CHATIDY_OIDC_CLIENT_SECRET_FILE=' + str(secret),
            'CHATIDY_PROXY_NETWORK=' + network,
            'CHATIDY_EGRESS_NETWORK=' + network + '_egress',
            'CHATIDY_DATA_VOLUME=' + volume,
        ]) + '\n')
        compose = ['docker', 'compose', '--env-file', str(env), '-p', 'chatidy-smoke-' + suffix,
                   '-f', str(ROOT / 'compose.yaml')]
        config = json.loads(run(*compose, 'config', '--format', 'json'))
        service = config['services']['chatidy']
        assert not service.get('ports') and not service.get('privileged')
        assert service['read_only'] and service['user'] == '10001:10001'
        assert service['environment'].get('CHATIDY_OIDC_CLIENT_SECRET') is None
        run('docker', 'network', 'create', '--internal', network)
        try:
            run(*compose, 'up', '-d', '--no-build')
            container = run(*compose, 'ps', '-q', 'chatidy')
            for _ in range(30):
                health = run('docker', 'inspect', '--format', '{{.State.Health.Status}}', container)
                if health == 'healthy': break
                if health == 'unhealthy':
                    print(run('docker', 'logs', container))
                    print(run('docker', 'inspect', '--format', '{{json .State.Health}}', container))
                    raise RuntimeError('Container healthcheck failed')
                time.sleep(1)
            assert health == 'healthy'
            inspection = json.loads(run('docker', 'inspect', container))[0]
            assert inspection['HostConfig']['ReadonlyRootfs']
            assert not inspection['HostConfig']['Privileged']
            assert not inspection['NetworkSettings']['Ports']
            # Entire check executes inside the isolated container; no host binding.
            script = r'''
import json, os, time, http.client
from contextlib import closing
from chatidy.db import connect
from chatidy.enroll import enroll
from chatidy.users import enrolled_user
from chatidy.auth_state import issue_session
from chatidy.healthcheck import main as healthcheck
assert os.getuid() == 10001
from pathlib import Path
assert not Path('/app/.git').exists()
assert not Path('/app/.env').exists()
assert not Path('/run/secrets/build_ca').exists()
assert healthcheck() == 0
issuer = os.environ['CHATIDY_OIDC_ISSUER']
with closing(connect()) as db:
    assert db.execute('SELECT count(*) FROM users').fetchone()[0] == 0
    tokens=[]
    for subject in ('synthetic-a', 'synthetic-b'):
        enroll(db, issuer, subject, 'member', confirmed=True)
        tokens.append(issue_session(db, enrolled_user(db, issuer, subject)))
def request(path, token=None, value=None, forwarded=True):
    h={'Host':'app.example.invalid'}
    if forwarded: h.update({'X-Forwarded-Proto':'https','X-Forwarded-Host':'app.example.invalid'})
    if token: h['Cookie']='__Host-chatidy_session='+token
    body=None
    if value is not None:
        h.update({'Origin':'https://app.example.invalid','Content-Type':'application/json','X-Filename':'synthetic.json'})
        body=json.dumps(value)
    c=http.client.HTTPConnection('127.0.0.1',8877,timeout=5)
    try:
        c.request('POST' if body is not None else 'GET',path,body,h)
        r=c.getresponse(); raw=r.read()
        return r.status,json.loads(raw) if raw else None
    finally:c.close()
assert request('/api/stats')[0] == 401
assert request('/api/stats',tokens[0],forwarded=False)[0] == 403
assert request('/api/stats',tokens[0])[1]['chats'] == 0
chat={'id':'synthetic-a-chat','title':'Synthetic container SQLite','messages':[{'id':'m','role':'user','content':'Synthetic FTS sample'}]}
assert request('/api/import',tokens[0],chat)[0] == 200
assert request('/api/chats?q=FTS',tokens[0])[1][0]['id'] == chat['id']
assert request('/api/chat/'+chat['id'],tokens[1])[0] == 404
assert request('/api/chats?q=FTS',tokens[1])[1] == []
status,job=request('/api/import/jobs',tokens[0],chat)
assert status == 202
job_id=job['id']
for _ in range(100):
    status,job=request('/api/import/jobs/'+job_id,tokens[0])
    if job['state'] in ('done','error'):break
    time.sleep(.05)
assert job['state'] == 'done'
assert request('/api/import/jobs',tokens[1])[1]['count'] == 0
assert request('/api/import/jobs/'+job_id,tokens[1])[0] in (400,404)
assert request('/api/import/jobs/'+job_id+'/delete',tokens[1],{'confirm':True})[0] in (400,404)
assert request('/api/import/jobs/'+job_id+'/delete',tokens[0],{'confirm':True})[0] == 200
assert request('/api/stats',tokens[0])[1]['chats'] == 1
assert oct(os.stat('/data/accounts/1').st_mode & 0o777) == '0o700'
assert oct(os.stat('/data/registry.sqlite3').st_mode & 0o777) == '0o600'
print('PASS: non-root, health, auth, migration, SQLite/FTS, two-account data/job isolation, confirmed cleanup')
'''
            print(run('docker', 'exec', '-i', container, 'python', '-', input=script))
            run(*compose, 'restart', 'chatidy')
            for _ in range(30):
                if subprocess.run(['docker', 'exec', container, 'python', '-m', 'chatidy.healthcheck'],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0: break
                time.sleep(1)
            persistence = '''from contextlib import closing
from chatidy.db import connect
from chatidy.library_scope import account_library
from chatidy.users import enrolled_user
import os
with closing(connect()) as db:
    assert db.execute('SELECT count(*) FROM users').fetchone()[0] == 2
    user = enrolled_user(db, os.environ['CHATIDY_OIDC_ISSUER'], 'synthetic-a')
with account_library(user, os.environ['CHATIDY_DB']):
    with closing(connect()) as db:
        assert db.execute('SELECT count(*) FROM conversations').fetchone()[0] == 1
print('PASS: registry and account library survive container restart')
'''
            print(run('docker', 'exec', '-i', container, 'python', '-', input=persistence))
        finally:
            # Only this run's randomly named synthetic resources are removed.
            subprocess.run([*compose, 'down', '--volumes'], check=True, stdout=subprocess.DEVNULL)
            run('docker', 'network', 'rm', network)


if __name__ == '__main__':
    main()
