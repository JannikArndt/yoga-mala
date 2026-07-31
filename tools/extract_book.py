"""Extract the Yoga Mala ebook HTML into one structured JSON document.

The ebook is Calibre-generated: semantics live in CSS class names, not tags.
This script converts those class names back into meaning so that every later
step (summarising, rendering) works on data instead of on HTML.

Class-name meanings observed in the source:
  style2 / style3  section heading (METHOD, BENEFITS) *or* an image caption
  style5 / calibre7  body paragraph
  style4             attribution line for a quoted scripture verse
  calibre6           part heading (YAMA, NIYAMA)

An image caption is a style2/style3 paragraph directly followed by an <img>.
"""

import html
import json
import re
from pathlib import Path

EBOOK_TEXT_DIRECTORY = Path(__file__).parent.parent / "ebook" / "Text"
OUTPUT_FILE = Path(__file__).parent.parent / "site" / "data" / "book-raw.json"

HEADING_CLASSES = {"style2", "style3", "calibre6"}
BODY_CLASSES = {"style5", "calibre7", "calibre8"}
ATTRIBUTION_CLASSES = {"style4"}


def strip_tags(fragment):
    """Turn an HTML fragment into the plain text a reader would see."""
    without_tags = re.sub(r"<[^>]+>", "", fragment)
    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()


def parse_blocks(chapter_html):
    """Walk the chapter in document order, yielding typed content blocks.

    Order matters: an image belongs to the caption that precedes it, and the
    METHOD/BENEFITS headings partition the body paragraphs that follow them.
    """
    blocks = []
    element_pattern = re.compile(
        r'<p class="([a-z0-9]+)"[^>]*>(.*?)</p>|<img[^>]*src="\.\./Images/([^"]+)"',
        re.DOTALL,
    )
    for match in element_pattern.finditer(chapter_html):
        class_name, inner_html, image_file = match.groups()
        if image_file:
            blocks.append({"kind": "image", "file": image_file})
            continue
        text = strip_tags(inner_html)
        if not text:
            continue
        if class_name in HEADING_CLASSES:
            blocks.append({"kind": "heading", "text": text, "class": class_name})
        elif class_name in ATTRIBUTION_CLASSES:
            blocks.append({"kind": "attribution", "text": text})
        elif class_name in BODY_CLASSES:
            blocks.append({"kind": "paragraph", "text": text})
    return blocks


def attach_captions_to_images(blocks):
    """Replace each image block's caption with the heading that introduced it.

    Also removes those headings from the block list so they are not mistaken
    for section headings like METHOD.
    """
    result = []
    for index, block in enumerate(blocks):
        is_caption = (
            block["kind"] == "heading"
            and index + 1 < len(blocks)
            and blocks[index + 1]["kind"] == "image"
        )
        if is_caption:
            continue
        if block["kind"] == "image":
            previous = blocks[index - 1] if index else None
            caption = previous["text"] if previous and previous["kind"] == "heading" else ""
            result.append({**block, "caption": caption})
        else:
            result.append(block)
    return result


def read_chapter(path):
    chapter_html = path.read_text(encoding="utf-8")
    title_match = re.search(r"<title>(.*?)</title>", chapter_html, re.DOTALL)
    blocks = attach_captions_to_images(parse_blocks(chapter_html))
    return {
        "source_file": path.name,
        "title": html.unescape(title_match.group(1)).strip() if title_match else path.stem,
        "blocks": blocks,
        "plain_text": "\n\n".join(
            block["text"] for block in blocks if block["kind"] != "image"
        ),
    }


def main():
    chapter_paths = sorted(
        EBOOK_TEXT_DIRECTORY.glob("chapter*.html"),
        key=lambda path: path.name,
    )
    chapters = [read_chapter(path) for path in chapter_paths]
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(chapters, indent=1, ensure_ascii=False))
    total_images = sum(
        1 for chapter in chapters for block in chapter["blocks"] if block["kind"] == "image"
    )
    print(f"{len(chapters)} chapters, {total_images} images -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
