# Yoga Mala — an interactive reader

A static site that presents Sri K. Pattabhi Jois's *Yoga Mala* as something you
can practice from: the Surya Namaskara, the asanas in the order he teaches them,
and the eight limbs of Patanjali as he explains them.

The left of each page is the practice, compressed to bullets — one line per
vinyasa, every breath kept. The right is what supports it: the plates from the
book, the benefits he gives, and his own sentences where they are worth reading
whole.

## The rule the content follows

**Nothing on the site that is not in the book.** Where Guruji names no gazing
point, none is supplied, however standard it has since become. Where he gives no
benefits, the section is absent. Where he makes a claim about disease, it is
kept as a quotation in his words rather than restated as fact. The site does not
modernise him, correct him, or fill his gaps from later Ashtanga sources.

`tools/verify_entries.py` tests that rule mechanically — it re-reads every
chapter and flags any entry whose breath instructions, vinyasa counts, or
gazing points are not traceable back to the text.

## Layout

```
ebook/                 the source EPUB, unpacked (not published)
site/                  everything that gets deployed
  index.html
  app.js               routing, rendering, keyboard and swipe paging
  styles.css
  data/mala.json       the compiled payload the page fetches
  data/entries/*.json  one file per asana or concept — the editable source
  assets/plates/       the photographs, copied from the ebook
tools/                 the build and verification scripts
```

## Rebuilding

```sh
python3 tools/extract_book.py     # ebook HTML  -> data/book-raw.json
python3 tools/build_images.py     # plates      -> assets/ + data/images.json
python3 tools/build_site_data.py  # entries     -> data/mala.json
python3 tools/verify_entries.py   # check the entries against the book
```

Reading order and the chapter grouping are declared in `tools/build_site_data.py`.
To correct a posture, edit its file in `site/data/entries/` and re-run the third
command.

Preview locally with `python3 -m http.server 8765 --directory site`.

## Deployment

`.github/workflows/pages.yml` publishes `site/` to GitHub Pages on every push to
`main`, after checking that the committed data still matches what the tools
produce and that the entries still pass verification. Enable it once under
**Settings → Pages → Source: GitHub Actions**.

## On the text

*Yoga Mala* is copyright © 1999, 2002 by Sri K. Pattabhi Jois, published by
North Point Press, translated by Sri Vishwanath Kadam and Dr. H. L.
Chandrashekar. This repository contains the book's text and photographs. That is
fine for private use; **publishing it is a decision for the rights holders, not
for this repository.** See the note in the conversation that produced this site
before making the Pages site public.
