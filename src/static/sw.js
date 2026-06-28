const CACHE = 'pixstruct-v1';
const STATIC = ['/', '/static/index.html'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC)));
});

self.addEventListener('fetch', e => {
  // For API calls (/extract, /bills) — network first, no cache
  if (e.request.url.includes('/extract') || e.request.url.includes('/bills')) {
    e.respondWith(fetch(e.request));
    return;
  }
  // For static assets — cache first
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  );
});