"""The one way to deploy by hand: clean tree, verify, push main, wait until live.

GitHub Actions does the deploy; this only watches for the result.
Last line: `LIVE: <version>` or `SHIP: FAIL (<why>)`.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def run(*command):
    return subprocess.run(command, cwd=ROOT).returncode == 0


def main():
    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True
    ).stdout
    if dirty:
        print(dirty, end="")
        print("SHIP: FAIL (commit first; the tree has changes)")
        return 1
    if not run(sys.executable, "tools/verify.py"):
        print("SHIP: FAIL (verify)")
        return 1
    if not run("git", "push", "origin", "HEAD:main"):
        print("SHIP: FAIL (push)")
        return 1
    return 0 if run(sys.executable, "tools/live.py", "--wait") else 1


if __name__ == "__main__":
    sys.exit(main())
