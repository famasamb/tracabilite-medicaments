// Service worker: l'application s'ouvre même sans réseau (coque de l'application seulement).
// Les appels à l'API ne sont jamais mis en cache. Le mode hors ligne des opérations viendra plus tard.
const VERSION = "v11";
const COQUE = ["./", "app.css", "app.js", "manifest.webmanifest", "icons/icone.svg",
  "fonts/geist-latin-wght-normal.woff2", "fonts/geist-mono-latin-wght-normal.woff2"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(COQUE)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((cles) => Promise.all(cles.filter((c) => c !== VERSION).map((c) => caches.delete(c))))
    .then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin || !url.pathname.startsWith("/mobile/")) return;
  // Réseau d'abord (toujours la dernière version), cache en secours
  e.respondWith(fetch(e.request).then((r) => {
    const copie = r.clone();
    caches.open(VERSION).then((c) => c.put(e.request, copie));
    return r;
  }).catch(() => caches.match(e.request).then((r) => r || caches.match("./"))));
});
