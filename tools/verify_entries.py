"""Check the entries for consistency, and against the book when it is present.

The summaries were written by language models, so the claim that "no breath was
dropped" needs to be tested rather than trusted. This script cannot judge
meaning, but it catches the failures that have actually occurred:

  Always (these need only the repository, and run in CI):
    - a breath value outside the schema
    - a step marked as the state whose vinyasa is not listed as a state
    - a step numbered beyond the asana's vinyasa count
    - sibling asanas the book describes together disagreeing on their counts
    - an entry declared in the reading order but missing, or a missing plate

  Only with the book unpacked in ebook/ (it is copyrighted and not committed;
  run tools/extract_book.py first):
    - a chapter's breath words outnumbering the entry's — a dropped breath
    - a combined breath recorded in the opposite order to the book's
    - a gazing point the chapter never names
    - a benefit, caution, quote, or verse that is not the book's exact words

It reports every flag and exits non-zero if there are any.
"""

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
ENTRIES_DIRECTORY = PROJECT_ROOT / "site" / "data" / "entries"
IMAGES_FILE = PROJECT_ROOT / "site" / "data" / "images.json"
ABOUT_FILE = PROJECT_ROOT / "site" / "data" / "about.json"
PLATES_DIRECTORY = PROJECT_ROOT / "site" / "assets" / "plates"
BOOK_RAW_FILE = PROJECT_ROOT / "ebook" / "book-raw.json"

sys.path.insert(0, str(Path(__file__).parent))
from build_site_data import NAVIGATION  # noqa: E402

BREATHS = {"inhale", "exhale", "inhale-exhale", "exhale-inhale", "free", "hold", None}

# Asanas the book gives one vinyasa count and one set of states for.
SIBLINGS = [
    ["janu-shirshasana-a", "janu-shirshasana-b", "janu-shirshasana-c"],
    ["marichyasana-a", "marichyasana-b"],
    ["marichyasana-c", "marichyasana-d"],
    [f"prasarita-padottanasana-{part}" for part in "abcd"],
]

BREATH_PATTERN = re.compile(
    r"\b(puraka|rechaka|kumbhaka|inhal\w*|exhal\w*|breath\w*)\b", re.IGNORECASE
)
INHALE_OR_EXHALE = re.compile(r"\b(puraka|inhal\w*)\b|\b(rechaka|exhal\w*)\b", re.IGNORECASE)
VINYASA_CLOSE = re.compile(
    r"this (?:is|constitutes|forms) (?:the )?(\d+)(?:st|nd|rd|th) vinyasa", re.IGNORECASE
)


def count_breaths(text):
    return len(BREATH_PATTERN.findall(text))


def normalise(text):
    """Compare words only: quotes, dashes, footnote marks and spacing vary."""
    text = re.sub(r"[¹²³⁰-⁹]", "", text.lower())
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def entry_text(entry):
    """Every string in the entry that could carry a breath instruction."""
    steps = entry.get("sequence", [])
    parts = [step.get("action", "") for step in steps]
    parts += [step.get("breath") or "" for step in steps]
    parts += [step.get("breath_as_printed") or "" for step in steps]
    for field in ("while_holding", "notes", "quotes", "cautions"):
        parts += entry.get(field) or []
    return " ".join(parts)


def verbatim_fields(entry):
    """(label, text) for every string the site presents as Guruji's own words."""
    for field in ("benefits", "cautions", "quotes"):
        for text in entry.get(field) or []:
            yield field, text
    verses = list(entry.get("verses") or [])
    if entry.get("sutra"):
        verses.append(entry["sutra"])
    for verse in verses:
        for field in ("sanskrit", "translation"):
            if verse.get(field):
                yield f"verse {field}", verse[field]


def check_structure(entries, problems):
    for entry in entries.values():
        steps = entry.get("sequence") or []
        states = entry.get("state_vinyasas") or []
        count = entry.get("vinyasa_count")
        for step in steps:
            if step.get("breath") not in BREATHS:
                problems.append(f"{entry['id']}: unknown breath '{step.get('breath')}'")
            number = step.get("vinyasa")
            if step.get("is_state") and number is not None and number not in states:
                problems.append(
                    f"{entry['id']}: vinyasa {number} marked as state but state_vinyasas is {states}"
                )
            if count and number and number > count:
                problems.append(f"{entry['id']}: step {number} beyond its {count} vinyasas")

    for group in SIBLINGS:
        shapes = {
            entry_id: (entries[entry_id].get("vinyasa_count"), entries[entry_id].get("state_vinyasas"))
            for entry_id in group
            if entry_id in entries
        }
        if len({json.dumps(shape) for shape in shapes.values()}) > 1:
            problems.append(f"siblings disagree on count and states: {shapes}")

    declared = [
        entry_id for part in NAVIGATION for chapter in part["chapters"] for entry_id in chapter["entries"]
    ]
    for entry_id in declared:
        if entry_id not in entries:
            problems.append(f"{entry_id}: in the reading order but has no entry file")

    for plates in json.loads(IMAGES_FILE.read_text()).values():
        for plate in plates:
            if not (PLATES_DIRECTORY / plate["file"]).exists():
                problems.append(f"plate {plate['file']} is listed but missing")


def method_clauses(source_text):
    """Vinyasa number -> the text that describes it, from the METHOD onwards."""
    method = source_text.split("METHOD", 1)[-1]
    clauses, start = {}, 0
    for match in VINYASA_CLOSE.finditer(method):
        clauses.setdefault(int(match.group(1)), method[start:match.start()])
        start = match.end()
    return clauses


def check_against_book(entries, chapters, problems):
    whole_book = normalise(" ".join(chapter["plain_text"] for chapter in chapters.values()))

    entries_per_chapter = {}
    for entry in entries.values():
        source = entry.get("source_file")
        entries_per_chapter[source] = entries_per_chapter.get(source, 0) + 1

    for entry in entries.values():
        for label, text in verbatim_fields(entry):
            if normalise(text) not in whole_book:
                problems.append(f"{entry['id']}: {label} is not the book's wording: {text[:90]}")

        chapter = chapters.get(entry.get("source_file"))
        if chapter is None or entry.get("kind") == "concept":
            continue
        source_text = chapter["plain_text"]

        # A chapter is allowed to say "puraka" in prose the summary compresses,
        # so only a large shortfall is evidence of a dropped instruction.
        source_breaths = count_breaths(source_text)
        is_shared_chapter = entries_per_chapter[entry["source_file"]] > 1
        if source_breaths and not is_shared_chapter and count_breaths(entry_text(entry)) < source_breaths * 0.5:
            problems.append(
                f"{entry['id']}: {count_breaths(entry_text(entry))} breath words vs {source_breaths} in the chapter"
            )

        # A combined breath must start the way the book's own sentence does.
        # Only a vinyasa's first step is compared: later steps of the same
        # vinyasa start partway through the book's sentence.
        clauses = method_clauses(source_text)
        seen_vinyasas = set()
        for step in entry.get("sequence", []):
            is_first = step.get("vinyasa") not in seen_vinyasas
            seen_vinyasas.add(step.get("vinyasa"))
            if not is_first or step.get("breath") not in ("inhale-exhale", "exhale-inhale"):
                continue
            clause = clauses.get(step.get("vinyasa"))
            first = INHALE_OR_EXHALE.search(clause or "")
            if not first:
                continue
            printed_first = "inhale" if first.group(1) else "exhale"
            if not step["breath"].startswith(printed_first):
                problems.append(
                    f"{entry['id']}: vinyasa {step['vinyasa']} is '{step['breath']}' "
                    f"but the book begins it with {first.group(0)}"
                )

        # Guruji sometimes prints a fact about one asana in the next asana's
        # chapter (Baddha Padmasana's gaze is under Padmasana), so the gaze is
        # looked for in the entry's chapter and the one after it.
        chapter_order = sorted(chapters)
        position = chapter_order.index(entry["source_file"])
        gaze_text = normalise(" ".join(
            chapters[name]["plain_text"] for name in chapter_order[position:position + 2]
        ))
        for step in entry.get("sequence", []):
            for word in normalise(step.get("drishti") or "").split():
                if len(word) > 3 and word not in gaze_text:
                    problems.append(f"{entry['id']}: gazing point '{step['drishti']}' not named in the chapter")

    about = json.loads(ABOUT_FILE.read_text())
    about_quotes = [about.get("dedication", "")]
    for section in ("preface", "blessing"):
        about_quotes += about.get(section, {}).get("quotes", [])
    for foreword in about.get("forewords", []):
        about_quotes += foreword["quotes"]
    for text in about_quotes:
        if text and normalise(text) not in whole_book:
            problems.append(f"about: quote is not the book's wording: {text[:90]}")


def main():
    entries = {}
    for path in sorted(ENTRIES_DIRECTORY.glob("*.json")):
        entry = json.loads(path.read_text())
        entries[entry["id"]] = entry

    problems = []
    check_structure(entries, problems)

    if BOOK_RAW_FILE.exists():
        chapters = {chapter["source_file"]: chapter for chapter in json.loads(BOOK_RAW_FILE.read_text())}
        check_against_book(entries, chapters, problems)
    else:
        print(f"{BOOK_RAW_FILE.relative_to(PROJECT_ROOT)} not found: checked structure only, not the text.")

    for problem in problems:
        print("FLAG", problem)
    print(f"\n{len(problems)} flags")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
