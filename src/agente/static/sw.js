const CACHE_NAME = "nexus-agent-v1";
self.addEventListener("install", (e) => {
  self.skipWaiting();
});
self.addEventListener("activate", (e) => {
  e.waitUntil(self.clients.claim());
});
self.addEventListener("fetch", (e) => {
  // Pass through to network
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});
