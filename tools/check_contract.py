"""The deploy conventions, as checks. Run by tools/verify.py.

Fails when an action pin floats, a workflow runs without permissions or a
timeout, a job other than the deploy may publish to Pages, the service worker
swaps code under a running page, or a tool, workflow or the Pages address is
missing from CLAUDE.md. Delete a check only if the repo has no such thing,
never to get green.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
PAGE_URL = "https://jannikarndt.github.io/yoga-mala/"
problems = []


def flag(message):
    problems.append(message)


def jobs_of(text):
    """{job name: its text} for a workflow."""
    block = re.split(r"^jobs:\s*$", text, flags=re.MULTILINE)[1]
    parts = re.split(r"^  ([\w-]+):\s*$", block, flags=re.MULTILINE)
    return dict(zip(parts[1::2], parts[2::2]))


for path in WORKFLOWS:
    text = path.read_text()
    name = path.name
    for line in re.findall(r"uses:\s*(\S+.*)$", text, flags=re.MULTILINE):
        if line.startswith("./"):
            continue
        if not re.match(r"\S+@[0-9a-f]{40}\s+#\s*v\d", line):
            flag(f"{name}: '{line}' is not pinned to a SHA with a '# vX' comment")
    if not re.search(r"^permissions:\s*\n  contents: read\s*$", text, flags=re.MULTILINE) and name != "dependabot-merge.yml":
        flag(f"{name}: top-level permissions must be exactly 'contents: read'")
    if name == "dependabot-merge.yml" and not re.search(r"^permissions:", text, flags=re.MULTILINE):
        flag(f"{name}: no top-level permissions")
    top = re.split(r"^jobs:", text, flags=re.MULTILINE)[0]
    if re.search(r"^  (pages|id-token): write", top, flags=re.MULTILINE):
        flag(f"{name}: pages/id-token write at workflow level; it belongs on the deploy job only")
    for job, body in jobs_of(text).items():
        if "timeout-minutes:" not in body:
            flag(f"{name}: job {job} has no timeout-minutes")
        if re.search(r"^      (pages|id-token): write", body, flags=re.MULTILINE) and job != "deploy":
            flag(f"{name}: job {job} may publish to Pages; only 'deploy' may")

pages = ROOT / ".github" / "workflows" / "pages.yml"
text = pages.read_text()
if not re.search(r"^  pull_request:", text, flags=re.MULTILINE):
    flag("pages.yml: a pull request must run verify")
deploy = jobs_of(text).get("deploy", "")
if "github.ref == 'refs/heads/main'" not in deploy or "!= 'pull_request'" not in deploy:
    flag("pages.yml: deploy must run only on main and never for a pull request")
if "needs: verify" not in deploy:
    flag("pages.yml: deploy must need verify")
if "tools/verify.py" not in text:
    flag("pages.yml: CI must run tools/verify.py, not a copy of its steps")
if "sw.js" not in deploy or "WANT" not in deploy:
    flag("pages.yml: the deploy has no live check of sw.js VERSION")

merge = (ROOT / ".github" / "workflows" / "dependabot-merge.yml").read_text()
target = re.search(r"DEPLOY_WORKFLOW:\s*(\S+)", merge)
if not target or not (ROOT / ".github" / "workflows" / target.group(1)).exists():
    flag("dependabot-merge.yml: DEPLOY_WORKFLOW does not name an existing workflow")
if "github-actions" not in (ROOT / ".github" / "dependabot.yml").read_text():
    flag("dependabot.yml: github-actions is not watched")

# The service worker: cache-first inside a version, never swapping code
# under a running page (a new worker waits for the reader's tap).
worker = (ROOT / "site" / "sw.js").read_text()
install = re.search(r'addEventListener\("install".*?\n\}\);', worker, flags=re.DOTALL)
if not install:
    flag("sw.js: no install handler found")
elif "skipWaiting" in install.group(0):
    flag("sw.js: install must not call skipWaiting; the reader's tap does (message 'skip-waiting')")
if not re.search(r'^const VERSION = "[0-9a-f]{12}";', worker, flags=re.MULTILINE):
    flag("sw.js: VERSION is not a 12-hex content hash")

# Docs match code.
claude = (ROOT / "CLAUDE.md").read_text() if (ROOT / "CLAUDE.md").exists() else ""
if not claude:
    flag("CLAUDE.md is missing")
for tool in sorted((ROOT / "tools").glob("*.py")):
    if tool.name not in claude:
        flag(f"CLAUDE.md does not mention tools/{tool.name}")
for path in WORKFLOWS:
    if path.name not in claude:
        flag(f"CLAUDE.md does not mention {path.name}")
if PAGE_URL not in claude or PAGE_URL not in (ROOT / "README.md").read_text():
    flag(f"the Pages address {PAGE_URL} must be in CLAUDE.md and README.md")
if PAGE_URL not in (ROOT / "tools" / "live.py").read_text():
    flag("tools/live.py does not default to the Pages address")

for problem in problems:
    print("FLAG", problem)
print(f"{len(problems)} flags")
sys.exit(1 if problems else 0)
