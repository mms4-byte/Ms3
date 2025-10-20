const CACHE_NAME = 'six-pro-v1';
const urlsToCache = [
  '/',
  '/index.html',
  '/manifest.json',
  'https://fonts.googleapis.com/icon?family=Material+Icons',
  'https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;600;700&display=swap',
  '/https://imgur.com/1l3hICE',
  'https://imgur.com/1l3hICE
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('تم فتح الكاش');
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        // إذا وُجد في الكاش، أعد إرساله
        if (response) {
          return response;
        }
        // خلاف ذلك، اطلب من الشبكة
        return fetch(event.request);
      }
    )
  );
});