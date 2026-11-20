"""AUTH-006: deny-by-default HTTP route classification before OIDC wiring."""
import unittest
from chatidy.access_policy import private_route, public_route, is_allowed_without_login


class AuthRoutePolicyTests(unittest.TestCase):
    def test_existing_library_and_api_routes_are_private(self):
        for url in ("/app", "/app/", "/app/import", "/api", "/api/stats",
                    "/api/chats?q=private", "/api/chat/synthetic-id",
                    "/api/folders", "/api/tags", "/api/smart-folders",
                    "/api/rules", "/api/topics", "/api/suggestions",
                    "/api/ai/suggest", "/api/export",
                    "/api/import", "/api/import/analyze",
                    "/api/import/jobs", "/api/import/jobs/abc/confirm",
                    "/api/import/jobs/abc/resume", "/api/import/jobs/abc/delete",
                    "/api/bulk/tags", "/api/bulk/assign", "/api/review",
                    "/api/assign", "/api/folders/update", "/api/rules/delete",
                    "/api%2Fchat%2Ftest", "/app%2Fimport"):
            with self.subTest(url=url):
                self.assertTrue(private_route(url))
                self.assertFalse(is_allowed_without_login(url))

    def test_only_named_public_routes_are_public(self):
        for url in ("/", "/landing.css", "/login", "/auth/callback?code=synthetic"):
            with self.subTest(url=url):
                self.assertTrue(public_route(url))
                self.assertTrue(is_allowed_without_login(url))
        for url in ("/style.css", "/reading.js", "/app.js", "/admin",
                    "/unknown", "/api-public", "/auth/logout", "/profile"):
            with self.subTest(url=url):
                self.assertFalse(is_allowed_without_login(url))

    def test_invalid_url_type_is_rejected(self):
        for url in (None, 42, [], {}):
            with self.assertRaises(ValueError):
                is_allowed_without_login(url)


if __name__ == "__main__":
    unittest.main()
