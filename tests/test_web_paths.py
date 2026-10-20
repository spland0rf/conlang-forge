"""The site is served under a prefix (https://host/conlang/), so pages must refer to their files by relative paths."""
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "conlang_forge" / "web"


def test_no_root_absolute_static_paths():
    for f in [WEB / "index.html", *(WEB / "static").glob("*.html"), *(WEB / "static" / "js").glob("*.js"), WEB / "static" / "site.webmanifest"]:
        text = f.read_text()
        for bad in ('"/static/', "'/static/", 'src="/', 'href="/static'):
            assert bad not in text, f"{f.name} uses a root-absolute path ({bad})"
