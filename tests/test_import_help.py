"""UX-002: importing from multiple providers is explained without changing import code."""
import unittest
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.text = []
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
    def handle_data(self, data):
        self.text.append(data)

class ImportHelpTests(unittest.TestCase):
    def test_import_help_is_in_existing_application(self):
        source = (ROOT / 'web/index.html').read_text(encoding='utf-8')
        parsed = Elements()
        parsed.feed(source)
        text = ' '.join(parsed.text)
        self.assertIn('KI-Gespräche importieren', text)
        self.assertIn('Welchen Export kann ich auswählen?', text)
        self.assertIn('ChatGPT:', text)
        self.assertIn('Claude:', text)
        self.assertIn('Extractor:', text)
        self.assertIn('conversations-000.zip', text)
        self.assertIn('Codex-Aufgaben', text)
        self.assertTrue(any(tag == 'details' and attrs.get('class') == 'format-help'
                            for tag, attrs in parsed.tags))
        self.assertTrue(any(tag == 'input' and attrs.get('id') == 'file-input'
                            for tag, attrs in parsed.tags))
        self.assertTrue(any(tag == 'section' and attrs.get('id') == 'import-preview'
                            for tag, attrs in parsed.tags))
        self.assertTrue(any(tag == 'button' and attrs.get('id') == 'pick-file'
                            for tag, attrs in parsed.tags))

if __name__ == '__main__':
    unittest.main()
