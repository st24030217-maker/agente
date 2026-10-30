const CACHE_NAME = "sebax-wa-fixed-v18";

self.addEventListener("install", (e) => {
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((k) => caches.delete(k))
      );
    }).then(() => self.clients.claim())
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

  // Assets estaticos: red primero, cache como respaldo si existe
  e.respondWith(
    fetch(e.request).catch(async () => {
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
