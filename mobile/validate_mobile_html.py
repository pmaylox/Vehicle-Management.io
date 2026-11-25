"""Validate the actual mobile document, including HTML embedded in an APK.

Usage: python mobile/validate_mobile_html.py [HTML or APK paths ...]
"""
from html.parser import HTMLParser
from pathlib import Path
from zipfile import ZipFile
import sys


class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.scripts = 0
        self.in_script = False
        self.closed = False

    def handle_starttag(self, tag, attrs):
        if self.closed:
            raise ValueError("Markup appears after </html>")
        if tag == "script":
            self.scripts += 1
            self.in_script = True
        for key, value in attrs:
            if key == "id":
                if value in self.ids:
                    raise ValueError(f"Duplicate static element ID: {value}")
                self.ids.add(value)

    def handle_endtag(self, tag):
        if tag == "script":
            if not self.in_script:
                raise ValueError("Unmatched </script>")
            self.in_script = False
        if tag == "html":
            if self.closed:
                raise ValueError("Multiple HTML documents")
            self.closed = True

    def handle_data(self, data):
        if self.closed and data.strip():
            raise ValueError("Text or application code appears after </html>")
        if not self.in_script and "${" in data:
            raise ValueError("Unrendered JavaScript template appears outside the script")


def validate_html(text):
    parser = Document()
    parser.feed(text)
    parser.close()
    if not parser.closed or parser.in_script or parser.scripts != 1:
        raise ValueError("Expected one complete HTML document and one closed script")
    if not text.rstrip().lower().endswith("</html>"):
        raise ValueError("Unexpected trailing content")


def validate_path(path):
    if path.suffix.lower() == ".apk":
        with ZipFile(path) as archive:
            text = archive.read("assets/index.html").decode("utf-8")
    else:
        text = path.read_text(encoding="utf-8")
    validate_html(text)


if __name__ == "__main__":
    paths = sys.argv[1:] or [
        "mobile/MileSage_Mobile_Auto_Refresh.html",
        "mobile/MileSage_Alpha_1_3_2_VIN_Lookup.html",
    ]
    for filename in paths:
        validate_path(Path(filename))
        print("PASS: complete document, unique IDs, no leaked JavaScript:", filename)
