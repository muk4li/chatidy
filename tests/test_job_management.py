"""Only synthetic files: lifecycle, real process locks and confined deletion."""
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
from chatidy.server import Handler
from pathlib import Path
from unittest.mock import patch
from chatidy import jobs, job_storage
from chatidy.db import connect, list_chats, stats


def payload(cid='synthetic-job'):
    return json.dumps({'id': cid, 'messages': [{'role': 'user', 'content': 'Synthetic SQLite content'}]}).encode()


class JobManagementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)
        self.db_path = self.path / 'synthetic.sqlite3'
        self.env = patch.dict(os.environ, CHATIDY_DB=str(self.db_path))
        self.env.start()
        connect(self.db_path).close()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def create(self, cid='synthetic-job', body=None):
        data = payload(cid) if body is None else body
        return jobs.create(io.BytesIO(data), len(data), 'synthetic.json')

    def test_done_cleanup_preserves_database_source_and_fts(self):
        original = self.path / 'original.json'
        original.write_bytes(payload())
        with original.open('rb') as source:
            job = jobs.create(source, original.stat().st_size, original.name)
        jobs.run(job)
        info = jobs.public_status(job)
        self.assertEqual(info['state'], 'done')
        self.assertGreater(info['storage_bytes'], 0)
        self.assertGreater(info['created'], 0)
        self.assertFalse(info['can_resume'])
        self.assertTrue(info['can_delete'])
        self.assertEqual(jobs.listing()['count'], 1)
        self.assertEqual(jobs.listing()['storage_bytes'], info['storage_bytes'])
        for confirmation in (False, None, 'true', 1):
            with self.assertRaisesRegex(ValueError, 'bestätigt'):
                jobs.delete(job, confirmation)
        self.assertTrue(jobs.job_path(job).exists())
        jobs.delete(job, confirmed=True)
        self.assertEqual(jobs.listing()['count'], 0)
        self.assertEqual(original.read_bytes(), payload())
        self.assertTrue(self.db_path.exists())
        db = connect(self.db_path)
        try:
            self.assertEqual(len(list_chats(db, 'SQLite')), 1)
            self.assertEqual(stats(db)['messages'], 1)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
        finally:
            db.close()

    def test_failed_and_uploaded_jobs_require_explicit_delete(self):
        for body in (b'not json', payload()):
            job = self.create(body=body)
            if body == b'not json':
                jobs.run(job)
                self.assertEqual(jobs.status(job)['state'], 'error')
            self.assertTrue(jobs.public_status(job)['can_resume'])
            with self.assertRaises(ValueError):
                jobs.delete(job)
            jobs.delete(job, confirmed=True)
        self.assertEqual(jobs.listing()['count'], 0)

    def test_real_process_termination_releases_lease_and_resume_is_atomic(self):
        job = self.create()
        code = '''import sys,time
from chatidy import jobs
original=jobs.iter_export
def paused(*args):
    print('VALIDATING',flush=True)
    time.sleep(60)
    yield from original(*args)
jobs.iter_export=paused
jobs.run(sys.argv[1])
'''
        child = subprocess.Popen([sys.executable, '-c', code, job], stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), 'VALIDATING')
            info = jobs.public_status(job)
            self.assertTrue(info['active'])
            self.assertEqual(info['state'], 'validating')
            self.assertFalse(info['can_delete'])
            with self.assertRaisesRegex(ValueError, 'Aktiver'):
                jobs.delete(job, confirmed=True)
            child.kill()
            child.wait(timeout=5)
            info = jobs.public_status(job)
            self.assertEqual(info['state'], 'interrupted')
            self.assertTrue(info['can_resume'])
            with self.assertRaises(ValueError):
                jobs.delete(job)
            jobs.run(job)
            self.assertEqual(jobs.status(job)['state'], 'done')
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)
            child.stdout.close()

    def test_parallel_jobs_and_duplicate_start(self):
        first, second = self.create('synthetic-one'), self.create('synthetic-two')
        ready = threading.Barrier(3)
        release = threading.Event()
        original = jobs.iter_export
        def paused(*args):
            ready.wait(timeout=5)
            if not release.wait(timeout=5):
                raise RuntimeError('Synthetic timeout')
            yield from original(*args)
        with patch('chatidy.jobs.iter_export', paused):
            a, b = jobs.start(first), jobs.start(second)
            try:
                ready.wait(timeout=5)
                self.assertIsNone(jobs.start(first))
                self.assertTrue(all(item['active'] for item in jobs.listing()['jobs']))
                with self.assertRaisesRegex(ValueError, 'Aktiver'):
                    jobs.delete(first, confirmed=True)
            finally:
                release.set()
                a.join(timeout=5)
                b.join(timeout=5)
        self.assertFalse(a.is_alive())
        self.assertFalse(b.is_alive())
        self.assertEqual(jobs.status(first)['state'], 'done')
        self.assertEqual(jobs.status(second)['state'], 'done')
        db = connect(self.db_path)
        self.assertEqual(len(list_chats(db, 'SQLite')), 2)
        db.close()

    def test_invalid_ids_never_touch_outside_files(self):
        sentinel = self.path / 'sentinel.txt'
        sentinel.write_text('Synthetic sentinel')
        for job in ('../sentinel.txt', '/tmp', '', 'A'*32, None, ['invalid']):
            with self.subTest(job=job):
                for action in (jobs.status, jobs.run, lambda value: jobs.delete(value, confirmed=True)):
                    with self.assertRaises(ValueError):
                        action(job)
        self.assertEqual(sentinel.read_text(), 'Synthetic sentinel')

    def test_unknown_files_and_subdirectories_block_all_deletion(self):
        for name, directory in (('unrelated.txt', False), ('foreign-directory', True)):
            job = self.create()
            foreign = jobs.job_path(job) / name
            foreign.mkdir() if directory else foreign.write_text('Synthetic foreign file')
            before = (jobs.job_path(job) / 'source.json').read_bytes()
            with self.assertRaisesRegex(ValueError, 'Unbekannte Datei'):
                jobs.delete(job, confirmed=True)
            self.assertEqual((jobs.job_path(job) / 'source.json').read_bytes(), before)
            self.assertTrue(foreign.exists())
            self.assertEqual(jobs.listing()['jobs'][0]['state'], 'blocked')
            foreign.rmdir() if directory else foreign.unlink()
            jobs.delete(job, confirmed=True)

    def test_file_symlink_hardlink_job_symlink_and_root_symlink_are_rejected(self):
        outside = self.path / 'outside.txt'
        outside.write_text('Synthetic outside file')
        job = self.create()
        source = jobs.job_path(job) / 'source.json'
        source.unlink()
        for hard in (False, True):
            if hard:
                os.link(outside, source)
            else:
                source.symlink_to(outside)
            with self.assertRaises(ValueError):
                jobs.delete(job, confirmed=True)
            with self.assertRaises(ValueError):
                jobs.run(job)
            self.assertEqual(jobs.listing()['jobs'][0]['state'], 'blocked')
            self.assertEqual(outside.read_text(), 'Synthetic outside file')
            source.unlink()
        source.write_bytes(payload())
        jobs.delete(job, confirmed=True)
        root = job_storage.root_path()
        fake_id = 'a'*32
        (root / fake_id).symlink_to(self.path, target_is_directory=True)
        with self.assertRaises(ValueError):
            jobs.delete(fake_id, confirmed=True)
        (root / fake_id).unlink()
        renamed = self.path / 'real-job-root'
        root.rename(renamed)
        root.symlink_to(renamed, target_is_directory=True)
        with self.assertRaises(ValueError):
            jobs.listing()
        with self.assertRaises(ValueError):
            self.create()
        self.assertEqual(outside.read_text(), 'Synthetic outside file')

    def test_symlinked_parent_is_not_resolved_implicitly(self):
        real = self.path / 'real'
        real.mkdir()
        alias = self.path / 'alias'
        alias.symlink_to(real, target_is_directory=True)
        with patch.dict(os.environ, CHATIDY_DB=str(alias / 'custom.db')):
            with self.assertRaises(ValueError):
                self.create()
        self.assertEqual(list(real.iterdir()), [])

    def test_interrupted_cleanup_is_visible_and_retryable_only_with_confirmation(self):
        job = self.create()
        jobs.run(job)
        unlink = os.unlink
        calls = []
        def interrupted(name, **kwargs):
            calls.append(name)
            if len(calls) == 2:
                raise OSError('Synthetic cleanup interruption')
            return unlink(name, **kwargs)
        with patch('chatidy.jobs.os.unlink', interrupted), self.assertRaises(ValueError):
            jobs.delete(job, confirmed=True)
        info = jobs.public_status(job)
        self.assertEqual(info['state'], 'cleanup_pending')
        self.assertFalse(info['can_resume'])
        self.assertTrue(info['can_delete'])
        self.assertEqual(jobs.listing()['count'], 1)
        with self.assertRaises(ValueError):
            jobs.delete(job)
        with self.assertRaisesRegex(ValueError, 'Bereinigung'):
            jobs.run(job)
        jobs.delete(job, confirmed=True)
        self.assertEqual(jobs.listing()['count'], 0)
        self.assertTrue(self.db_path.exists())

    def test_corrupt_status_can_only_be_cleaned_after_confirmation(self):
        job = self.create()
        (jobs.job_path(job)/'status.json').write_text('not JSON')
        info = jobs.public_status(job)
        self.assertEqual(info['state'], 'error')
        self.assertFalse(info['can_resume'])
        self.assertTrue(info['can_delete'])
        with self.assertRaises(ValueError):
            jobs.delete(job)
        jobs.delete(job, confirmed=True)
        self.assertEqual(jobs.listing()['count'], 0)

    def test_unsupported_locking_fails_closed(self):
        job = self.create()
        with patch('chatidy.job_storage.fcntl', None):
            with self.assertRaisesRegex(ValueError, 'POSIX'):
                jobs.delete(job, confirmed=True)
        self.assertTrue((jobs.job_path(job)/'source.json').exists())

    def test_world_writable_custom_parent_is_rejected(self):
        unsafe = self.path/'unsafe'
        unsafe.mkdir(mode=0o777)
        unsafe.chmod(0o777)
        with patch.dict(os.environ, CHATIDY_DB=str(unsafe/'synthetic.db')):
            with self.assertRaisesRegex(ValueError, 'übergeordnetes'):
                self.create()

    def test_http_management_requires_confirmation_and_preserves_imported_chats(self):
        job = self.create()
        jobs.run(job)
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        port = server.server_address[1]
        with patch.dict(os.environ, CHATIDY_PORT=str(port)):
            thread.start()
            try:
                def request(path, body=None):
                    req = urllib.request.Request(f'http://127.0.0.1:{port}'+path,
                        data=json.dumps(body).encode() if body is not None else None)
                    with urllib.request.urlopen(req, timeout=5) as response:
                        return json.load(response)
                self.assertEqual(request('/api/import/jobs')['count'], 1)
                for body in ({}, {'confirm': False}, {'confirm': 'true'}):
                    with self.assertRaises(urllib.error.HTTPError) as caught:
                        request('/api/import/jobs/'+job+'/delete', body)
                    self.assertEqual(caught.exception.code, 400)
                    caught.exception.close()
                request('/api/import/jobs/'+job+'/delete', {'confirm': True})
                self.assertEqual(request('/api/import/jobs')['count'], 0)
                self.assertEqual(request('/api/stats')['messages'], 1)
                self.assertEqual(len(request('/api/chats?q=SQLite')), 1)
            finally:
                server.shutdown()
                thread.join(timeout=5)
                server.server_close()

    def test_symlinked_control_and_sqlite_files_block_all_mutation(self):
        sentinel = self.path / 'outside-secret.txt'
        sentinel.write_text('Synthetic protected data')
        for name in ('status.json', 'status.tmp', 'staging.sqlite3', 'staging.sqlite3-wal', 'job.lock'):
            with self.subTest(name=name):
                job = self.create()
                target = jobs.job_path(job)/name
                old = target.read_bytes() if target.exists() else None
                target.unlink(missing_ok=True)
                target.symlink_to(sentinel)
                with self.assertRaises(ValueError):
                    jobs.delete(job, confirmed=True)
                self.assertEqual(sentinel.read_text(), 'Synthetic protected data')
                self.assertTrue((jobs.job_path(job)/'source.json').exists())
                self.assertEqual(jobs.listing()['jobs'][0]['state'], 'blocked')
                target.unlink()
                if old is not None:
                    target.write_bytes(old)
                jobs.delete(job, confirmed=True)

    def test_resume_after_main_commit_before_status_write_is_idempotent(self):
        job = self.create()
        code = """import sys,time
from chatidy import jobs
original=jobs.upsert
def paused(*args):
    count=original(*args)
    print('COMMITTED',flush=True)
    time.sleep(60)
    return count
jobs.upsert=paused
jobs.run(sys.argv[1])
"""
        child = subprocess.Popen([sys.executable, '-c', code, job], stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), 'COMMITTED')
            self.assertEqual(jobs.public_status(job)['state'], 'committing')
            child.kill()
            child.wait(timeout=5)
            self.assertEqual(jobs.public_status(job)['state'], 'interrupted')
            jobs.run(job)
            self.assertEqual(jobs.public_status(job)['state'], 'done')
            db = connect(self.db_path)
            self.assertEqual(stats(db)['messages'], 1)
            self.assertEqual(len(list_chats(db, 'SQLite')), 1)
            db.close()
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)
            child.stdout.close()

    def test_main_database_cannot_be_deleted_even_if_relocated_into_job(self):
        job = self.create()
        source = jobs.job_path(job) / 'source.json'
        source.unlink()
        self.db_path.rename(source)
        self.db_path.symlink_to(source)
        with self.assertRaisesRegex(ValueError, 'Chatidy-Datenbank'):
            jobs.delete(job, confirmed=True)
        self.assertTrue(source.exists())

    def test_directory_swap_to_symlink_does_not_follow_outside_target(self):
        job = self.create()
        source = jobs.job_path(job) / 'source.json'
        outside = self.path / 'outside'
        outside.mkdir()
        (outside/'sentinel.txt').write_text('Synthetic sentinel')
        rename = os.rename
        def swap(*args, **kwargs):
            # Replace the public path with a symlink immediately after the pinned
            # directory is renamed. Deletion must still use the pinned directory.
            result = rename(*args, **kwargs)
            source.parent.symlink_to(outside, target_is_directory=True)
            return result
        with patch('chatidy.jobs.os.rename', swap):
            jobs.delete(job, confirmed=True)
        self.assertEqual((outside/'sentinel.txt').read_text(), 'Synthetic sentinel')
        self.assertTrue(source.parent.is_symlink())
