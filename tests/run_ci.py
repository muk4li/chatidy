"""Run the full suite and expose synthetic failure traces as CI annotations.

The exit code and test outcomes are unchanged. This also makes failures
inspectable on the public Actions page when raw logs require a GitHub login.
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
suite = unittest.defaultTestLoader.discover('tests')
result = unittest.TextTestRunner(verbosity=2).run(suite)
if os.getenv('GITHUB_ACTIONS') == 'true':
    def escape(value):
        return value.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    for test, detail in result.errors + result.failures:
        print('::error::'+escape(str(test)+'\n'+detail[-5000:]), flush=True)
sys.exit(0 if result.wasSuccessful() else 1)
