/* Service worker Pizzeria Pino.
   Deux régimes, parce que deux besoins opposés :
   — les pages doivent être fraîches : réseau d'abord, cache en secours ;
   — polices, photos et icônes ne changent jamais sans changer de nom :
     cache d'abord, zéro attente réseau, et rafraîchissement en arrière-plan. */
var CACHE = 'pino-v264';
var CORE = [
  './', './index.html', './legal.html', './manifest.webmanifest',
  /* Le style vit dans son propre fichier. Sans lui dans cette liste, une page
     servie du cache hors ligne arriverait sans habillage — du texte nu sur
     fond blanc. */
  './styles.css',
  './icons/icon-512.png', './icons/icon-maskable-512.png', './icons/apple-touch-icon.png',
  './favicon.ico', './icons/favicon-48.png', './icons/favicon-96.png', './icons/favicon-192.png',
  './icons/pino-logo.webp', './icons/pino-logo.png',
  './fonts/fraunces-normal-400_700.woff2', './fonts/inter-normal-400.woff2', './fonts/oswald-normal-400.woff2',
  './images/video-poster.webp', './images/hero-feast.webp',
  './images/bg-pates.webp', './images/bg-pizzas.webp', './images/bg-viandes.webp', './images/bg-desserts.webp'
];

/* Un fichier dont le nom porte le contenu : on peut le servir du cache sans
   se demander s'il a changé. Une mise à jour passe par un nouveau CACHE. */
function estFige(url){
  return /\.(woff2|woff|ttf|png|jpe?g|webp|avif|svg|ico|mp4|webm)$/i.test(url.pathname);
}

function metEnCache(req, res){
  if(res && res.status === 200 && res.type === 'basic'){
    var copie = res.clone();
    caches.open(CACHE).then(function(c){ c.put(req, copie); });
  }
  return res;
}

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
  if(url.origin !== self.location.origin) return; /* laisser les tiers (Google Maps, Supabase…) */

  /* Ressources figées : on répond depuis le cache immédiatement. */
  if(estFige(url)){
    e.respondWith(
      caches.match(req).then(function(m){
        if(m){
          /* On vérifie quand même, sans faire attendre personne. */
          fetch(req).then(function(res){ metEnCache(req, res); }).catch(function(){});
          return m;
        }
        return fetch(req).then(function(res){ return metEnCache(req, res); });
      })
    );
    return;
  }

  /* Pages et reste : réseau d'abord, pour ne jamais servir une carte périmée. */
  e.respondWith(
    fetch(req).then(function(res){ return metEnCache(req, res); })
      .catch(function(){
        return caches.match(req).then(function(m){ return m || caches.match('./index.html'); });
      })
  );
});
