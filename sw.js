/* Deep Signal service worker.
   Bump CACHE_VERSION on every deploy — the old cache is dropped on activate. */
const CACHE_VERSION = "deep-signal-v2";

/* Relative so the app works from a project subpath (e.g. /deep-signal/ on Pages). */

/* Without these the app cannot open offline at all. addAll is all-or-nothing,
   so a partial fetch (stale CDN edge mid-deploy, hall wifi dropping) rejects
   the install and the browser retries on the next visit — rather than leaving
   a silently half-built cache that never self-heals. */
const CRITICAL = [
  "./",
  "./index.html",
  "./manifest.webmanifest"
];

/* Nice to have. A missing icon is a cosmetic problem, not an offline one, so
   these are best-effort and must not fail the install. */
const OPTIONAL = [
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/icon-maskable-512.png",
  "./icons/icon-180.png"
];

self.addEventListener("install", e => {
  e.waitUntil((async () => {
    const cache = await caches.open(CACHE_VERSION);
    await cache.addAll(CRITICAL);
    await Promise.all(OPTIONAL.map(u => cache.add(u).catch(() => {})));
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", e => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k !== CACHE_VERSION).map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;   // never touch cross-origin

  // Navigations (including a QR hit like ?site=WRECK) — network first so a
  // redeploy is picked up, cached shell when the hall wifi isn't there.
  if (req.mode === "navigate") {
    e.respondWith((async () => {
      try {
        const fresh = await fetch(req);
        const cache = await caches.open(CACHE_VERSION);
        cache.put("./index.html", fresh.clone());
        return fresh;
      } catch (err) {
        const cache = await caches.open(CACHE_VERSION);
        return (await cache.match("./index.html")) ||
               (await cache.match("./", { ignoreSearch: true })) ||
               Response.error();
      }
    })());
    return;
  }

  // Static assets — cache first, refresh in the background.
  e.respondWith((async () => {
    const cache = await caches.open(CACHE_VERSION);
    const hit = await cache.match(req, { ignoreSearch: true });
    const net = fetch(req).then(res => {
      if (res && res.ok) cache.put(req, res.clone());
      return res;
    }).catch(() => null);
    return hit || (await net) || Response.error();
  })());
});
