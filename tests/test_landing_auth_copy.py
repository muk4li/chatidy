"""AUTH-016: public copy works in both loopback and authenticated modes."""
import unittest
from pathlib import Path

class LandingCopyTests(unittest.TestCase):
    def test_cta_leads_to_privately_gated_application_without_claiming_live_saas(self):
        content=(Path(__file__).resolve().parents[1]/"web"/"landing.html").read_text(encoding="utf-8")
        self.assertIn('href="/app"',content)
        self.assertIn('Bibliothek öffnen',content)
        self.assertIn("selbst betriebenen Wissensbibliothek",content)
        self.assertIn("Sicherheitsfreigabe",content)
        self.assertNotIn("noch ohne Benutzeranmeldung",content)
        self.assertNotIn("Eine künftige Version mit Anmeldung",content)
        self.assertNotIn("Lokale Bibliothek öffnen",content)
        self.assertIn("erfundenen Beispieldaten",content)

if __name__=="__main__":unittest.main()
