const CACHE_NAME = "sebax-cloud-wa-v36";

self.addEventListener("install", (e) => {
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((k) => caches.delete(k))
      );
    }).then(() => self.clients.claim()).then(async () => {
      const clients = await self.clients.matchAll({ type: "window" });
      clients.forEach((c) => {
        c.postMessage({ type: "CACHE_PURGED" });
      });
    })
  );
});

self.addEventListener("fetch", (e) => {
  // Las peticiones que no sean GET nunca deben interceptarse por el ServiceWorker
  if (e.request.method !== "GET") {
    return;
  }

  const url = new URL(e.request.url);
  if (
    url.pathname.startsWith("/api/") ||
    url.pathname.startsWith("/qr") ||
    url.pathname.startsWith("/pairing-code") ||
    url.pathname.startsWith("/health") ||
    url.pathname.startsWith("/webhook")
  ) {
    return;
  }

  // Siempre solicitar contenido fresco al servidor sin caché
  e.respondWith(
    fetch(e.request, { cache: "no-store" }).catch(async () => {
      const match = await caches.match(e.request);
      if (match) {
        return match;
      }
      return new Response("Contenido no disponible sin conexion", {
        status: 503,
        statusText: "Offline",
        headers: { "Content-Type": "text/plain; charset=utf-8" }
      });
    })
  );
});
