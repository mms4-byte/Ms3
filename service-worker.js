const CACHE_NAME = 'six-pro-v1';
const urlsToCache = [
  '/',
  '/index.html',
  '/tasks.html',
  '/math.html',
  '/english.html',
  '/schedule.html',
  '/stats.html',
  '/profile.html',
  '/manifest.json',
  'https://cdn.tailwindcss.com',
  'https://cdn.jsdelivr.net/npm/feather-icons/dist/feather.min.js',
  'https://unpkg.com/feather-icons',
  'https://fonts.googleapis.com/css2?family=Tajawal:wght@200;300;400;500;700;800;900&display=swap',
  'https://i.imgur.com/1l3hICE.jpg'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});