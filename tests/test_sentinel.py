import tempfile
import unittest
from pathlib import Path
from sentinel import audit

BASE = '<!doctype html><html lang="en"><head><title>Test</title><meta name="description" content="A page"></head><body><h1>Test</h1>{}</body></html>'

class SentinelTests(unittest.TestCase):
    def check(self, files, exclude=()):
        with tempfile.TemporaryDirectory() as temp:
            for name, text in files.items():
                path=Path(temp)/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
            return audit(temp, exclude)

    def test_root_links_and_fragments(self):
        result=self.check({'index.html':BASE.format('<a href="/about/#details">About</a>'), 'about/index.html':BASE.format('<p id="details">Detail</p>')})
        self.assertEqual(result['errors'],0)

    def test_missing_files_and_cross_page_anchors(self):
        result=self.check({'index.html':BASE.format('<a href="other.html#missing">Other</a><img src="lost.png" alt="">'), 'other.html':BASE.format('')})
        self.assertEqual({i['code'] for i in result['issues']},{'missing-target','missing-fragment'})

    def test_external_urls_are_not_fetched(self):
        result=self.check({'index.html':BASE.format('<a href="https://example.invalid/">External</a><img alt="" src="data:image/png;base64,AA">')})
        self.assertEqual(result['errors'],0)

    def test_duplicate_ids_and_missing_alt(self):
        result=self.check({'index.html':BASE.format('<p id="x">A</p><p id="x">B</p><img src="x.png">'),'x.png':'data'})
        self.assertEqual({i['code'] for i in result['issues']},{'duplicate-id','missing-alt'})

    def test_percent_encoded_paths_and_queries(self):
        result=self.check({'index.html':BASE.format('<a href="hello%20world.html?preview=1#x%20y">Read</a>'),'hello world.html':BASE.format('<p id="x y">Hello</p>')})
        self.assertEqual(result['errors'],0)

    def test_parent_path_cannot_escape_root(self):
        result=self.check({'index.html':BASE.format('<a href="../outside.html">Outside</a>')})
        self.assertEqual(result['issues'][0]['code'],'outside-root')

    def test_exclusions_and_heading_warning(self):
        result=self.check({'index.html':BASE.format('<h3>Skipped h2</h3>'),'vendor/index.html':'<html>'},['vendor/*'])
        self.assertEqual(result['pages'],1)
        self.assertEqual(result['errors'],0)
        self.assertEqual(result['warnings'],1)

    def test_malformed_url_is_reported(self):
        result=self.check({'index.html':BASE.format('<a href="https://[">Broken URL</a>')})
        self.assertEqual(result['issues'][0]['code'],'invalid-url')

    def test_empty_directory(self):
        self.assertEqual(self.check({})['errors'],1)

if __name__ == '__main__': unittest.main()
