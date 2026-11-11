"""Regression checks for the public repository's local-data ignore policy."""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GitIgnorePrivacyTests(unittest.TestCase):
    def ignored(self, path):
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "--quiet", path],
            cwd=ROOT, check=False, capture_output=True, text=True,
        )
        self.assertIn(result.returncode, (0, 1), result.stderr)
        return result.returncode == 0

    def test_private_runtime_data_are_ignored(self):
        for path in (
            "data/chatidy.sqlite3",
            "import-jobs/synthetic/source.json",
            "data/chatidy.sqlite3-wal",
            "instance/private.db",
            "backups/archive.json",
            "exports/conversations.json",
            "imports/raw.json",
            "attachments/private.png",
            "conversations.json",
            "conversations-2026.json",
            "chatgpt-export-2026.json",
            "personal.zip",
            ".env",
            ".env.local",
            "secret.pem",
            "run.log",
        ):
            with self.subTest(path=path):
                self.assertTrue(self.ignored(path), path)

    def test_public_source_and_safe_templates_are_not_ignored(self):
        for path in (
            "chatidy/importer.py",
            "tests/test_core.py",
            "web/app.js",
            "README.md",
            ".github/workflows/tests.yml",
            ".env.example",
            "tests/fixtures/synthetic.json",
        ):
            with self.subTest(path=path):
                self.assertFalse(self.ignored(path), path)


if __name__ == "__main__":
    unittest.main()
