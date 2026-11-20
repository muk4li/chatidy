"""Landingpage is static, and the existing local app stays available separately."""
import unittest
from chatidy.server import STATIC

class LandingRoutingTests(unittest.TestCase):
    def test_public_page_and_local_app_have_distinct_routes(self):
        self.assertEqual(STATIC['/'][0], 'web/landing.html')
        self.assertEqual(STATIC['/app'][0], 'web/index.html')
        self.assertEqual(STATIC['/landing.css'][0], 'web/landing.css')
        self.assertEqual(STATIC['/app.js'][0], 'web/app.js')

    def test_landing_does_not_load_library_code_or_external_resources(self):
        from chatidy.server import ROOT
        html = (ROOT / 'web/landing.html').read_text(encoding='utf-8')
        self.assertIn('href="/app"', html)
        self.assertIn('href="/landing.css"', html)
        self.assertNotIn('src="/app.js"', html)
        self.assertNotIn('src="https://', html)
        self.assertNotIn('href="https://fonts.', html)
        self.assertNotIn('Anmelden', html)

if __name__ == '__main__':
    unittest.main()
