"""Compile the per-entry JSON files into the single payload the site fetches.

Entries are authored one file per asana or concept because that is how the
extraction work was divided. The browser wants the opposite: one request, in
reading order, with the plates already attached. This script is the seam.

Reading order is declared here rather than derived, because the book's order is
not recoverable from the entries themselves — Guruji numbers the asanas but not
the concepts, and the four Prasarita Padottanasanas share one number.
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
ENTRIES_DIRECTORY = PROJECT_ROOT / "site" / "data" / "entries"
IMAGES_FILE = PROJECT_ROOT / "site" / "data" / "images.json"
ABOUT_FILE = PROJECT_ROOT / "site" / "data" / "about.json"
OUTPUT_FILE = PROJECT_ROOT / "site" / "data" / "mala.json"

# A recording of Guruji leading the series, linked from every asana. Title and
# note are what YouTube itself reports for the upload; nothing more is claimed.
PRIMARY_SERIES_VIDEO = {
    "title": "Primary Series Ashtanga with Sri K. Pattabhi Jois",
    "note": "YouTube",
    "url": "https://www.youtube.com/watch?v=aUgtMaAZzW0",
}

# Part -> chapter -> the entry ids in that chapter, in the order the book gives.
NAVIGATION = [
    {
        "id": "practice",
        "title": "Yoga Asanas",
        "subtitle": "Part One",
        "chapters": [
            {
                "id": "surya-namaskara",
                "title": "Surya Namaskara",
                "entries": [
                    "surya-namaskara-intro",
                    "surya-namaskara-a",
                    "surya-namaskara-b",
                ],
            },
            {
                "id": "standing",
                "title": "Standing",
                "entries": [
                    "padangushtasana",
                    "padahastasana",
                    "utthita-trikonasana",
                    "utthita-parshvakonasana",
                    "prasarita-padottanasana-a",
                    "prasarita-padottanasana-b",
                    "prasarita-padottanasana-c",
                    "prasarita-padottanasana-d",
                    "parshvottanasana",
                    "utthita-hasta-padangushtasana",
                    "ardha-baddha-padmottanasana",
                    "utkatasana",
                    "virabhadrasana",
                ],
            },
            {
                "id": "seated",
                "title": "Seated",
                "entries": [
                    "paschimattanasana",
                    "purvatanasana",
                    "ardha-baddha-padma-paschimattanasana",
                    "tiriangmukhaikapada-paschimattanasana",
                    "janu-shirshasana-a",
                    "janu-shirshasana-b",
                    "janu-shirshasana-c",
                    "marichyasana-a",
                    "marichyasana-b",
                    "marichyasana-c",
                    "marichyasana-d",
                    "navasana",
                    "bhujapidasana",
                    "kurmasana",
                    "garbha-pindasana",
                    "kukkutasana",
                    "baddha-konasana",
                    "upavishta-konasana",
                    "supta-konasana",
                    "supta-padangushtasana",
                    "ubhaya-padangushtasana",
                    "urdhva-mukha-paschimattanasana",
                    "setu-bandhasana",
                ],
            },
            {
                "id": "finishing",
                "title": "Finishing",
                "entries": [
                    "sarvangasana",
                    "halasana",
                    "karnapidasana",
                    "urdhva-padmasana",
                    "pindasana",
                    "matsyasana",
                    "uttana-padasana",
                    "shirshasana",
                    "baddha-padmasana",
                    "padmasana",
                    "uth-pluthi",
                ],
            },
        ],
    },
    {
        "id": "shastra",
        "title": "Yoga Shastra",
        "subtitle": "Part Two",
        "chapters": [
            {
                "id": "foundation",
                "title": "What Is Yoga",
                "entries": ["what-is-yoga", "ashtanga"],
            },
            {
                "id": "yama",
                "title": "Yama",
                "entries": [
                    "yama",
                    "ahimsa",
                    "satya",
                    "asteya",
                    "brahmacharya",
                    "aparigraha",
                ],
            },
            {
                "id": "niyama",
                "title": "Niyama",
                "entries": [
                    "niyama",
                    "shaucha",
                    "santosha",
                    "tapas",
                    "swadhyaya",
                    "ishwarapranidhana",
                ],
            },
            {
                "id": "limbs",
                "title": "The Further Limbs",
                "entries": [
                    "asana",
                    "pranayama",
                    "pratyahara",
                    "dharana",
                    "dhyana",
                    "samadhi",
                ],
            },
        ],
    },
]


def load_entries():
    entries = {}
    for path in sorted(ENTRIES_DIRECTORY.glob("*.json")):
        entry = json.loads(path.read_text())
        entries[entry["id"]] = entry
    return entries


def report_mismatches(entries):
    """Fail loudly when the declared order and the extracted files disagree."""
    declared = [
        entry_id
        for part in NAVIGATION
        for chapter in part["chapters"]
        for entry_id in chapter["entries"]
    ]
    missing = [entry_id for entry_id in declared if entry_id not in entries]
    orphaned = [entry_id for entry_id in entries if entry_id not in declared]
    if missing:
        print(f"MISSING {len(missing)} declared but not extracted: {missing}")
    if orphaned:
        print(f"ORPHANED {len(orphaned)} extracted but not placed: {orphaned}")
    return missing, orphaned


def main():
    entries = load_entries()
    images_by_entry = json.loads(IMAGES_FILE.read_text())
    missing, _ = report_mismatches(entries)

    for entry_id, entry in entries.items():
        entry["images"] = images_by_entry.get(entry_id, [])

    # Flat reading order drives the previous/next arrows and the keyboard.
    reading_order = []
    for part in NAVIGATION:
        for chapter in part["chapters"]:
            for entry_id in chapter["entries"]:
                if entry_id in entries:
                    reading_order.append(entry_id)

    payload = {
        "navigation": [
            {
                **part,
                "chapters": [
                    {
                        **chapter,
                        "entries": [
                            entry_id
                            for entry_id in chapter["entries"]
                            if entry_id in entries
                        ],
                    }
                    for chapter in part["chapters"]
                ],
            }
            for part in NAVIGATION
        ],
        "reading_order": reading_order,
        "entries": entries,
        "gallery": images_by_entry.get("_gallery", []),
        "portrait": images_by_entry.get("_portrait", []),
        "cover": images_by_entry.get("_cover", []),
        "video": PRIMARY_SERIES_VIDEO,
        "about": json.loads(ABOUT_FILE.read_text()) if ABOUT_FILE.exists() else None,
    }
    OUTPUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    size_kilobytes = OUTPUT_FILE.stat().st_size / 1024
    print(
        f"{len(reading_order)} entries in reading order, "
        f"{len(missing)} missing -> {OUTPUT_FILE.name} ({size_kilobytes:.0f} KB)"
    )

    # The offline cache is versioned by the files' contents, mala.json among them.
    sys.path.insert(0, str(Path(__file__).parent))
    import build_offline

    build_offline.main()


if __name__ == "__main__":
    main()
