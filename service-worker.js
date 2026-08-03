const CACHE_NAME = 'jf-apps-pwa-v2-uniformisation';

const STATIC_ASSETS = [
  '/manifest.webmanifest',
  '/offline.html',
  '/assets/logo_jf.png',
  '/assets/favicon-32.png',
  '/assets/favicon-64.png',
  '/assets/pwa-icon-192.png',
  '/assets/pwa-icon-512.png',
  '/assets/pwa-icon-maskable-512.png',
  '/assets/apple-touch-icon.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;

  if (request.method !== 'GET') {
    return;
  }

  const url = new URL(request.url);

  if (url.origin !== self.location.origin) {
    return;
  }

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match('/offline.html'))
    );
    return;
  }

  if (STATIC_ASSETS.includes(url.pathname)) {
    event.respondWith(
      caches
        .match(request)
        .then((cached) => cached || fetch(request))
    );
  }
});
