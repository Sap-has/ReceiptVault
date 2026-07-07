const CACHE_NAME = 'receipt-ocr-v1';
// Add any core CSS or JS files you want cached so the UI loads instantly
const ASSETS = [
  '/',
  '/static/css/style.css', 
  '/manifest.json'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS))
  );
});

self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then(res => res || fetch(e.request))
  );
});