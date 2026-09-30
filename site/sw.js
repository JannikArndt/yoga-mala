/* Yoga Mala — offline support.
   Every file the reader needs is cached when the service worker installs, so
   once the site has been opened online it works with no connection at all.
   The block between the markers is written by tools/build_offline.py: the
   version is a hash of the files, so any change to them installs a new cache. */

// BEGIN GENERATED
const VERSION = "d6acd2aaab7f";
const FILES = [
  "app.js",
  "assets/icons/apple-touch-icon.png",
  "assets/icons/favicon-32.png",
  "assets/icons/favicon.svg",
  "assets/icons/icon-192.png",
  "assets/icons/icon-512.png",
  "assets/icons/icon-maskable-512.png",
  "assets/plates/image-11TUHUIM.jpg",
  "assets/plates/image-1MQF7HA7.jpg",
  "assets/plates/image-1RHOOE4S.jpg",
  "assets/plates/image-1YFB5ZHP.jpg",
  "assets/plates/image-2192JZLU.jpg",
  "assets/plates/image-2GPC79M3.jpg",
  "assets/plates/image-2VITAN9E.jpg",
  "assets/plates/image-4CEN357L.jpg",
  "assets/plates/image-4M1R870S.jpg",
  "assets/plates/image-4ZRO5IP0.jpg",
  "assets/plates/image-55DMNTM0.jpg",
  "assets/plates/image-58KG1P9U.jpg",
  "assets/plates/image-5WHX1CVC.jpg",
  "assets/plates/image-60JMCA85.jpg",
  "assets/plates/image-6IYBVHVS.jpg",
  "assets/plates/image-7ZAY4OT6.jpg",
  "assets/plates/image-8046DK53.jpg",
  "assets/plates/image-8JZ4UXQ2.jpg",
  "assets/plates/image-8OY2V5KJ.jpg",
  "assets/plates/image-8WWCCSAI.jpg",
  "assets/plates/image-9AQK1Z4X.jpg",
  "assets/plates/image-BF4Y8PWE.jpg",
  "assets/plates/image-D669M2K7.jpg",
  "assets/plates/image-DJO8HEOU.jpg",
  "assets/plates/image-DZBMR226.jpg",
  "assets/plates/image-EWPH0RBP.jpg",
  "assets/plates/image-F13Z0ZEA.jpg",
  "assets/plates/image-FYZHLY6V.jpg",
  "assets/plates/image-GYCRYZ4K.jpg",
  "assets/plates/image-H03207KQ.jpg",
  "assets/plates/image-I69OLZZT.jpg",
  "assets/plates/image-II6Z7F24.jpg",
  "assets/plates/image-IX6RTXXF.jpg",
  "assets/plates/image-IX8DBCJQ.jpg",
  "assets/plates/image-J5C0YN43.jpg",
  "assets/plates/image-JOW7208H.jpg",
  "assets/plates/image-KCLK7QH6.jpg",
  "assets/plates/image-KD71FCAM.jpg",
  "assets/plates/image-KHGGIXTG.jpg",
  "assets/plates/image-LO04RBHP.jpg",
  "assets/plates/image-MAG8XG8V.jpg",
  "assets/plates/image-NCZT8ZWI.jpg",
  "assets/plates/image-NN0YYGR6.jpg",
  "assets/plates/image-ONYBDWYJ.jpg",
  "assets/plates/image-OO1SPJBV.jpg",
  "assets/plates/image-OR6H1YIB.jpg",
  "assets/plates/image-PACRJUEO.jpg",
  "assets/plates/image-PI8UOZYK.jpg",
  "assets/plates/image-Q5RF9VKN.jpg",
  "assets/plates/image-Q8OV7B6U.jpg",
  "assets/plates/image-QVZCIRZR.jpg",
  "assets/plates/image-R2VF65XM.jpg",
  "assets/plates/image-RJVJJRVH.jpg",
  "assets/plates/image-SJ7NCRUQ.jpg",
  "assets/plates/image-SZ6HG0Q9.jpg",
  "assets/plates/image-T39FYO5L.jpg",
  "assets/plates/image-TI5FBO4M.jpg",
  "assets/plates/image-TPS1I8FY.jpg",
  "assets/plates/image-U2YOUK6H.jpg",
  "assets/plates/image-UGG9U65L.jpg",
  "assets/plates/image-V5D2KS3U.jpg",
  "assets/plates/image-V5YUE4GZ.jpg",
  "assets/plates/image-VUG0QN0P.jpg",
  "assets/plates/image-VY90YXVK.jpg",
  "assets/plates/image-W0W2XOKB.jpg",
  "assets/plates/image-W8WAGDFM.jpg",
  "assets/plates/image-XOCO7A4E.jpg",
  "assets/plates/image-Y5LGJ8MH.jpg",
  "assets/plates/image-YO88YP3N.jpg",
  "assets/plates/image-ZFN8G2SO.jpg",
  "data/mala.json",
  "./",
  "manifest.webmanifest",
  "styles.css"
];
// END GENERATED

const CACHE = `yoga-mala-${VERSION}`;

self.addEventListener("install", (event) => {
  // `reload` bypasses the HTTP cache, so a new version never caches stale files.
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.addAll(FILES.map((file) => new Request(file, { cache: "reload" })))),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((key) => key.startsWith("yoga-mala-") && key !== CACHE).map((key) => caches.delete(key))),
      )
      .then(() => self.clients.claim()),
  );
});

// The page asks for this when the reader taps "reload" on the update notice.
self.addEventListener("message", (event) => {
  if (event.data === "skip-waiting") self.skipWaiting();
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET" || new URL(request.url).origin !== self.location.origin) return;

  event.respondWith(
    caches.open(CACHE).then(async (cache) => {
      // Every route is a hash on the one page, so any navigation is index.html.
      const cached = request.mode === "navigate"
        ? await cache.match("./")
        : await cache.match(request, { ignoreSearch: true });
      if (cached) return cached;
      try {
        return await fetch(request);
      } catch (error) {
        if (request.mode === "navigate") return cache.match("./");
        throw error;
      }
    }),
  );
});
