"""Map the ebook's plates to practice entries, and copy them into the site.

The plates are matched by their printed caption, not by the chapter they sit
in: the ebook lays a plate out on the page *after* the asana it depicts, so
chapter position is misleading while the caption never is.

Ten plates carry no caption in the ebook markup. Those were identified by
looking at the photographs — several have the caption burned into the emulsion
— and are listed in UNCAPTIONED_PLATES with the evidence for each.
"""

import json
import re
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SOURCE_IMAGE_DIRECTORY = PROJECT_ROOT / "ebook" / "Images"
SITE_IMAGE_DIRECTORY = PROJECT_ROOT / "site" / "assets" / "plates"
BOOK_RAW_FILE = PROJECT_ROOT / "site" / "data" / "book-raw.json"
OUTPUT_FILE = PROJECT_ROOT / "site" / "data" / "images.json"

# Caption text -> entry id, where slugifying the caption is not enough.
CAPTION_TO_ENTRY_OVERRIDES = {
    "supta-kurmasana": "kurmasana",
    "paschimattanasana-1st-type": "paschimattanasana",
    "paschimattanasana-2nd-type": "paschimattanasana",
    "paschimattanasana-3rd-type": "paschimattanasana",
    "supta-padangushtasana-1st-part": "supta-padangushtasana",
    "supta-padangushtasana-2nd-part": "supta-padangushtasana",
    "yoga-mudra-baddha-padmasana": "baddha-padmasana",
    "samasthiti": "surya-namaskara-intro",
    "first-surya-namaskara-second-surya-namaskara": "surya-namaskara-a",
    "second-surya-namaskara": "surya-namaskara-b",
}

# Plates the ebook leaves uncaptioned, resolved by inspecting the photographs.
UNCAPTIONED_PLATES = {
    "image-55DMNTM0.jpg": ("surya-namaskara-a", "First Surya Namaskara, 1st vinyasa"),
    "image-Q8OV7B6U.jpg": ("surya-namaskara-a", "First Surya Namaskara, 2nd vinyasa"),
    "image-SJ7NCRUQ.jpg": ("surya-namaskara-a", "First Surya Namaskara, 3rd vinyasa"),
    "image-U2YOUK6H.jpg": ("sarvangasana", "Sarvangasana"),
    "image-KCLK7QH6.jpg": ("shirshasana", "Shirshasana"),
    "image-6IYBVHVS.jpg": ("baddha-padmasana", "Baddha Padmasana"),
    "image-NN0YYGR6.jpg": ("padmasana", "Padmasana"),
    "image-VUG0QN0P.jpg": ("uth-pluthi", "Uth Pluthi"),
    # Documentary photographs of the shala rather than plates of an asana.
    "image-2GPC79M3.jpg": ("_gallery", "Guruji in Shirshasana at the shala"),
    "image-8JZ4UXQ2.jpg": ("_gallery", "Students practising at the shala"),
    # Front matter.
    "image-R2VF65XM.jpg": ("_cover", "Yoga Mala, cover"),
    "image-PI8UOZYK.jpg": ("_frontmatter", "Title page"),
    "image-W8WAGDFM.jpg": ("_portrait", "Sri K. Pattabhi Jois"),
    "image-JOW7208H.jpg": ("_frontmatter", "Sri Shringeri Jagadguru Mahasamsthanam"),
}


def slugify_caption(caption):
    """Reduce a printed caption to the entry id it names.

    Vinyasa numbers and parenthetical qualifiers are dropped, because several
    plates of the same asana share one entry.
    """
    text = caption.lower()
    text = re.sub(r"\b\d+\s*(st|nd|rd|th)\b", " ", text)
    text = re.sub(r"\bvinyasa\b|\btype\b|\bpart\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def caption_to_entry_ids(caption):
    """Return every entry a plate belongs to.

    Usually one. The Surya Namaskara plates are shared: a single photograph is
    captioned as both a vinyasa of the first sequence and a vinyasa of the
    second, and it should appear under both.
    """
    upper_caption = caption.upper()
    if "FIRST SURYA NAMASKARA" in upper_caption and "SECOND SURYA NAMASKARA" in upper_caption:
        return ["surya-namaskara-a", "surya-namaskara-b"]

    slug = slugify_caption(caption)
    for prefix, entry_id in CAPTION_TO_ENTRY_OVERRIDES.items():
        if slug.startswith(prefix):
            return [entry_id]
    return [slug]


def title_case_caption(caption):
    """The captions are printed in full caps; soften them for the web."""
    return re.sub(
        r"\b([A-Z])([A-Z']+)\b",
        lambda match: match.group(1) + match.group(2).lower(),
        caption.strip(),
    )


def collect_plates():
    chapters = json.loads(BOOK_RAW_FILE.read_text())
    plates = []
    for chapter in chapters:
        for block in chapter["blocks"]:
            if block["kind"] != "image":
                continue
            file_name = block["file"]
            caption = block.get("caption", "").strip()
            if caption:
                entry_ids = caption_to_entry_ids(caption)
                label = title_case_caption(caption)
            elif file_name in UNCAPTIONED_PLATES:
                single_entry_id, label = UNCAPTIONED_PLATES[file_name]
                entry_ids = [single_entry_id]
            else:
                entry_ids, label = ["_unassigned"], ""
            for entry_id in entry_ids:
                plates.append(
                    {
                        "file": file_name,
                        "entry": entry_id,
                        "caption": label,
                        "source_file": chapter["source_file"],
                    }
                )
    return plates


def main():
    plates = collect_plates()

    SITE_IMAGE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for plate in plates:
        shutil.copy2(
            SOURCE_IMAGE_DIRECTORY / plate["file"],
            SITE_IMAGE_DIRECTORY / plate["file"],
        )

    by_entry = {}
    for plate in plates:
        by_entry.setdefault(plate["entry"], []).append(
            {"file": plate["file"], "caption": plate["caption"]}
        )
    OUTPUT_FILE.write_text(json.dumps(by_entry, indent=1, ensure_ascii=False))

    unassigned = by_entry.get("_unassigned", [])
    print(f"{len(plates)} plates -> {len(by_entry)} entries")
    if unassigned:
        print("UNASSIGNED:", [plate["file"] for plate in unassigned])
    for entry_id in sorted(by_entry):
        print(f"  {entry_id}: {len(by_entry[entry_id])}")


if __name__ == "__main__":
    main()
