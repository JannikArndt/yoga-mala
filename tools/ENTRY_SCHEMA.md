# Entry schema

Every practice entry is one JSON file at `site/data/entries/<id>.json`.

## The one rule that outranks all others

**Nothing may appear in an entry that is not in Guruji's text.** This site
honours the book; it does not improve, modernise, or complete it. If the book
does not name a drishti, `drishti` is `null` — do not supply one from other
Ashtanga sources, however well known. If the book gives no benefits, the array
is empty. Never invent counts, Sanskrit translations, cautions, or vinyasa
numbers. When the source is ambiguous, prefer its exact words.

## Fields

```jsonc
{
  "id": "padangushtasana",          // kebab-case, unique, stable (used in URLs)
  "number": 1,                       // asana number as printed; null if unnumbered
  "title": "Padangushtasana",        // display name, title case
  "title_as_printed": "1. PADANGUSHTASANA",
  "section": "standing",             // surya-namaskara | standing | seated | finishing
  "source_file": "chapter0006.html",

  "vinyasa_count": 3,                // integer, or null if the book does not say
  "state_vinyasas": [2],             // which vinyasas ARE the asana; [] if not stated
  // Optional display overrides, for asanas whose count or states the numbers
  // alone would misstate (Supta Padangushtasana's two parts):
  // "vinyasa_label": "20 in part 1, 28 in part 2",
  // "state_label": "9 and 13 in part 1; 11 and 19 in part 2",
  "drishti": null,                   // legacy; put gazing points on the steps
  "translation": null,               // only if the book translates the name

  // The framing sentences before METHOD, if they carry meaning beyond the
  // vinyasa count. One short bullet each. Usually empty.
  "notes": [],

  // The METHOD, one bullet per vinyasa, in order.
  // EVERY breath in the source must survive. Prose must not.
  "sequence": [
    {
      "vinyasa": 1,                  // integer; null for un-numbered lead-in steps
      "breath": "inhale",            // inhale | exhale | inhale-exhale | exhale-inhale | free | hold | null
      "breath_as_printed": "puraka", // Guruji's word: puraka | rechaka | ... | null
      "action": "Jump the legs half a foot apart, take hold of the big toes, lift head and chest, knees straight.",
      "is_state": false,             // true when this vinyasa is the state of the asana
      "drishti": "fingertips",       // optional; only where the book names the gaze for this step
      "borrowed": true               // optional; a step carried over from another asana
    }
  ],

  // Instructions that apply while holding, not to a single vinyasa.
  "while_holding": [
    "Draw the lower abdomen in and hold it tightly.",
    "Rechaka and puraka slowly and as fully as possible."
  ],

  // The book's BENEFITS, as whole sentences in Guruji's exact words. They are
  // shown in quotation marks, so a claim about disease is never restated as
  // fact. Where the book gives benefits for a group of asanas in one place,
  // every member carries them and "benefits_source" says so.
  "benefits": [
    "Padangushtasana dissolves the fat of the lower abdomen, and purifies both the kanda, or egg-shaped nerve plexus in the anal region, and the rectum."
  ],
  "benefits_source": null,

  // Verbatim sentences worth showing beside the summary — Guruji's voice.
  // 0–3 per entry. Quote exactly, including his punctuation.
  "quotes": [],

  // Scripture he quotes: { "sanskrit": "...", "translation": "...", "source": "..." }.
  // Not his words, so never in "quotes".
  "verses": [],

  // Filled in later by the image-matching pass. Always emit as [].
  "images": []
}
```

## Writing the `sequence` bullets

- One bullet per vinyasa the book describes, `vinyasa` matching its number.
- `action` is imperative, no filler: "Exhale, head between the knees" not
  "Then, letting the breath out, one should place the head...".
- Split a vinyasa into two bullets only if the book gives it two distinct
  breaths that are not a hold.
- A combined breath keeps the book's order: "rechaka and then puraka" is
  `exhale-inhale`, "puraka and then rechaka" is `inhale-exhale`. Steady
  breathing while staying in a state ("rechaka and puraka as much as
  possible") is `free`.
- `breath: "free"` means the book says to breathe freely / as much as possible.
  `breath: "hold"` means the book says to stay while holding the breath.
- Write references out. Where the book says "do the first six vinyasas of the
  first Surya Namaskara" or "the remaining vinyasas follow Paschimattanasana",
  add those vinyasas as steps with their own numbers and breaths, marked
  `"borrowed": true` so they are shown smaller and fainter. Name the Surya
  Namaskara's 4th, 5th and 6th vinyasas as the book's plates do: Chaturanga
  Dandasana, Urdhva Mukha Svanasana, Adho Mukha Svanasana. Expand only where
  the mapping is fixed: the numbering must then run exactly from 1 to
  `vinyasa_count`.

## Sanity checks before you write the file

1. Does every `puraka` / `rechaka` / "inhale" / "exhale" in the METHOD text
   appear somewhere in `sequence`? Count them.
2. Do `state_vinyasas` and the `is_state: true` bullets agree?
3. Is every fact traceable to a sentence in the chapter? Delete it if not.
4. Is the JSON valid and does it parse? Run `tools/verify_entries.py`, with
   the ebook unpacked so the wording and breath order are checked too.
