"""What CI runs, with only what needs reading printed.

    python3 tools/verify.py                 all steps
    python3 tools/verify.py build entries   some of them

Steps: `build` regenerates site/data/mala.json and site/sw.js and fails if they
differ from what was there (the regenerated files stay, so commit them);
`entries` is tools/verify_entries.py; `contract` is tools/check_contract.py
(pins, permissions, timeouts, the service worker, the docs). Every step runs
even when an earlier one fails. The last line is `VERIFY: PASS` or
`VERIFY: FAIL (<steps>)`.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
GENERATED = [ROOT / "site" / "data" / "mala.json", ROOT / "site" / "sw.js"]


def read_generated():
    return {path: path.read_bytes() for path in GENERATED}


def build():
    """Returns (ok, output)."""
    before = read_generated()
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "build_site_data.py")],
        cwd=ROOT, capture_output=True, text=True,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        return False, output
    stale = [str(p.relative_to(ROOT)) for p, data in before.items() if p.read_bytes() != data]
    ok = True
    if stale:
        ok = False
        output += (
            "These generated files were stale and have been regenerated; commit them: "
            + ", ".join(stale) + "\n"
        )
    if os.environ.get("CI"):
        # git diff ignores untracked files; in CI an untracked file under
        # site/ is one the deploy would publish but the repository lacks.
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "site"],
            cwd=ROOT, capture_output=True, text=True,
        ).stdout.split()
        if untracked:
            ok = False
            output += "Untracked files under site/ after the build: " + ", ".join(untracked) + "\n"
    return ok, output


def command(*args):
    def run():
        result = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)
        return result.returncode == 0, result.stdout + result.stderr
    return run


STEPS = {
    "build": build,
    "entries": command(str(ROOT / "tools" / "verify_entries.py")),
    "contract": command(str(ROOT / "tools" / "check_contract.py")),
}


def main(argv):
    unknown = [name for name in argv if name not in STEPS]
    if unknown:
        print(f"unknown step: {' '.join(unknown)} (steps: {' '.join(STEPS)})")
        return 2
    failed = []
    for name in argv or STEPS:
        started = time.time()
        ok, output = STEPS[name]()
        seconds = f"{time.time() - started:.1f} s"
        if ok:
            print(f"✓ {name} ({seconds})")
            continue
        failed.append(name)
        print(f"✗ {name} ({seconds})")
        print("\n".join(output.strip().splitlines()[-40:]))
    print(f"VERIFY: FAIL ({' '.join(failed)})" if failed else "VERIFY: PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
