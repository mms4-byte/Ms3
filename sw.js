// اسم الكاش المحدث
const CACHE_NAME = 'six-pro-royal-v2';

// الملفات الأساسية للتشغيل أوفلاين
const urlsToCache = [
  './',
  'index.html',
  'manifest.json',
  'https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap',
  'https://fonts.googleapis.com/icon?family=Material+Icons',
  'https://cdn.tailwindcss.com',
  'https://iili.io/fbckoRn.md.jpg' 
];

// عند التثبيت
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('تم فتح الكاش الملكي');
      return cache.addAll(urlsToCache);
    })
  );
  self.skipWaiting();
});

// عند التفعيل (حذف الكاش القديم فوراً)
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            console.log('تم حذف الكاش القديم');
            return caches.delete(cache);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// استراتيجية (الإنترنت أولاً) لضمان ظهور التحديثات التصميمية فوراً
self.addEventListener('fetch', (event) => {
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // إذا نجح الطلب، نحفظ نسخة منه في الكاش ونرجعه
        if (event.request.method === 'GET') {
          const resClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, resClone);
          });
        }
        return response;
      })
      .catch(() => {
        // في حال انقطاع الإنترنت، نستخدم الكاش
        return caches.match(event.request);
      })
  );
});
