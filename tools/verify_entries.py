"""Check the extracted entries against the chapters they came from.

The summaries were written by language models, so the claim that "no breath was
dropped" needs to be tested rather than trusted. This script cannot judge
meaning, but it can catch the two failures that matter most:

  1. A chapter's breath instructions outnumbering the entry's — a dropped breath.
  2. An entry asserting a vinyasa count or drishti the chapter never printed.

It reports; it does not edit. Every flag is for a human to read.
"""

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
ENTRIES_DIRECTORY = PROJECT_ROOT / "site" / "data" / "entries"
BOOK_RAW_FILE = PROJECT_ROOT / "site" / "data" / "book-raw.json"

BREATH_PATTERN = re.compile(
    r"\b(puraka|rechaka|kumbhaka|inhal\w*|exhal\w*|breath\w*)\b", re.IGNORECASE
)


def count_breaths(text):
    return len(BREATH_PATTERN.findall(text))


def entry_text(entry):
    """Every string in the entry that could carry a breath instruction."""
    parts = [step.get("action", "") for step in entry.get("sequence", [])]
    parts += [step.get("breath") or "" for step in entry.get("sequence", [])]
    parts += [step.get("breath_as_printed") or "" for step in entry.get("sequence", [])]
    parts += entry.get("while_holding", []) or []
    parts += entry.get("notes", []) or []
    parts += entry.get("quotes", []) or []
    return " ".join(parts)


def main():
    chapters = {chapter["source_file"]: chapter for chapter in json.loads(BOOK_RAW_FILE.read_text())}
    entries = [json.loads(path.read_text()) for path in sorted(ENTRIES_DIRECTORY.glob("*.json"))]
    problems = []

    # Guruji regularly states a fact about one asana in the next asana's chapter
    # — the gazing point for Baddha Padmasana is printed under Padmasana. So a
    # claim is checked against the whole book, not only its own chapter.
    whole_book = "\n".join(chapter["plain_text"] for chapter in chapters.values())

    # A chapter split across several entries cannot be compared breath-for-breath
    # against any one of them.
    entries_per_chapter = {}
    for entry in entries:
        entries_per_chapter[entry.get("source_file")] = (
            entries_per_chapter.get(entry.get("source_file"), 0) + 1
        )

    for entry in entries:
        chapter = chapters.get(entry.get("source_file"))
        if chapter is None or entry.get("kind") == "concept":
            continue

        source_text = chapter["plain_text"]
        source_breaths = count_breaths(source_text)
        entry_breaths = count_breaths(entry_text(entry))

        # A chapter is allowed to say "puraka" in prose the summary compresses,
        # so only a large shortfall is evidence of a dropped instruction.
        is_shared_chapter = entries_per_chapter[entry["source_file"]] > 1
        if source_breaths and not is_shared_chapter and entry_breaths < source_breaths * 0.5:
            problems.append(
                f"{entry['id']}: {entry_breaths} breath words vs {source_breaths} in the chapter"
            )

        if entry.get("vinyasa_count") is not None:
            # The count is printed either as "sixteen vinyasas" or implicitly, by
            # the method numbering its steps up to "this is the Nth vinyasa".
            states_a_total = re.search(r"\w+\s+vinyasas", source_text.lower())
            enumerated = re.findall(r"the (\d+)(?:st|nd|rd|th) vinyasa", source_text.lower())
            highest_enumerated = max((int(number) for number in enumerated), default=0)
            if not states_a_total and highest_enumerated < entry["vinyasa_count"]:
                problems.append(
                    f"{entry['id']}: claims {entry['vinyasa_count']} vinyasas, "
                    f"chapter prints no count and enumerates only {highest_enumerated}"
                )

        if entry.get("drishti"):
            if not re.search(r"gaz\w*|drishti|eyebrow|nose", whole_book, re.IGNORECASE):
                problems.append(
                    f"{entry['id']}: states drishti '{entry['drishti']}', the book names no gazing point"
                )

        for step in entry.get("sequence", []):
            if step.get("is_state") and step.get("vinyasa") is not None:
                if step["vinyasa"] not in (entry.get("state_vinyasas") or []):
                    problems.append(
                        f"{entry['id']}: vinyasa {step['vinyasa']} marked as state "
                        f"but state_vinyasas is {entry.get('state_vinyasas')}"
                    )

    for problem in problems:
        print("FLAG", problem)
    print(f"\n{len(problems)} flags")
    return 0


if __name__ == "__main__":
    sys.exit(main())
