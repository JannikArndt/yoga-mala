"""Is this tree's version what the live site serves?

    python3 tools/live.py                answers now (exit 1 if not)
    python3 tools/live.py --wait         polls every 5 s, up to 10 minutes
    python3 tools/live.py --url <base>   another address (a custom domain)
    python3 tools/live.py --print-version  the committed VERSION, nothing else

The version is the content hash in the generated block of site/sw.js. The last
line is `LIVE: <version>` or `NOT LIVE: want <a>, <url> serves <b>`.
"""

import os
import re
import sys
import time
import urllib.request
from pathlib import Path

PAGE_URL = "https://jannikarndt.github.io/yoga-mala/"
SERVICE_WORKER = Path(__file__).parent.parent / "site" / "sw.js"
VERSION = re.compile(r'^const VERSION = "([^"]+)";', re.MULTILINE)


def committed_version():
    return VERSION.search(SERVICE_WORKER.read_text()).group(1)


def served_version(base):
    # The query defeats Pages' ten-minute CDN cache; no-store defeats ours.
    request = urllib.request.Request(
        f"{base}/sw.js?t={int(time.time())}", headers={"Cache-Control": "no-cache"}
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            match = VERSION.search(response.read().decode())
            return match.group(1) if match else "no VERSION in sw.js"
    except Exception as error:  # a verdict line must always come out
        return getattr(error, "code", None) and f"HTTP {error.code}" or type(error).__name__


def main(argv):
    if "--print-version" in argv:
        print(committed_version())
        return 0
    base = os.environ.get("APP_URL") or PAGE_URL
    if "--url" in argv:
        base = argv[argv.index("--url") + 1]
    base = base.rstrip("/")
    want = committed_version()
    started, last = time.time(), ""
    while True:
        got = served_version(base)
        if got == want:
            print(f"LIVE: {want}")
            return 0
        seconds = int(time.time() - started)
        if "--wait" not in argv or seconds > 600:
            print(f"NOT LIVE: want {want}, {base} serves {got}")
            return 1
        if got != last:
            print(f"  {seconds} s: {base} serves {got}")
            last = got
        time.sleep(5)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
