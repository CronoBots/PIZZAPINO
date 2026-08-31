/* Service worker Pizzeria Pino — réseau d'abord, cache en secours (hors-ligne). */
var CACHE = 'pino-v212';
var CORE = [
  './', './index.html', './legal.html', './manifest.webmanifest',
  './icons/icon-512.png', './icons/icon-maskable-512.png', './icons/apple-touch-icon.png', './icons/pino-logo.png',
  './fonts/fraunces-normal-400_700.woff2', './fonts/inter-normal-400.woff2', './fonts/oswald-normal-400.woff2',
  './images/hero-feast.webp',
  './images/bg-pates.webp', './images/bg-pizzas.webp', './images/bg-viandes.webp', './images/bg-desserts.webp'
];

self.addEventListener('install', function(e){
  e.waitUntil(
    caches.open(CACHE).then(function(c){
      return Promise.all(CORE.map(function(u){ return c.add(u).catch(function(){}); }));
    }).then(function(){ return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function(e){
  e.waitUntil(
    caches.keys().then(function(keys){
      return Promise.all(keys.map(function(k){ if(k !== CACHE) return caches.delete(k); }));
    }).then(function(){ return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function(e){
  var req = e.request;
  if(req.method !== 'GET') return;
  var url;
  try{ url = new URL(req.url); }catch(err){ return; }
  if(url.origin !== self.location.origin) return; /* laisser les tiers (Google Maps, etc.) */

  e.respondWith(
    fetch(req).then(function(res){
      if(res && res.status === 200 && res.type === 'basic'){
        var copy = res.clone();
        caches.open(CACHE).then(function(c){ c.put(req, copy); });
      }
      return res;
    }).catch(function(){
      return caches.match(req).then(function(m){
        if(m) return m;
        /* Ne jamais renvoyer la page HTML à la place d'un média : l'élément <video>/<img>
           recevrait un document et échouerait en silence. Mieux vaut une vraie erreur réseau,
           le poster / la photo de repli prend alors le relais. */
        var media = req.destination === 'video' || req.destination === 'audio' || req.destination === 'image' ||
                    /\.(mp4|webm|ogg|mp3|jpe?g|png|webp|avif|svg|woff2?)$/i.test(url.pathname);
        return media ? Response.error() : caches.match('./index.html');
      });
    })
  );
});
