# Yoga Mala

A static reader for Sri K. Pattabhi Jois's *Yoga Mala*, meant to be practised
from on a phone (installed to the Home Screen, works offline). One owner.
Live at https://jannikarndt.github.io/yoga-mala/ (GitHub Pages, deployed by
GitHub Actions). `README.md` says what the site does and how to preview it;
this file is what must stay true when changing it.

## Ship loop

- Work on `main`. A change isn't done until it is live.
- Edit, then `python3 tools/verify.py` (last line `VERIFY: PASS`), commit
  **including the regenerated files**, push `main`.
- CI (`.github/workflows/pages.yml`): verify, deploy, then poll
  `<page>/sw.js?t=…` until its `VERSION` equals the committed one.
- `python3 tools/ship.py` does all of it from a clean tree.

| command | does | last line |
|---|---|---|
| `python3 tools/verify.py [build\|entries\|contract]` | what CI runs: rebuild and compare, entries, deploy contract | `VERIFY: PASS` / `VERIFY: FAIL (…)` |
| `python3 tools/live.py [--wait] [--url base]` | does the live `sw.js` carry this tree's `VERSION`? | `LIVE: <version>` / `NOT LIVE: …` |
| `python3 tools/ship.py` | clean tree → verify → push `main` → `live --wait` | `LIVE: <version>` / `SHIP: FAIL (…)` |
| `python3 tools/build_site_data.py` | entries + images → `site/data/mala.json`, then `sw.js` | one line, files and version |

## Hard constraints

| Constraint | Why |
|---|---|
| Nothing on the site that is not in the book; benefits are his exact sentences in quotation marks | The owner's content rule (README); `tools/verify_entries.py` tests it, in full only where the EPUB is unpacked in `ebook/` |
| The book (`ebook/`) is never committed | Copyrighted; git-ignored. CI can therefore only check the entries' structure |
| `site/` is committed pre-built; no build step beyond the Python tools; no package.json | What is committed is what is served |
| Every path in `site/` is relative | Served under `/yoga-mala/`; the manifest uses `./` |

## Map

| path | owns |
|---|---|
| `site/` | everything that is deployed: `index.html`, `app.js`, `styles.css`, `sw.js`, `manifest.webmanifest`, `assets/`, `data/` |
| `site/data/entries/*.json`, `images.json`, `about.json` | the editable source; fields in `tools/ENTRY_SCHEMA.md` |
| `site/data/mala.json` | **generated** payload the page fetches |
| `site/sw.js` | cache-first service worker; the block between `BEGIN/END GENERATED` is **generated** |
| `tools/build_site_data.py` | entries → `mala.json` (reading order is declared in `NAVIGATION`), then calls `build_offline.py` |
| `tools/build_offline.py` | writes the cached file list and `VERSION` (sha256 over names and bytes of every cached file, first 12 hex) into `sw.js` |
| `tools/verify_entries.py` | consistency of the entries; vs the book text when `ebook/` exists |
| `tools/extract_book.py` | unpacked EPUB → `ebook/book-raw.json`, input to the full check |
| `tools/build_icons.py` | regenerates `site/assets/icons/` |
| `tools/asana-manifest.json` | asana list the tools read |
| `tools/verify.py`, `live.py`, `ship.py`, `check_contract.py` | the dev loop above; `check_contract.py` holds the workflows, the service worker and these docs to the conventions |
| `.github/workflows/pages.yml`, `dependabot-merge.yml`, `.github/dependabot.yml` | CI, Dependabot merging itself on green |

## Invariants and traps

- **Regenerate, then commit.** Editing *any* file in `site/` changes `VERSION`.
  Run `python3 tools/build_site_data.py` (or `verify.py`, which does and tells
  you) and commit `site/data/mala.json` and `site/sw.js` with the change.
  CI rebuilds and fails on a difference; two branches touching `site/` will
  conflict in the generated block — resolve by rerunning the build, never by
  hand.
- **The version is a content hash, not a timestamp**, so the service worker
  updates only when something shipped changed. The editable sources
  (`data/entries/`, `images.json`, `about.json`) are not cached and not hashed;
  `mala.json` is.
- **Update flow**: `install` does not call `skipWaiting()`; a new worker waits,
  the page offers a reload, the tap posts `skip-waiting`, `controllerchange`
  reloads once. Reading position survives. Never make the worker network-first
  and never reload automatically: a reader may be mid-practice.
- Pages' CDN serves `sw.js` with about ten minutes of cache; the live check
  uses a `?t=` query and a ten-minute window for that reason.
- CI uses the runner's `python3` (no pinned Python); keep the tools to the
  standard library.

## Deploying

- Settings → Pages → Source: GitHub Actions (set once, by the owner).
- Workflow jobs: `verify` (`permissions: contents: read`) then `deploy`
  (`pages: write`, `id-token: write`, `environment: github-pages`, then the
  live check). Pull requests run `verify` only. No secrets, no variables.
- Actions are pinned to SHAs with a version comment. Dependabot proposes bumps
  weekly (majors ignored); `dependabot-merge.yml` verifies, merges and starts
  `pages.yml` (a merge by the workflow token does not trigger push workflows).

## Do not

- Add a fact, gazing point or benefit the book does not give, or modernise or
  correct the text.
- Commit `ebook/` or anything unpacked from the EPUB.
- Hand-edit the generated blocks or `mala.json`.
- Add a dependency or a build step.
