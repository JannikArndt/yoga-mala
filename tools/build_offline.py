"""Write the list of files, and their version, into the service worker.

The reader works offline because site/sw.js caches every file it needs when
it installs. This script keeps that list complete and stamps it with a hash
of the files' contents: browsers install a new service worker only when
sw.js itself changes, so without a new hash an edit would never reach a phone
that already has the site. build_site_data.py runs it after every build.
"""

import hashlib
import json
import re
from pathlib import Path

SITE_DIRECTORY = Path(__file__).parent.parent / "site"
SERVICE_WORKER = SITE_DIRECTORY / "sw.js"
NOT_CACHED = {"sw.js", ".nojekyll"}
# The editable sources of mala.json; the reader never fetches them.
SOURCE_DATA = ("data/entries/", "data/images.json", "data/about.json")
GENERATED_BLOCK = re.compile(r"// BEGIN GENERATED\n.*?// END GENERATED", re.DOTALL)


def site_files():
    names = (
        path.relative_to(SITE_DIRECTORY).as_posix()
        for path in SITE_DIRECTORY.rglob("*")
        if path.is_file() and path.name not in NOT_CACHED and not path.name.startswith(".")
    )
    return sorted(name for name in names if not name.startswith(SOURCE_DATA))


def main():
    files = site_files()
    digest = hashlib.sha256()
    for name in files:
        digest.update(name.encode())
        digest.update((SITE_DIRECTORY / name).read_bytes())
    version = digest.hexdigest()[:12]

    # The page itself is cached as "./", the address the reader opens.
    urls = ["./" if name == "index.html" else name for name in files]
    block = (
        "// BEGIN GENERATED\n"
        f"const VERSION = {json.dumps(version)};\n"
        f"const FILES = {json.dumps(urls, indent=2)};\n"
        "// END GENERATED"
    )
    source = SERVICE_WORKER.read_text()
    SERVICE_WORKER.write_text(GENERATED_BLOCK.sub(lambda _: block, source, count=1))
    size_megabytes = sum((SITE_DIRECTORY / name).stat().st_size for name in files) / 1e6
    print(f"{len(files)} files ({size_megabytes:.1f} MB) cached offline, version {version}")


if __name__ == "__main__":
    main()
