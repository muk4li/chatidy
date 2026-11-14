"""Synthetic regression coverage for first-run defaults and start configuration."""
import os
from contextlib import closing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from chatidy import db, jobs, server
from chatidy import job_storage
from chatidy.db import assign, create_folder, create_rule, upsert


class DefaultsTests(unittest.TestCase):
    def test_new_database_has_chat_categories(self):
        with tempfile.TemporaryDirectory() as directory:
            with closing(db.connect(Path(directory) / 'library.sqlite3')) as connection:
                self.assertEqual(
                    [tuple(row) for row in connection.execute('SELECT name,parent_id FROM folders ORDER BY id')],
                    [(name, None) for name in ['Programmieren', 'Infrastruktur & DevOps',
                     'Lernen', 'Schreiben & Texte', 'Recherche', 'Projekte', 'Persönliches', 'Favoriten']])

    def test_existing_folders_memberships_rules_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'library.sqlite3'
            with closing(db.connect(path)) as connection:
                # Reproduce the previous root/child layout, including an old category.
                connection.execute('DELETE FROM folders')
                connection.commit()
                root = create_folder(connection, 'Wissen')
                old = create_folder(connection, 'Anime', root)
                custom = create_folder(connection, 'Eigener Ordner')
                upsert(connection, [{'id': 'synthetic-chat', 'title': 'Synthetic',
                                     'messages': [{'id': 'm', 'role': 'user', 'content': 'synthetic'}]}])
                assign(connection, 'synthetic-chat', [old, custom])
                create_rule(connection, 'title', 'Synthetic', old)
                tables = ('folders', 'memberships', 'rules')
                before = {table: [tuple(row) for row in connection.execute(f'SELECT * FROM {table} ORDER BY rowid')]
                          for table in tables}
            with closing(db.connect(path)) as connection:
                after = {table: [tuple(row) for row in connection.execute(f'SELECT * FROM {table} ORDER BY rowid')]
                         for table in tables}
                self.assertEqual(after, before)

    def test_existing_empty_folder_table_stays_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'library.sqlite3'
            with closing(db.connect(path)) as connection:
                connection.execute('DELETE FROM folders')
                connection.commit()
            with closing(db.connect(path)) as connection:
                self.assertEqual(connection.execute('SELECT COUNT(*) FROM folders').fetchone()[0], 0)

    def test_default_database_is_project_relative_from_other_cwd(self):
        expected = Path(db.__file__).resolve().parent.parent / 'data' / 'chatidy.sqlite3'
        self.assertEqual(db.DEFAULT_DATABASE, expected)
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ):
            os.environ.pop('CHATIDY_DB', None)
            previous = Path.cwd()
            try:
                os.chdir(directory)
                # Inspect the actual selected filename without writing into the checkout.
                with patch.object(db.sqlite3, 'connect', side_effect=RuntimeError('filename inspected')) as connect:
                    with patch.object(Path, 'mkdir'):
                        with self.assertRaisesRegex(RuntimeError, 'filename inspected'):
                            db.connect()
                    self.assertEqual(connect.call_args.args[0], expected)
            finally:
                os.chdir(previous)

    def test_environment_and_explicit_path_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            configured = Path(directory) / 'configured.sqlite3'
            explicit = Path(directory) / 'explicit.sqlite3'
            with patch.dict(os.environ, CHATIDY_DB=str(configured)):
                with closing(db.connect()) as connection:
                    self.assertEqual(Path(connection.execute('PRAGMA database_list').fetchone()[2]), configured)
                with closing(db.connect(explicit)) as connection:
                    self.assertEqual(Path(connection.execute('PRAGMA database_list').fetchone()[2]), explicit)

    def test_server_start_shares_default_with_existing_jobs(self):
        with patch.dict(os.environ), patch.object(server, 'ThreadingHTTPServer'):
            os.environ.pop('CHATIDY_DB', None)
            server.main()
            self.assertEqual(jobs.database_path(), db.DEFAULT_DATABASE)
            self.assertEqual(job_storage.root_path(), db.DEFAULT_DATABASE.parent / 'import-jobs')

    def test_server_preserves_configured_relative_path(self):
        with patch.dict(os.environ, CHATIDY_DB='custom/library.sqlite3'), patch.object(server, 'ThreadingHTTPServer'):
            server.main()
            self.assertEqual(os.environ['CHATIDY_DB'], 'custom/library.sqlite3')
            self.assertEqual(jobs.database_path(), Path.cwd() / 'custom' / 'library.sqlite3')
