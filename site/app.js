/* Yoga Mala — reader.
   One fetch of data/mala.json, then everything is rendered from that. The URL
   hash is the single source of truth for "where am I", so every way of moving
   through the book (click, arrow key, swipe, back button) goes through it. */

const BREATH_MARKS = {
  inhale: { mark: "▲", label: "Inhale" },
  exhale: { mark: "▼", label: "Exhale" },
  "inhale-exhale": { mark: "◆", label: "Inhale, then exhale" },
  free: { mark: "∿", label: "Breathe freely" },
  hold: { mark: "●", label: "Hold" },
};

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

const section = (title, inner) =>
  inner ? `<section class="section"><h2 class="section__title">${escapeHtml(title)}</h2>${inner}</section>` : "";

/** The entry currently addressed by the URL, falling back to the first one. */
function currentEntryId() {
  const route = location.hash.replace(/^#\/?/, "");
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

  const active = nav.querySelector('[aria-current="true"]');
  if (active) {
    // Keep the current posture visible in the strip without scrolling the page.
    const offset = active.offsetLeft - nav.clientWidth / 2 + active.clientWidth / 2;
    nav.scrollTo({ left: Math.max(0, offset), behavior: "smooth" });
  }
}

function renderPager(entryId) {
  const position = book.reading_order.indexOf(entryId);
  const previous = document.getElementById("previous");
  const next = document.getElementById("next");
  previous.disabled = position <= 0;
  next.disabled = position < 0 || position >= book.reading_order.length - 1;
  previous.dataset.target = book.reading_order[position - 1] ?? "";
  next.dataset.target = book.reading_order[position + 1] ?? "";
}

/* --------------------------------------------------------------- fragments */

function renderPlates(images) {
  if (!images?.length) return "";
  const many = images.length > 1 ? " plates--many" : "";
  const figures = images
    .map(
      (image) => `
      <figure class="plate">
        <img src="assets/plates/${escapeHtml(image.file)}" alt="${escapeHtml(image.caption || "Plate from Yoga Mala")}" loading="lazy" decoding="async">
        ${image.caption ? `<figcaption>${escapeHtml(image.caption)}</figcaption>` : ""}
      </figure>`,
    )
    .join("");
  return `<div class="plates${many}">${figures}</div>`;
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
        <span class="resource__note">${escapeHtml(video.note)} &middot; watch the whole series</span>
      </span>
    </a>`;
}

function renderSequence(sequence) {
  if (!sequence?.length) return "";
  const rows = sequence
    .map((step) => {
      const breath = BREATH_MARKS[step.breath];
      const breathCell = breath
        ? `<span class="vinyasa__breath vinyasa__breath--${escapeHtml(step.breath)}" title="${escapeHtml(
            breath.label + (step.breath_as_printed ? ` (${step.breath_as_printed})` : ""),
          )}">${breath.mark}</span>`
        : `<span class="vinyasa__breath"></span>`;
      const stateTag = step.is_state ? `<span class="vinyasa__state-tag">state</span>` : "";
      return `
        <li class="vinyasa${step.is_state ? " vinyasa--state" : ""}">
          <span class="vinyasa__number">${step.vinyasa ?? ""}</span>
          ${breathCell}
          <p class="vinyasa__action">${escapeHtml(step.action)}${stateTag}</p>
        </li>`;
    })
    .join("");
  return `<ul class="vinyasas">${rows}</ul>`;
}

/* ------------------------------------------------------------ entry views */

function renderAsana(entry) {
  const meta = [];
  if (entry.vinyasa_count) meta.push(`<span><b>${entry.vinyasa_count}</b> vinyasas</span>`);
  if (entry.state_vinyasas?.length)
    meta.push(`<span>state: <b>${entry.state_vinyasas.join(", ")}</b></span>`);
  if (entry.drishti) meta.push(`<span>drishti: <b>${escapeHtml(entry.drishti)}</b></span>`);

  const left = [
    section("Method", renderSequence(entry.sequence)),
    section("While holding", listOf(entry.while_holding)),
    section("Notes", listOf(entry.notes)),
  ].join("");

  const right = [
    renderPlates(entry.images),
    section("Benefits", listOf(entry.benefits)),
    section("In Guruji's words", renderQuotes(entry.quotes)),
    section("Watch", renderVideoResource()),
  ].join("");

  return `
    <div class="entry__head">
      <p class="entry__eyebrow">${escapeHtml(entry.title_as_printed || "")}</p>
      <h1 class="entry__title">${entry.number ? `<span class="entry__number">${entry.number}</span>` : ""}${escapeHtml(entry.title)}</h1>
      ${meta.length ? `<div class="entry__meta">${meta.join("")}</div>` : ""}
    </div>
    <div class="entry__body"><div>${left}</div><div>${right}</div></div>`;
}

function renderConcept(entry) {
  const left = [
    entry.one_line ? `<p class="lead">${escapeHtml(entry.one_line)}</p>` : "",
    listOf(entry.points),
  ].join("");

  const right = [
    renderPlates(entry.images),
    section("Scripture", renderVerse(entry.sutra)),
    section("In Guruji's words", renderQuotes(entry.quotes)),
  ].join("");

  return `
    <div class="entry__head">
      <p class="entry__eyebrow">Yoga Shastra</p>
      <h1 class="entry__title">${escapeHtml(entry.title)}</h1>
    </div>
    <div class="entry__body"><div>${left}</div><div>${right}</div></div>`;
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
      ${section("His life", listOf(about.guruji?.life))}
      ${section("In his words", renderQuotes(about.guruji?.quotes))}
      ${about.dedication ? `<p class="about__dedication">${escapeHtml(about.dedication)}</p>` : ""}
      ${section("Why he wrote this book", listOf(about.preface?.summary) + renderQuotes(about.preface?.quotes))}
      ${section("The blessing of Shringeri", (about.blessing?.summary ? `<p>${escapeHtml(about.blessing.summary)}</p>` : "") + renderQuotes(about.blessing?.quotes))}
      ${section("The shala", renderPlates(book.gallery))}
      ${section("Acknowledgments", about.acknowledgments ? `<p>${escapeHtml(about.acknowledgments)}</p>` : "")}
    </div>`;
}

/* ------------------------------------------------------------------ render */

function render() {
  const entryId = currentEntryId();
  const entryElement = document.getElementById("entry");

  if (entryId === "about") {
    renderChapterNav(null);
    renderEntryNav(null, null);
    renderPager("about");
    document.querySelector(".masthead__about").setAttribute("aria-current", "page");
    entryElement.innerHTML = renderAbout();
  } else {
    const entry = book.entries[entryId];
    const location_ = chapterContaining(entryId);
    renderChapterNav(location_?.chapter.id);
    renderEntryNav(location_?.chapter, entryId);
    renderPager(entryId);
    document.querySelector(".masthead__about").removeAttribute("aria-current");
    entryElement.innerHTML = entry.kind === "concept" ? renderConcept(entry) : renderAsana(entry);
    document.title = `${entry.title} — Yoga Mala`;
  }

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

/* ---------------------------------------------------------------- controls */

function attachControls() {
  document.getElementById("previous").addEventListener("click", () => step(-1));
  document.getElementById("next").addEventListener("click", () => step(1));

  window.addEventListener("hashchange", render);

  document.addEventListener("keydown", (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    if (event.key === "ArrowLeft") step(-1);
    if (event.key === "ArrowRight") step(1);
  });

  // Horizontal swipe pages the book; vertical scrolling must stay untouched.
  let touchStartX = 0;
  let touchStartY = 0;
  document.addEventListener(
    "touchstart",
    (event) => {
      touchStartX = event.changedTouches[0].clientX;
      touchStartY = event.changedTouches[0].clientY;
    },
    { passive: true },
  );
  document.addEventListener(
    "touchend",
    (event) => {
      const deltaX = event.changedTouches[0].clientX - touchStartX;
      const deltaY = event.changedTouches[0].clientY - touchStartY;
      if (Math.abs(deltaX) > 60 && Math.abs(deltaX) > Math.abs(deltaY) * 1.5) {
        step(deltaX < 0 ? 1 : -1);
      }
    },
    { passive: true },
  );
}

function renderColophon() {
  const copyright = book.about?.copyright;
  document.getElementById("colophon").innerHTML = `
    <p>Every word of the practice on this site is Sri K. Pattabhi Jois's, from <i>Yoga Mala</i>.</p>
    ${copyright?.notice ? `<p>${escapeHtml(copyright.notice)}${copyright.publisher ? ` &middot; ${escapeHtml(copyright.publisher)}` : ""}</p>` : ""}
    ${copyright?.translator ? `<p>Translated by ${escapeHtml(copyright.translator)}.</p>` : ""}
    <p>This reader is offered in gratitude, not in place of a teacher.</p>`;
}

async function start() {
  const response = await fetch("data/mala.json");
  book = await response.json();
  attachControls();
  renderColophon();
  render();
}

start();
