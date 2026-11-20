"""F-001 to F-009 frontend contract (without network access or real data)."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class UXContractTests(unittest.TestCase):
    def test_landing_has_no_fake_preview_and_app_brand_is_a_link(self):
        landing=(ROOT/"web/landing.html").read_text(encoding="utf-8")
        html=(ROOT/"web/index.html").read_text(encoding="utf-8")
        self.assertNotIn('class="preview-section',landing)
        self.assertNotIn('class="fake-row',landing)
        self.assertIn('class="brand" href="/"',html)

    def test_controls_for_multifile_source_date_are_present(self):
        html=(ROOT/"web/index.html").read_text(encoding="utf-8")
        script=(ROOT/"web/app.js").read_text(encoding="utf-8")
        self.assertIn('id="file-input" type="file" accept=".zip,.json" multiple',html)
        for control in ('multi-upload-status','source-list','date-from','date-to','undated','date-sort','clear'):
            self.assertIn('id="'+control+'"',html)
        self.assertIn('XMLHttpRequest',script)
        self.assertIn("const SOURCE_LABELS=",script)
        self.assertIn("addEventListener('popstate',applyRoute)",script)

if __name__=="__main__":unittest.main()
