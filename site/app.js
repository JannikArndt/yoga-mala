/* Yoga Mala — reader.
   One fetch of data/mala.json, then everything is rendered from that. The URL
   hash is the single source of truth for "where am I", so every way of moving
   through the book (click, arrow key, swipe, contents, back button) goes
   through it. sw.js keeps a copy of every file, so it all works offline. */

const BREATH_MARKS = {
  inhale: { mark: "▲", label: "Inhale", short: "inhale" },
  exhale: { mark: "▼", label: "Exhale", short: "exhale" },
  "inhale-exhale": { mark: "▲▼", label: "Inhale, then exhale", short: "inhale, then exhale" },
  "exhale-inhale": { mark: "▼▲", label: "Exhale, then inhale", short: "exhale, then inhale" },
  free: { mark: "∿", label: "Breathe freely", short: "breathe freely" },
  hold: { mark: "●", label: "Hold", short: "hold" },
};

const LAST_PLACE_KEY = "yoga-mala:last-place";

let book = null;

/* ------------------------------------------------------------------ utils */

const escapeHtml = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (character) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character],
  );

const listOf = (items, className = "points") =>
  items?.length
    ? `<ul class="${className}">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
    : "";

/** Guruji's exact sentences, shown as quotations rather than as facts. */
const quotedListOf = (items, note) =>
  items?.length
    ? listOf(items, "points points--quoted") + (note ? `<p class="section__note">${escapeHtml(note)}</p>` : "")
    : "";

const section = (title, inner) =>
  inner ? `<section class="section"><h2 class="section__title">${escapeHtml(title)}</h2>${inner}</section>` : "";

/** Lower case, no diacritics, letters and digits only: "Śīrṣāsana" finds "shirshasana". */
const searchable = (text) =>
  String(text ?? "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();

/** localStorage can be missing or refuse (private mode); the reader must not care. */
const remember = {
  get: (key) => {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set: (key, value) => {
    try {
      localStorage.setItem(key, value);
    } catch {
      /* not remembered, which is fine */
    }
  },
};

const routeOf = () => location.hash.replace(/^#\/?/, "");

/** The entry currently addressed by the URL, falling back to the first one. */
function currentEntryId() {
  const route = routeOf();
  if (route === "about") return "about";
  return book.entries[route] ? route : book.reading_order[0];
}

function chapterContaining(entryId) {
  for (const part of book.navigation) {
    for (const chapter of part.chapters) {
      if (chapter.entries.includes(entryId)) return { part, chapter };
    }
  }
  return null;
}

/**
 * The title, split so the variant letter never ends up alone on a line:
 * "Prasarita Padottanasana D" keeps "Padottanasana D" together, and the letter
 * is set as a small tag rather than as a word.
 */
function titleHtml(entry, { withNumber = true } = {}) {
  const match = /^(.*?)(?:\s+\(?([A-D])\)?)?$/.exec(entry.title);
  const words = match[1].split(" ");
  const lastWord = words.pop();
  const variant = match[2] ? `<span class="title-variant">${match[2]}</span>` : "";
  const number = withNumber && entry.number ? `<span class="title-number">${entry.number}</span>` : "";
  const head = words.length ? `${escapeHtml(words.join(" "))} ` : "";
  return `${number}${head}<span class="nowrap">${escapeHtml(lastWord)}${variant}</span>`;
}

/** "Seated · 7 of 23": where this page sits, which the title no longer repeats. */
function positionLabel(entryId) {
  const place = chapterContaining(entryId);
  if (!place) return "";
  const index = place.chapter.entries.indexOf(entryId);
  return `${place.chapter.title} · ${index + 1} of ${place.chapter.entries.length}`;
}

/* ------------------------------------------------------------ navigation */

function renderChapterNav(activeChapterId) {
  document.getElementById("chapter-nav").innerHTML = book.navigation
    .map(
      (part) => `
      <div class="part">
        <span class="part__label">${escapeHtml(part.subtitle)}</span>
        ${part.chapters
          .map(
            (chapter) => `
          <a class="chapter-link" href="#/${escapeHtml(chapter.entries[0])}"
             aria-current="${chapter.id === activeChapterId}">${escapeHtml(chapter.title)}</a>`,
          )
          .join("")}
      </div>`,
    )
    .join("");

  // On a narrow screen the tabs scroll sideways; keep the current one in view.
  centreActiveLink(document.getElementById("chapter-nav"));
}

/** Scroll a sideways strip so its current link sits in the middle. */
function centreActiveLink(strip) {
  const active = strip.querySelector('[aria-current="true"]');
  if (!active) return;
  const stripBox = strip.getBoundingClientRect();
  const linkBox = active.getBoundingClientRect();
  const offset = strip.scrollLeft + linkBox.left - stripBox.left - (stripBox.width - linkBox.width) / 2;
  strip.scrollTo({ left: Math.max(0, offset), behavior: "smooth" });
}

function renderEntryNav(chapter, activeEntryId) {
  const nav = document.getElementById("entry-nav");
  // The About page belongs to no chapter, so the strip is hidden rather than
  // left as an empty band.
  nav.hidden = !chapter;
  if (!chapter) {
    nav.innerHTML = "";
    return;
  }
  nav.innerHTML = chapter.entries
    .map((entryId) => {
      const entry = book.entries[entryId];
      const number = entry.number ? `<span class="entry-link__number">${entry.number}</span>` : "";
      return `<a class="entry-link" href="#/${escapeHtml(entryId)}"
                 aria-current="${entryId === activeEntryId}">${number}${escapeHtml(entry.title)}</a>`;
    })
    .join("");

  // Keep the current posture visible in the strip without scrolling the page.
  centreActiveLink(nav);
}

function renderPager(entryId) {
  const position = book.reading_order.indexOf(entryId);
  const previousId = book.reading_order[position - 1];
  const nextId = position < 0 ? undefined : book.reading_order[position + 1];
  const previous = document.getElementById("previous");
  const next = document.getElementById("next");
  previous.disabled = !previousId || position < 0;
  next.disabled = !nextId;
  previous.setAttribute("aria-label", previousId && position >= 0 ? `Previous: ${book.entries[previousId].title}` : "Previous");
  next.setAttribute("aria-label", nextId ? `Next: ${book.entries[nextId].title}` : "Next");

  // At the foot of the page, name where the arrows go.
  const turn = document.getElementById("turn");
  const link = (id, direction) =>
    id
      ? `<a class="turn__link turn__link--${direction}" href="#/${escapeHtml(id)}">
           <span class="turn__label">${direction === "previous" ? "← Previous" : "Next →"}</span>
           <span class="turn__title">${titleHtml(book.entries[id])}</span>
         </a>`
      : `<span></span>`;
  turn.hidden = position < 0;
  turn.innerHTML = position < 0 ? "" : link(previousId, "previous") + link(nextId, "next");
}

/* --------------------------------------------------------------- fragments */

function renderPlates(images, className = "plates") {
  if (!images?.length) return "";
  const many = images.length > 1 ? ` ${className}--many` : "";
  const figures = images
    .map(
      (image) => `
      <figure class="plate">
        <button class="plate__open" type="button" aria-label="Enlarge: ${escapeHtml(image.caption || "plate")}">
          <img src="assets/plates/${escapeHtml(image.file)}" alt="${escapeHtml(image.caption || "Plate from Yoga Mala")}" loading="lazy" decoding="async">
        </button>
        ${image.caption ? `<figcaption>${escapeHtml(image.caption)}</figcaption>` : ""}
      </figure>`,
    )
    .join("");
  return `<div class="${className}${many}">${figures}</div>`;
}

function renderVerse(sutra) {
  if (!sutra) return "";
  return `
    <blockquote class="verse">
      ${sutra.sanskrit ? `<p class="verse__sanskrit">${escapeHtml(sutra.sanskrit)}</p>` : ""}
      ${sutra.translation ? `<p class="verse__translation">${escapeHtml(sutra.translation)}</p>` : ""}
      ${sutra.source ? `<cite class="verse__source">${escapeHtml(sutra.source)}</cite>` : ""}
    </blockquote>`;
}

function renderVerses(verses) {
  return (verses || []).map(renderVerse).join("");
}

function renderQuotes(quotes) {
  if (!quotes?.length) return "";
  return quotes.map((quote) => `<p class="quote">${escapeHtml(quote)}</p>`).join("");
}

function renderVideoResource() {
  const video = book.video;
  return `
    <a class="resource" href="${escapeHtml(video.url)}" target="_blank" rel="noopener noreferrer">
      <span class="resource__icon" aria-hidden="true">&#9654;</span>
      <span>
        <span class="resource__title">${escapeHtml(video.title)}</span>
        <span class="resource__note">${escapeHtml(video.note)} &middot; watch the whole series &middot; needs a connection</span>
      </span>
    </a>`;
}

/** Only the marks this asana uses, so the key stays one line. */
function renderBreathKey(sequence) {
  const used = Object.keys(BREATH_MARKS).filter((breath) => sequence?.some((step) => step.breath === breath));
  if (!used.length) return "";
  const items = used
    .map((breath) => `<span><b class="vinyasa__breath--${breath}">${BREATH_MARKS[breath].mark}</b> ${BREATH_MARKS[breath].short}</span>`)
    .join("");
  return `<p class="breath-key" aria-hidden="true">${items}</p>`;
}

function renderSequence(sequence) {
  if (!sequence?.length) return "";
  const rows = sequence
    .map((step) => {
      const breath = BREATH_MARKS[step.breath];
      const breathLabel = breath
        ? escapeHtml(breath.label + (step.breath_as_printed ? ` (${step.breath_as_printed})` : ""))
        : "";
      const breathCell = breath
        ? `<span class="vinyasa__breath vinyasa__breath--${escapeHtml(step.breath)}" role="img"
             aria-label="${breathLabel}" title="${breathLabel}">${breath.mark}</span>`
        : `<span class="vinyasa__breath"></span>`;
      const stateTag = step.is_state ? `<span class="vinyasa__state-tag">state</span>` : "";
      const gaze = step.drishti ? `<span class="vinyasa__gaze">gaze: ${escapeHtml(step.drishti)}</span>` : "";
      return `
        <li class="vinyasa${step.is_state ? " vinyasa--state" : ""}">
          <span class="vinyasa__number">${step.vinyasa ?? ""}</span>
          ${breathCell}
          <p class="vinyasa__action">${escapeHtml(step.action)}${stateTag}${gaze}</p>
        </li>`;
    })
    .join("");
  return `<ul class="vinyasas">${rows}</ul>${renderBreathKey(sequence)}`;
}

/* ------------------------------------------------------------ entry views */

function renderHead(entryId, entry, meta = []) {
  return `
    <div class="entry__head">
      <p class="entry__eyebrow">${escapeHtml(positionLabel(entryId))}</p>
      <h1 class="entry__title">${titleHtml(entry)}</h1>
      ${meta.length ? `<div class="entry__meta">${meta.join("")}</div>` : ""}
    </div>`;
}

/**
 * Three regions rather than two columns: on a phone the plates come first,
 * because you look at a posture before you read it.
 */
function renderBody(main, plates, support) {
  return `
    <div class="entry__body">
      ${plates ? `<div class="entry__plates">${plates}</div>` : ""}
      <div class="entry__main">${main}</div>
      <div class="entry__support">${support}</div>
    </div>`;
}

function renderAsana(entryId, entry) {
  const meta = [];
  if (entry.vinyasa_label) meta.push(`<span>vinyasas: <b>${escapeHtml(entry.vinyasa_label)}</b></span>`);
  else if (entry.vinyasa_count) meta.push(`<span><b>${entry.vinyasa_count}</b> vinyasas</span>`);
  if (entry.state_label) meta.push(`<span>state: <b>${escapeHtml(entry.state_label)}</b></span>`);
  else if (entry.state_vinyasas?.length)
    meta.push(`<span>state: <b>${entry.state_vinyasas.join(", ")}</b></span>`);
  if (entry.drishti) meta.push(`<span>drishti: <b>${escapeHtml(entry.drishti)}</b></span>`);

  const main = [
    section("Method", renderSequence(entry.sequence)),
    section("While holding", listOf(entry.while_holding)),
    section("Cautions", quotedListOf(entry.cautions)),
    section("Notes", listOf(entry.notes)),
  ].join("");

  const support = [
    section("Benefits, in Guruji's words", quotedListOf(entry.benefits, entry.benefits_source)),
    section("In Guruji's words", renderQuotes(entry.quotes)),
    section("Scripture he quotes", renderVerses(entry.verses)),
    section("Watch", renderVideoResource()),
  ].join("");

  return renderHead(entryId, entry, meta) + renderBody(main, renderPlates(entry.images), support);
}

function renderConcept(entryId, entry) {
  const main = [
    entry.one_line ? `<p class="lead">${escapeHtml(entry.one_line)}</p>` : "",
    listOf(entry.points),
  ].join("");

  const support = [
    section("Scripture", renderVerse(entry.sutra) + renderVerses(entry.verses)),
    section("In Guruji's words", renderQuotes(entry.quotes)),
  ].join("");

  return renderHead(entryId, entry) + renderBody(main, renderPlates(entry.images), support);
}

function renderAbout() {
  const about = book.about;
  const portrait = book.portrait?.[0];
  if (!about) return `<h1 class="entry__title">Guruji</h1>`;

  return `
    <div class="about">
      <div class="entry__head">
        <p class="entry__eyebrow">${escapeHtml(about.guruji?.dates || "")}</p>
        <h1 class="entry__title">${escapeHtml(about.guruji?.name || "Sri K. Pattabhi Jois")}</h1>
      </div>
      ${portrait ? `<img class="about__portrait" src="assets/plates/${escapeHtml(portrait.file)}" alt="${escapeHtml(portrait.caption)}">` : ""}
      ${section(
        "His life",
        listOf(about.guruji?.life) +
          (about.guruji?.life_source ? `<p class="section__note">${escapeHtml(about.guruji.life_source)}</p>` : ""),
      )}
      ${(about.forewords || [])
        .map((foreword) => section(`From ${foreword.author}'s foreword`, renderQuotes(foreword.quotes)))
        .join("")}
      ${about.dedication ? `<p class="about__dedication">${escapeHtml(about.dedication)}</p>` : ""}
      ${section("Why he wrote this book", listOf(about.preface?.summary) + renderQuotes(about.preface?.quotes))}
      ${section("The blessing of Shringeri", (about.blessing?.summary ? `<p>${escapeHtml(about.blessing.summary)}</p>` : "") + renderQuotes(about.blessing?.quotes))}
      ${section("Photographs", renderPlates(book.gallery))}
      ${section("Acknowledgments", about.acknowledgments ? `<p>${escapeHtml(about.acknowledgments)}</p>` : "")}
    </div>`;
}

/* ------------------------------------------------------------------ render */

function render() {
  const entryId = currentEntryId();
  // An unknown address shows the first entry; say so in the URL too.
  if (entryId !== routeOf()) history.replaceState(null, "", `#/${entryId}`);
  remember.set(LAST_PLACE_KEY, entryId);
  const entryElement = document.getElementById("entry");

  if (entryId === "about") {
    renderChapterNav(null);
    renderEntryNav(null, null);
    renderPager("about");
    document.querySelector(".masthead__about").setAttribute("aria-current", "page");
    entryElement.innerHTML = renderAbout();
    document.title = "Guruji — Yoga Mala";
  } else {
    const entry = book.entries[entryId];
    const place = chapterContaining(entryId);
    renderChapterNav(place?.chapter.id);
    renderEntryNav(place?.chapter, entryId);
    renderPager(entryId);
    document.querySelector(".masthead__about").removeAttribute("aria-current");
    entryElement.innerHTML = entry.kind === "concept" ? renderConcept(entryId, entry) : renderAsana(entryId, entry);
    document.title = `${entry.title} — Yoga Mala`;
  }

  markCurrentInContents(entryId);
  window.scrollTo({ top: 0, behavior: "auto" });
}

function goTo(entryId) {
  if (entryId) location.hash = `#/${entryId}`;
}

function step(direction) {
  const position = book.reading_order.indexOf(currentEntryId());
  if (position < 0) return;
  goTo(book.reading_order[position + direction]);
}

/* -------------------------------------------------------- contents and search */

function renderContents() {
  const parts = book.navigation
    .map(
      (part) => `
      <section class="toc__part">
        <h2 class="toc__part-title">${escapeHtml(part.subtitle)} · ${escapeHtml(part.title)}</h2>
        ${part.chapters
          .map(
            (chapter) => `
          <div class="toc__chapter">
            <h3 class="toc__chapter-title">${escapeHtml(chapter.title)}</h3>
            <ul class="toc__list">
              ${chapter.entries
                .map((entryId) => {
                  const entry = book.entries[entryId];
                  const terms = searchable(`${entry.title} ${entry.number ?? ""} ${chapter.title}`);
                  return `
                  <li data-search="${escapeHtml(terms)}">
                    <a class="toc__link" href="#/${escapeHtml(entryId)}" data-entry="${escapeHtml(entryId)}">
                      <span class="toc__number">${entry.number ?? ""}</span>
                      <span>${titleHtml(entry, { withNumber: false })}</span>
                    </a>
                  </li>`;
                })
                .join("")}
            </ul>
          </div>`,
          )
          .join("")}
      </section>`,
    )
    .join("");
  const about = `
    <section class="toc__part">
      <ul class="toc__list">
        <li data-search="guruji pattabhi jois about life foreword preface">
          <a class="toc__link" href="#/about" data-entry="about"><span class="toc__number"></span><span>Guruji — his life and this book</span></a>
        </li>
      </ul>
    </section>`;
  document.getElementById("contents-list").innerHTML =
    parts + about + `<p class="toc__empty" hidden>Nothing matches.</p>`;
}

function markCurrentInContents(entryId) {
  document.querySelectorAll("#contents-list .toc__link").forEach((link) => {
    if (link.dataset.entry === entryId) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
}

/** Every word typed must begin a word of the entry: "mari c" finds Marichyasana C only. */
function filterContents(query) {
  const words = searchable(query).split(" ").filter(Boolean);
  const list = document.getElementById("contents-list");
  let shown = 0;
  list.querySelectorAll("li[data-search]").forEach((item) => {
    const terms = item.dataset.search.split(" ");
    const match = words.every((word) => terms.some((term) => term.startsWith(word)));
    item.hidden = !match;
    if (match) shown += 1;
  });
  // Hide headings whose every entry is filtered out.
  list.querySelectorAll(".toc__chapter, .toc__part").forEach((group) => {
    group.hidden = !group.querySelector("li[data-search]:not([hidden])");
  });
  list.querySelector(".toc__empty").hidden = shown > 0;
}

function openContents() {
  const dialog = document.getElementById("contents");
  if (dialog.open) return;
  const search = document.getElementById("search");
  search.value = "";
  filterContents("");
  dialog.showModal();
  const current = dialog.querySelector('[aria-current="page"]');
  current?.scrollIntoView({ block: "center" });
  // A keyboard opens it to type; a finger opens it to browse, and focusing
  // the field would throw the iPhone keyboard over the list.
  if (matchMedia("(hover: hover)").matches) search.focus();
}

/* ------------------------------------------------------------ plate viewer */

function openPlate(image) {
  const viewer = document.getElementById("viewer");
  const img = document.getElementById("viewer-image");
  img.src = image.getAttribute("src");
  img.alt = image.alt;
  document.getElementById("viewer-caption").textContent = image.closest("figure")?.querySelector("figcaption")?.textContent || "";
  viewer.showModal();
}

/* ---------------------------------------------------------------- controls */

function isTyping(target) {
  return target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement;
}

function attachControls() {
  // The skip link targets #entry, which the router would read as a route.
  document.querySelector(".skip-link").addEventListener("click", (event) => {
    event.preventDefault();
    document.getElementById("entry").focus();
  });

  document.getElementById("previous").addEventListener("click", () => step(-1));
  document.getElementById("next").addEventListener("click", () => step(1));

  window.addEventListener("hashchange", () => {
    render();
    // Move keyboard and screen-reader focus to the new page, as a link would.
    document.getElementById("entry").focus({ preventScroll: true });
  });

  // Contents: open, search, and close once a place is chosen.
  const contents = document.getElementById("contents");
  document.getElementById("open-contents").addEventListener("click", openContents);
  document.getElementById("search").addEventListener("input", (event) => filterContents(event.target.value));
  document.getElementById("search").addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    const first = contents.querySelector("li[data-search]:not([hidden]) a");
    if (first) {
      event.preventDefault();
      first.click();
    }
  });
  contents.addEventListener("click", (event) => {
    if (event.target.closest(".toc__link") || event.target.closest("[data-close]") || event.target === contents) {
      contents.close();
    }
  });

  // Plates open full screen; any tap closes them again.
  const viewer = document.getElementById("viewer");
  document.getElementById("entry").addEventListener("click", (event) => {
    const button = event.target.closest(".plate__open");
    if (button) openPlate(button.querySelector("img"));
  });
  viewer.addEventListener("click", () => viewer.close());

  document.addEventListener("keydown", (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey || isTyping(event.target)) return;
    if (contents.open || viewer.open) return;
    if (event.key === "ArrowLeft") step(-1);
    if (event.key === "ArrowRight") step(1);
    if (event.key === "/") {
      event.preventDefault();
      openContents();
    }
  });

  // Horizontal swipe pages the book; vertical scrolling must stay untouched.
  let touchStartX = 0;
  let touchStartY = 0;
  let swipeIgnored = false;
  document.addEventListener(
    "touchstart",
    (event) => {
      const touch = event.changedTouches[0];
      // The strips scroll sideways, the dialogs are their own world, and a
      // swipe from the very edge of the screen is the system's back gesture.
      swipeIgnored =
        event.touches.length > 1 ||
        Boolean(event.target.closest?.(".chapters, .entries, dialog")) ||
        touch.clientX < 24 ||
        touch.clientX > window.innerWidth - 24;
      touchStartX = touch.clientX;
      touchStartY = touch.clientY;
    },
    { passive: true },
  );
  document.addEventListener(
    "touchend",
    (event) => {
      if (swipeIgnored) return;
      const deltaX = event.changedTouches[0].clientX - touchStartX;
      const deltaY = event.changedTouches[0].clientY - touchStartY;
      if (Math.abs(deltaX) > 60 && Math.abs(deltaX) > Math.abs(deltaY) * 1.5) {
        step(deltaX < 0 ? 1 : -1);
      }
    },
    { passive: true },
  );
}

/* ----------------------------------------------------------------- offline */

let offlineMessage = "";

function setOfflineStatus(message) {
  offlineMessage = message;
  document.querySelectorAll(".offline-status, #offline-status").forEach((element) => {
    element.textContent = message;
  });
}

function registerOffline() {
  if (!("serviceWorker" in navigator)) {
    setOfflineStatus("This browser cannot keep the book for offline reading.");
    return;
  }
  // Only a page that already had a worker is being updated; on the very first
  // visit the new worker takes over silently.
  const hadController = Boolean(navigator.serviceWorker.controller);
  let updateRequested = false;
  const notice = document.getElementById("update-notice");
  const offerUpdate = (worker) => {
    notice.hidden = false;
    document.getElementById("apply-update").onclick = () => {
      updateRequested = true;
      worker.postMessage("skip-waiting");
    };
  };

  setOfflineStatus(hadController ? "Saved for offline reading." : "Saving the book for offline reading…");
  navigator.serviceWorker
    .register("sw.js")
    .then((registration) => {
      if (registration.waiting && hadController) offerUpdate(registration.waiting);
      registration.addEventListener("updatefound", () => {
        const worker = registration.installing;
        worker?.addEventListener("statechange", () => {
          if (worker.state === "installed" && navigator.serviceWorker.controller) offerUpdate(worker);
        });
      });
      // A home-screen app can stay open for days; look for a new version
      // whenever it comes back to the front.
      document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") registration.update().catch(() => {});
      });
    })
    .catch(() => setOfflineStatus("The book could not be saved for offline reading."));

  navigator.serviceWorker.ready.then(() => setOfflineStatus("Saved for offline reading — works without a connection."));

  let reloading = false;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (!(hadController || updateRequested) || reloading) return;
    reloading = true;
    location.reload();
  });
}

function renderColophon() {
  const copyright = book.about?.copyright;
  document.getElementById("colophon").innerHTML = `
    <p>The practice on this site is summarised from Sri K. Pattabhi Jois's <i>Yoga Mala</i>; passages in quotation marks are quoted from the book.</p>
    ${copyright?.notice ? `<p>${escapeHtml(copyright.notice)}${copyright.publisher ? ` &middot; ${escapeHtml(copyright.publisher)}` : ""}</p>` : ""}
    ${copyright?.translator ? `<p>Translated by ${escapeHtml(copyright.translator)}.</p>` : ""}
    ${copyright?.forewords ? `<p>${escapeHtml(copyright.forewords)}.</p>` : ""}
    ${copyright?.photographs ? `<p>${escapeHtml(copyright.photographs)}.</p>` : ""}
    <p>This reader is offered in gratitude, not in place of a teacher.</p>
    <p class="offline-status">${escapeHtml(offlineMessage)}</p>`;
}

async function start() {
  registerOffline();
  try {
    const response = await fetch("data/mala.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    book = await response.json();
  } catch (error) {
    document.getElementById("entry").innerHTML =
      `<p class="lead">The book could not be loaded (${escapeHtml(error.message)}). Please reload the page.</p>`;
    return;
  }

  // Opened from the home screen with no address: carry on where you stopped.
  const lastPlace = remember.get(LAST_PLACE_KEY);
  if (!routeOf() && lastPlace && (lastPlace === "about" || book.entries[lastPlace])) {
    history.replaceState(null, "", `#/${lastPlace}`);
  }

  attachControls();
  renderContents();
  renderColophon();
  render();
}

start();
