"""AUTH-015: fail-closed startup for invalid public and OIDC configurations."""
import os
import unittest
from unittest.mock import patch
from chatidy.server import main

class StartupGateTests(unittest.TestCase):
    def test_public_origin_cannot_run_without_auth(self):
        for flag in ("0", "", "false", "1 ", "true"):
            with self.subTest(flag=flag):
                with patch.dict(os.environ,{"CHATIDY_AUTH_REQUIRED":flag,
                          "CHATIDY_PUBLIC_ORIGIN":"https://app.example.invalid"}):
                    with patch("chatidy.server.ThreadingHTTPServer") as server:
                        with self.assertRaises(ValueError):
                            main()
                        server.assert_not_called()

    def test_auth_cannot_start_with_missing_oidc_configuration(self):
        with patch.dict(os.environ,{"CHATIDY_AUTH_REQUIRED":"1",
            "CHATIDY_PUBLIC_ORIGIN":"https://app.example.invalid",
            "CHATIDY_OIDC_ISSUER":""}):
            with patch("chatidy.server.ThreadingHTTPServer") as server:
                with self.assertRaises(ValueError):
                    main()
                server.assert_not_called()

    def test_local_loopback_still_starts_without_auth_or_oidc(self):
        with patch.dict(os.environ,{"CHATIDY_AUTH_REQUIRED":"0",
                                    "CHATIDY_PUBLIC_ORIGIN":""}):
            with patch("chatidy.server.ThreadingHTTPServer") as server:
                main()
                args=server.call_args[0][0]
                self.assertEqual(args[0],"127.0.0.1")
                server.return_value.serve_forever.assert_called_once()

if __name__=="__main__":unittest.main()
