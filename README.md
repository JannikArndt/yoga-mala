# Yoga Mala — an interactive reader

A static site that presents Sri K. Pattabhi Jois's *Yoga Mala* as something you
can practice from: the Surya Namaskara, the asanas in the order he teaches them,
and the eight limbs of Patanjali as he explains them.

The left of each page is the practice, compressed to bullets — one line per
vinyasa, every breath kept. Where the book says "as in the first Surya
Namaskara" or "as in Paschimattanasana", those vinyasas are written out in
place, smaller and fainter, so nothing has to be looked up. The right is what supports it: the plates from the
book, the benefits he gives, and his own sentences where they are worth reading
whole.

## On an iPhone

Open the site in Safari, tap **Share → Add to Home Screen**, and open it from
the new icon once while online. It then runs full screen like an app and keeps
every page and plate on the phone: the contents sheet (☰) says *Saved for
offline reading* once it is ready, and from then on it needs no connection —
only the linked video does. It reopens where you stopped, and when a new
version is published it offers to reload.

Moving around: swipe sideways or use the arrows to turn pages, tap a chapter
or a posture in the strips at the top, or open ☰ to see everything and search
("mari c" finds Marichyasana C). Tap a plate to see it full screen. With a
keyboard: ← and → turn pages, / opens the search.

## The rule the content follows

**Nothing on the site that is not in the book.** Where Guruji names no gazing
point, none is supplied, however standard it has since become. Where he gives no
benefits, the section is absent. Benefits are his exact sentences, shown in
quotation marks — so a claim about disease stays a quotation in his
words rather than being restated as fact. The site does not modernise him,
correct him, or fill his gaps from later Ashtanga sources.

`tools/verify_entries.py` tests that rule mechanically. It always checks the
entries for consistency; with the book unpacked locally it also re-reads every
chapter and flags any entry whose breaths are dropped or out of order, whose
gazing points the chapter does not name, or whose quoted text is not the book's
exact wording. It exits non-zero on any flag.

## Layout

```
site/                  everything that gets deployed
  index.html
  app.js               routing, rendering, contents and search, paging
  styles.css
  sw.js                the offline cache (its file list is generated)
  manifest.webmanifest what makes it installable as an app
  assets/icons/        the mala icon, from tools/build_icons.py
  data/mala.json       the compiled payload the page fetches
  data/entries/*.json  one file per asana or concept — the editable source
  data/images.json     which plate belongs to which entry, with its caption
  data/about.json      the About page
  assets/plates/       the photographs
tools/                 the build and verification scripts
ebook/                 the unpacked EPUB — local only, git-ignored
```

The ebook delivers most plates as photographic negatives. The copies in
`site/assets/plates/` have been turned positive and toned sepia; the five that
were already positive (the cover, the title page, the portrait, and two plates)
were left alone.

## Rebuilding

```sh
python3 tools/build_site_data.py  # entries + images -> data/mala.json, and sw.js's file list
python3 tools/verify_entries.py   # check the entries
```

Run the build after changing *any* file in `site/`, not only the entries: it
stamps `sw.js` with a hash of every cached file, which is how phones that
already have the site learn that there is something new to download.

Reading order and the chapter grouping are declared in `tools/build_site_data.py`.
To correct a posture, edit its file in `site/data/entries/` (the fields are
described in `tools/ENTRY_SCHEMA.md`) and re-run both commands.

To check the entries against the text as well, unpack the EPUB into `ebook/`
(so that `ebook/Text/chapter0006.html` exists), then run
`python3 tools/extract_book.py` before `verify_entries.py`.

Preview locally with `python3 -m http.server 8765 --directory site`.

## Deployment

`.github/workflows/pages.yml` publishes `site/` to GitHub Pages on every push to
`main`, after checking that the committed `mala.json` and `sw.js` still match what
the build produces and that the entries pass verification. Enable it once under
**Settings → Pages → Source: GitHub Actions**.

## Credits

*Yoga Mala* by Sri K. Pattabhi Jois, copyright © 1999, 2002 by Sri K. Pattabhi
Jois, published by North Point Press, a division of Farrar, Straus and Giroux;
translated by Sri Vishwanath Kadam and Dr. H. L. Chandrashekar. Forewords
copyright © 2010 by R. Sharath and by Eddie Stern. Photographs of Sharath
Rangaswamy copyright © 1999 by Stephan Crasneanscki; archival photographs of
Sri K. Pattabhi Jois courtesy of Sri K. Pattabhi Jois.
