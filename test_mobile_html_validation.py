import unittest
from mobile.validate_mobile_html import validate_html


class MobileHTMLValidationTests(unittest.TestCase):
    GOOD = '<!doctype html><html><body><div id="garage"></div><script>const x=1;</script></body></html>'

    def test_valid_page(self):
        validate_html(self.GOOD)

    def test_rejects_code_after_page_like_broken_apk(self):
        with self.assertRaises(ValueError):
            validate_html(self.GOOD + 'function renderFuel(){return `${fuel}`;}')

    def test_rejects_duplicate_markup(self):
        with self.assertRaises(ValueError):
            validate_html(self.GOOD.replace('</body>', '<div id="garage"></div></body>'))

    def test_rejects_leaked_template(self):
        with self.assertRaises(ValueError):
            validate_html(self.GOOD.replace('</body>', '<div>${usd(total)}</div></body>'))

    def test_rejects_unmatched_script_closing_tag(self):
        with self.assertRaises(ValueError):
            validate_html(self.GOOD.replace('</body>', '</script></body>'))


if __name__ == '__main__':
    unittest.main()
