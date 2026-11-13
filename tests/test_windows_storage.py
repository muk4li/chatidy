"""Real native Windows tests, intentionally not simulated on Linux."""
import io
import json
import os
import sqlite3
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from chatidy import jobs, job_storage
from chatidy.db import connect, list_chats


def junction(link, target):
    # mklink /J is a Windows built-in and requires no symlink privilege.
    # All paths here are generated synthetic fixtures, not API input.
    result = subprocess.run(['cmd', '/d', '/c', 'mklink', '/J', str(link), str(target)],
                            capture_output=True, text=True)
    if result.returncode:
        raise AssertionError('Junction fixture could not be created: '+result.stderr)


@unittest.skipUnless(os.name == 'nt', 'Requires a real Windows host')
class WindowsStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='chatidy-native-')
        self.path = Path(self.temp.name)
        self.database = self.path/'library.sqlite3'
        self.env = patch.dict(os.environ, CHATIDY_DB=str(self.database))
        self.env.start()
        connect(self.database).close()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def create(self):
        body = json.dumps({'id': 'synthetic-windows', 'messages': [
            {'role': 'user', 'content': 'Synthetic SQLite'}]}).encode()
        return jobs.create(io.BytesIO(body), len(body), 'synthetic.json')

    def test_native_byte_locks_and_pinned_directories(self):
        job_id = self.create()
        job, lease = jobs._lease(job_id)
        try:
            self.assertTrue(jobs.public_status(job_id)['active'])
            with self.assertRaises(ValueError):
                jobs.delete(job_id, confirmed=True)
            for path in (jobs.job_path(job_id), job_storage.root_path()):
                with self.assertRaises(OSError):
                    path.rename(path.with_name(path.name+'-moved'))
        finally:
            os.close(lease)
            job.close()
        jobs.run(job_id)
        jobs.delete(job_id, confirmed=True)

    def test_job_and_root_junctions_are_rejected(self):
        job_id = self.create()
        real = jobs.job_path(job_id)
        backup = self.path/'saved-job'
        real.rename(backup)
        outside = self.path/'outside'
        outside.mkdir()
        sentinel = outside/'sentinel.txt'
        sentinel.write_text('Synthetic untouched')
        junction(real, outside)
        try:
            with self.assertRaises(ValueError):
                jobs.delete(job_id, confirmed=True)
            self.assertEqual(jobs.listing()['jobs'][0]['state'], 'blocked')
            self.assertEqual(sentinel.read_text(), 'Synthetic untouched')
        finally:
            os.rmdir(real)  # Remove the junction itself, never its target.
            backup.rename(real)
        jobs.delete(job_id, confirmed=True)
        root = job_storage.root_path()
        saved = self.path/'saved-root'
        root.rename(saved)
        junction(root, saved)
        try:
            with self.assertRaises(ValueError):
                jobs.listing()
            with self.assertRaises(ValueError):
                self.create()
        finally:
            os.rmdir(root)
            saved.rename(root)

    def test_junction_in_database_parent_is_rejected(self):
        target = self.path/'target'
        target.mkdir()
        alias = self.path/'alias'
        junction(alias, target)
        try:
            with patch.dict(os.environ, CHATIDY_DB=str(alias/'library.db')):
                with self.assertRaises(ValueError):
                    self.create()
            self.assertFalse((target/'import-jobs').exists())
        finally:
            os.rmdir(alias)

    def test_hardlinked_source_is_not_removed(self):
        job_id = self.create()
        source = jobs.job_path(job_id)/'source.json'
        outside = self.path/'original.json'
        source.rename(outside)
        os.link(outside, source)
        with self.assertRaises(ValueError):
            jobs.delete(job_id, confirmed=True)
        self.assertTrue(outside.exists())
        self.assertTrue(source.exists())

    def test_file_symlink_is_rejected_when_privilege_available(self):
        job_id = self.create()
        source = jobs.job_path(job_id)/'source.json'
        original = self.path/'outside.json'
        source.rename(original)
        try:
            source.symlink_to(original)
        except OSError as exc:
            if exc.winerror == 1314:
                self.skipTest('Windows runner lacks symbolic-link privilege; junction tests still execute')
            raise
        with self.assertRaises(ValueError):
            jobs.delete(job_id, confirmed=True)
        self.assertTrue(original.exists())

    def test_open_file_prevents_cleanup_until_closed(self):
        from chatidy import windows_handles as win
        job_id = self.create()
        jobs.run(job_id)
        handle = win.open_handle(jobs.job_path(job_id)/'staging.sqlite3', 0x80000000, share=win.SHARE_PIN)
        try:
            with self.assertRaises(ValueError):
                jobs.delete(job_id, confirmed=True)
        finally:
            win.Close(handle)
        self.assertEqual(jobs.public_status(job_id)['state'], 'cleanup_pending')
        jobs.delete(job_id, confirmed=True)
        db = connect(self.database)
        self.assertEqual(len(list_chats(db, 'SQLite')), 1)
        db.close()

    def test_sqlite_wal_handles_are_closed_before_cleanup(self):
        job_id = self.create()
        jobs.run(job_id)
        job, lease = jobs._lease(job_id)
        db = sqlite3.connect(job.sqlite_path())
        try:
            self.assertEqual(db.execute('PRAGMA journal_mode=WAL').fetchone()[0], 'wal')
            db.execute('CREATE TABLE synthetic_probe(value INTEGER)')
            db.execute('INSERT INTO synthetic_probe VALUES(1)')
            db.commit()
            self.assertTrue((jobs.job_path(job_id)/'staging.sqlite3-wal').exists())
            with self.assertRaises(ValueError):
                jobs.delete(job_id, confirmed=True)
        finally:
            db.close()
            os.close(lease)
            job.close()
        jobs.delete(job_id, confirmed=True)
        self.assertTrue(self.database.exists())

    def test_overbroad_file_acl_is_rejected(self):
        job_id = self.create()
        source = jobs.job_path(job_id)/'source.json'
        result = subprocess.run(['icacls', str(source), '/grant', '*S-1-1-0:M'], capture_output=True)
        self.assertEqual(result.returncode, 0)
        with self.assertRaises(ValueError):
            jobs.delete(job_id, confirmed=True)
        self.assertEqual(jobs.listing()['jobs'][0]['state'], 'blocked')
        self.assertTrue(source.exists())

    def test_status_is_readable_during_atomic_replacements(self):
        job_id = self.create()
        job, lease = jobs._lease(job_id)
        value = job.read('status.json')
        failures = []
        def writer():
            try:
                for _ in range(30):
                    job.write('status.json', value)
            except Exception as exc:
                failures.append(exc)
        thread = threading.Thread(target=writer)
        try:
            thread.start()
            for _ in range(30):
                info = jobs.public_status(job_id)
                self.assertEqual(info['state'], 'uploaded')
                self.assertTrue(info['active'])
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
            self.assertEqual(failures, [])
        finally:
            thread.join(timeout=10)
            os.close(lease)
            job.close()

    def test_windows_ids_paths_and_alternate_streams(self):
        from chatidy import windows_handles as win
        for value in ('..\\job', 'C:\\Windows', '\\\\server\\share', 'a'*32+':stream', 'CON'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                jobs.delete(value, confirmed=True)
        for value in ('C:relative', '\\\\server\\share\\jobs', '\\\\?\\C:\\jobs', 'C:\\jobs:stream'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                win.validate_volume(Path(value))
        for configured in ('C:relative.db', str(self.path/'library.db')+':stream'):
            with patch.dict(os.environ, CHATIDY_DB=configured):
                with self.assertRaises(ValueError):
                    job_storage.root_path()
