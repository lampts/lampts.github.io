const CACHE_NAME = 'inkflow-v2';
const ASSETS = [
  './tao.html',
  './manifest.json'
];

// External CDN assets to cache
const CDN_ASSETS = [
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Roboto+Mono:wght@400;500&display=swap',
  'https://cdnjs.cloudflare.com/ajax/libs/qrcode-generator/1.4.4/qrcode.min.js'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        // Cache local assets
        cache.addAll(ASSETS);
        // Cache CDN assets (fail silently if unavailable)
        return Promise.allSettled(
          CDN_ASSETS.map(url =>
            fetch(url).then(res => cache.put(url, res)).catch(() => {})
          )
        );
      })
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter(name => name !== CACHE_NAME)
          .map(name => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // Skip API calls
  if (request.url.includes('generativelanguage.googleapis.com')) {
    return;
  }

  event.respondWith(
    caches.match(request)
      .then((cached) => {
        // Cache-first for local assets, network-first for CDN
        if (cached) return cached;

        return fetch(request)
          .then((response) => {
            // Cache successful responses
            if (response.ok) {
              const clone = response.clone();
              caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
            }
            return response;
          })
          .catch(() => {
            // Offline fallback for HTML
            if (request.headers.get('accept')?.includes('text/html')) {
              return caches.match('./tao.html');
            }
          });
      })
  );
});
