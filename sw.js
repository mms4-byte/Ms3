// اسم الكاش
const CACHE_NAME = 'six-pro-cache-v1';

// الملفات التي سيتم تخزينها في الكاش
const urlsToCache = [
  'index.html',
  'manifest.json',
  'https://iili.io/fbckoRn.md.jpg' // صورة الأيقونة من Imgur
];

// عند التثبيت: نحفظ الملفات في الكاش
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(urlsToCache);
    })
  );
  self.skipWaiting();
});

// عند التفعيل: نحذف أي كاش قديم
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((name) => {
          if (name !== CACHE_NAME) {
            return caches.delete(name);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// عند أي طلب: نرجع الملف من الكاش أولاً ثم من الإنترنت إذا لم يكن موجوداً
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});
