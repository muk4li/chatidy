"""Synthetic runtime/proxy regressions; no real provider or infrastructure."""
from contextlib import closing
from email.message import Message
import http.client
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer

from chatidy.db import connect
from chatidy.auth_state import issue_session, session_user
from chatidy.users import enrolled_user
from chatidy.runtime_config import listener, proxy_request_allowed
from chatidy.server import Handler, main

AUTH = importlib.util.find_spec('jwt') is not None
CONFIG = {
    'CHATIDY_AUTH_REQUIRED': '1', 'CHATIDY_PUBLIC_ORIGIN': 'https://app.example.invalid',
    'CHATIDY_OIDC_ISSUER': 'https://idp.example.invalid/issuer/',
    'CHATIDY_OIDC_AUTHORIZE': 'https://idp.example.invalid/authorize',
    'CHATIDY_OIDC_TOKEN': 'https://idp.example.invalid/token',
    'CHATIDY_OIDC_JWKS': 'https://idp.example.invalid/jwks',
    'CHATIDY_OIDC_CLIENT_ID': 'synthetic-client',
    'CHATIDY_OIDC_CLIENT_SECRET': 'synthetic-only-secret',
    'CHATIDY_OIDC_END_SESSION': 'https://idp.example.invalid/end-session',
    'CHATIDY_TRUSTED_PROXIES': '127.0.0.1/32', 'CHATIDY_HOST': '0.0.0.0',
}


class RuntimeConfigTests(unittest.TestCase):
    def test_listener_fails_closed_for_local_global_and_invalid_proxy_configuration(self):
        self.assertEqual(listener({}), ('127.0.0.1', 8877))
        self.assertEqual(listener(CONFIG), ('0.0.0.0', 8877))
        for change in ({'CHATIDY_AUTH_REQUIRED': '0'}, {'CHATIDY_TRUSTED_PROXIES': ''},
                       {'CHATIDY_TRUSTED_PROXIES': '0.0.0.0/0'},
                       {'CHATIDY_TRUSTED_PROXIES': '::/0'},
                       {'CHATIDY_TRUSTED_PROXIES': 'not-an-ip'},
                       {'CHATIDY_PUBLIC_ORIGIN': 'https://app.example.invalid/extra'},
                       {'CHATIDY_PUBLIC_ORIGIN': 'https://u:p@app.example.invalid'},
                       {'CHATIDY_PUBLIC_ORIGIN': 'https://app.example.invalid?secret=value'},
                       {'CHATIDY_PUBLIC_ORIGIN': 'https://app.example.invalid:99999'},
                       {'CHATIDY_PORT': '0'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                listener(dict(CONFIG, **change))

    def test_cli_startup_failure_is_nonzero_and_does_not_echo_secret(self):
        import subprocess
        import sys
        environment = dict(os.environ, CHATIDY_AUTH_REQUIRED='0',
                           CHATIDY_PUBLIC_ORIGIN='', CHATIDY_PORT='synthetic-sensitive-invalid-port',
                           CHATIDY_OIDC_CLIENT_SECRET='synthetic-sensitive-startup-secret')
        result = subprocess.run([sys.executable, '-m', 'chatidy'], env=environment,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn('Start fehlgeschlagen', result.stderr)
        self.assertNotIn('synthetic-sensitive', result.stderr + result.stdout)
        self.assertNotIn('Traceback', result.stderr)

    def test_proxy_identity_comes_from_immediate_peer_not_xff(self):
        headers = Message()
        headers['X-Forwarded-Proto'] = 'https'
        headers['X-Forwarded-Host'] = 'app.example.invalid'
        headers['X-Forwarded-For'] = '127.0.0.1'
        self.assertFalse(proxy_request_allowed(headers, '192.0.2.10', CONFIG))
        self.assertTrue(proxy_request_allowed(headers, '127.0.0.1', CONFIG))
        self.assertFalse(proxy_request_allowed(headers, '127.0.0.1', {}))


@unittest.skipUnless(AUTH, 'Optional OIDC dependencies not installed')
class RuntimeAuthConfigTests(unittest.TestCase):
    def test_secret_file_and_neutral_endpoints(self):
        from chatidy.oidc_exchange import configured_settings
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic-secret'
            path.write_text('synthetic-only-file-secret\n')
            env = dict(CONFIG, CHATIDY_OIDC_CLIENT_SECRET='', CHATIDY_OIDC_CLIENT_SECRET_FILE=str(path))
            settings = configured_settings(env)
            self.assertEqual(settings.client_secret, 'synthetic-only-file-secret')
            self.assertNotIn(settings.client_secret, repr(settings))
            for change in ({'CHATIDY_OIDC_CLIENT_SECRET': 'ambiguous'},
                           {'CHATIDY_OIDC_CLIENT_SECRET_FILE': str(path / 'missing')},
                           {'CHATIDY_OIDC_END_SESSION': 'https://elsewhere.invalid/logout'}):
                with self.subTest(change=change), self.assertRaises(ValueError):
                    configured_settings(dict(env, **change))
            path.write_bytes(b'x' * 8193)
            with self.assertRaises(ValueError):
                configured_settings(env)

    def test_auth_startup_initializes_registry_before_accepting_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'registry.sqlite3'
            with patch.dict(os.environ, dict(CONFIG, CHATIDY_DB=str(database))), patch('chatidy.server.ThreadingHTTPServer') as http:
                main()
                http.assert_called_once_with(('0.0.0.0', 8877), Handler)
                http.return_value.server_close.assert_called_once()
            with closing(connect(database)) as db:
                self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 8)
                self.assertEqual(db.execute('SELECT count(*) FROM users').fetchone()[0], 0)


class ProxyHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.registry = Path(self.temp.name) / 'registry.sqlite3'
        self.env = patch.dict(os.environ, dict(CONFIG, CHATIDY_DB=str(self.registry)))
        self.env.start()
        with closing(connect(self.registry)) as db:
            with db:
                db.execute('INSERT INTO users(oidc_issuer,oidc_sub) VALUES(?,?)',
                           (CONFIG['CHATIDY_OIDC_ISSUER'], 'synthetic-account'))
            user = enrolled_user(db, CONFIG['CHATIDY_OIDC_ISSUER'], 'synthetic-account')
            self.token = issue_session(db, user)
        self.http = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.http.shutdown()
        self.thread.join(timeout=5)
        self.http.server_close()
        self.env.stop()
        self.temp.cleanup()

    def request(self, path, *, method='GET', changes=None, duplicates=(), token=None):
        headers = {'Host': 'app.example.invalid', 'X-Forwarded-Proto': 'https',
                   'X-Forwarded-Host': 'app.example.invalid'}
        if method == 'POST': headers['Origin'] = CONFIG['CHATIDY_PUBLIC_ORIGIN']
        if token: headers['Cookie'] = '__Host-chatidy_session=' + token
        for name, value in (changes or {}).items():
            if value is None: headers.pop(name, None)
            else: headers[name] = value
        client = http.client.HTTPConnection(*self.http.server_address, timeout=5)
        try:
            client.putrequest(method, path, skip_host=True)
            for name, value in [*headers.items(), *duplicates]: client.putheader(name, value)
            client.endheaders()
            response = client.getresponse()
            return response.status, response.read(), dict(response.getheaders())
        finally:
            client.close()

    def test_valid_proxy_still_requires_session_for_all_private_resources(self):
        for path in ('/api/stats', '/api/chats', '/api/import/jobs', '/app.js', '/reading.js'):
            self.assertEqual(self.request(path)[0], 401)
        self.assertEqual(self.request('/app')[0], 302)
        self.assertEqual(self.request('/api/stats', token=self.token)[0], 200)
        self.assertEqual(self.request('/api/export', method='POST')[0], 401)

    def test_forged_missing_ambiguous_or_wrong_headers_are_rejected_even_with_session(self):
        for changes in ({'X-Forwarded-Proto': None}, {'X-Forwarded-Host': None},
                        {'X-Forwarded-Proto': 'http'}, {'X-Forwarded-Proto': 'https,http'},
                        {'X-Forwarded-Host': 'evil.invalid'}, {'Host': 'evil.invalid'},
                        {'Forwarded': 'proto=https;host=app.example.invalid'},
                        {'X-Forwarded-Port': '443'}):
            with self.subTest(changes=changes):
                self.assertEqual(self.request('/api/stats', changes=changes, token=self.token)[0], 403)
        for name, value in [('Host', 'evil.invalid'), ('Origin', 'https://evil.invalid'),
                            ('X-Forwarded-Proto', 'https'), ('X-Forwarded-Host', 'app.example.invalid')]:
            self.assertEqual(self.request('/api/stats', duplicates=[(name, value)],
                changes={'Origin': CONFIG['CHATIDY_PUBLIC_ORIGIN']}, token=self.token)[0], 403)
        for origin in (None, 'https://evil.invalid', 'null'):
            self.assertEqual(self.request('/api/export', method='POST', changes={'Origin': origin}, token=self.token)[0], 403)
        with patch.dict(os.environ, CHATIDY_TRUSTED_PROXIES='192.0.2.10/32'):
            self.assertEqual(self.request('/api/stats', token=self.token,
                changes={'X-Forwarded-For': '192.0.2.10'})[0], 403)

    def test_expired_session_denied_over_proxy(self):
        with closing(connect(self.registry)) as db, db:
            db.execute('UPDATE auth_sessions SET expires_at=0')
        self.assertEqual(self.request('/api/stats', token=self.token)[0], 401)

    def test_local_health_never_exposes_data_or_requires_idp_and_rejects_public_host(self):
        self.assertEqual(self.request('/healthz')[0], 403)
        changes = {'Host': f'127.0.0.1:{self.http.server_address[1]}',
                   'X-Forwarded-Host': None, 'X-Forwarded-Proto': None}
        status, body, _ = self.request('/healthz', changes=changes)
        self.assertEqual((status, json.loads(body)), (200, {'status': 'ok'}))
        self.assertEqual(self.request('/healthz', changes=dict(changes, Forwarded='proto=https'))[0], 403)

    def test_fetch_logout_returns_fixed_navigation_and_clears_cookie(self):
        status, body, headers = self.request('/logout', method='POST', token=self.token,
                                             changes={'Accept': 'application/json'})
        self.assertEqual(status, 200)
        target = json.loads(body)['redirect']
        if AUTH:
            self.assertTrue(target.startswith(CONFIG['CHATIDY_OIDC_END_SESSION'] + '?'))
        else:
            self.assertEqual(target, '/')
        self.assertIn('Max-Age=0', headers['Set-Cookie'])
        self.assertEqual(self.request('/api/stats', token=self.token)[0], 401)

    @unittest.skipUnless(AUTH, 'Optional OIDC dependencies not installed')
    def test_logout_revokes_locally_before_fixed_provider_redirect_without_tokens(self):
        status, _, headers = self.request('/logout', method='POST', token=self.token)
        self.assertEqual(status, 302)
        from urllib.parse import urlsplit, parse_qs
        url = urlsplit(headers['Location'])
        self.assertEqual(url.hostname, 'idp.example.invalid')
        self.assertEqual(parse_qs(url.query), {'client_id': ['synthetic-client'],
                          'post_logout_redirect_uri': ['https://app.example.invalid/']})
        self.assertNotIn(self.token, headers['Location'])
        with closing(connect(self.registry)) as db:
            self.assertIsNone(session_user(db, self.token))
        self.assertEqual(self.request('/api/stats', token=self.token)[0], 401)


@unittest.skipUnless(importlib.util.find_spec('cryptography'), 'Optional TLS fixture dependency not installed')
class HTTPSProxyTests(unittest.TestCase):
    def test_verified_tls_proxy_keeps_auth_and_origin_checks(self):
        # A real local TLS hop using a synthetic CA/certificate, never verify=False.
        import datetime
        import ssl
        import ipaddress
        from http.server import BaseHTTPRequestHandler
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')])
            now = datetime.datetime.now(datetime.timezone.utc)
            certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
                .public_key(key.public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(now - datetime.timedelta(minutes=1))
                .not_valid_after(now + datetime.timedelta(hours=1))
                .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'),
                    x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), critical=False)
                .sign(key, hashes.SHA256()))
            cert_path, key_path = root / 'synthetic-cert.pem', root / 'synthetic-key.pem'
            cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
            key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
            database = root / 'registry.sqlite3'
            with patch.dict(os.environ, dict(CONFIG, CHATIDY_DB=str(database))):
                with closing(connect(database)) as db:
                    with db:
                        db.execute('INSERT INTO users(oidc_issuer,oidc_sub) VALUES(?,?)',
                                   (CONFIG['CHATIDY_OIDC_ISSUER'], 'synthetic-tls'))
                    token = issue_session(db, enrolled_user(db, CONFIG['CHATIDY_OIDC_ISSUER'], 'synthetic-tls'))
                backend = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
                class Proxy(BaseHTTPRequestHandler):
                    def do_GET(self):
                        connection = http.client.HTTPConnection(*backend.server_address, timeout=5)
                        headers = {'Host': 'app.example.invalid', 'X-Forwarded-Proto': 'https',
                                   'X-Forwarded-Host': 'app.example.invalid'}
                        for field in ('Cookie', 'Origin'):
                            if self.headers.get(field): headers[field] = self.headers[field]
                        try:
                            connection.request('GET', self.path, headers=headers)
                            response = connection.getresponse()
                            body = response.read()
                            self.send_response(response.status)
                            self.send_header('Content-Length', str(len(body)))
                            self.end_headers()
                            self.wfile.write(body)
                        finally:
                            connection.close()
                    def log_message(self, *args): pass
                proxy = ThreadingHTTPServer(('127.0.0.1', 0), Proxy)
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.load_cert_chain(cert_path, key_path)
                proxy.socket = context.wrap_socket(proxy.socket, server_side=True)
                threads = [threading.Thread(target=s.serve_forever, daemon=True) for s in (backend, proxy)]
                for thread in threads: thread.start()
                try:
                    verified_context = ssl.create_default_context(cafile=str(cert_path))
                    for headers, expected in [({}, 401),
                        ({'Cookie': '__Host-chatidy_session=' + token}, 200),
                        ({'Cookie': '__Host-chatidy_session=' + token, 'Origin': 'https://evil.invalid'}, 403)]:
                        connection = http.client.HTTPSConnection(*proxy.server_address, context=verified_context, timeout=5)
                        try:
                            connection.request('GET', '/api/stats', headers=headers)
                            response = connection.getresponse()
                            self.assertEqual(response.status, expected)
                            response.read()
                        finally:
                            connection.close()
                finally:
                    for server in (proxy, backend): server.shutdown(); server.server_close()
                    for thread in threads: thread.join(timeout=5)
