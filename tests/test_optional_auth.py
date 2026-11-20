"""Local-only Chatidy can import its HTTP handler without optional PyJWT."""
import builtins
import importlib
import unittest
from unittest.mock import patch

class OptionalAuthTests(unittest.TestCase):
    def test_server_does_not_eagerly_import_oidc_crypto(self):
        # This import is safe even without PyJWT installed. The server itself
        # must never import OIDC's cryptography on the regular local path.
        from chatidy import server
        self.assertNotIn("chatidy.oidc", server.__dict__)
        self.assertTrue(hasattr(server.Handler, "do_GET"))
        self.assertTrue(hasattr(server.Handler, "do_POST"))

if __name__=="__main__":unittest.main()
