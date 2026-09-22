/* ─────────────────────────────────────────────────────────────────────────────
   Mesure de fréquentation — Pizzeria Pino
   Fonction Edge Supabase. Deux points d'entrée :

     POST  /mesure/e       le site signale un événement
     GET   /mesure/stats   la page /statistiques lit les totaux, clé exigée

   Pourquoi une fonction Edge plutôt qu'un appel direct à la base : la clé
   de service reste ici, côté serveur. La table est fermée à « anon », et
   le mot de passe du tableau de bord est vérifié avant toute lecture. Si
   l'agrégation était exposée au rôle anonyme, n'importe qui lisant le
   JavaScript du site pourrait consulter les chiffres.

   On n'enregistre que des compteurs agrégés : pas de ligne par visiteur,
   pas d'adresse IP conservée, pas de cookie. L'IP sert au plus à situer
   une ville, le temps d'un appel, et n'est jamais écrite.
   ───────────────────────────────────────────────────────────────────────── */

const TYPES = new Set(['vue', 'appel', 'itineraire', 'commande', 'reseau', 'photo', 'pub']);

/* Les départs vers un réseau : le nom du réseau ET l'endroit d'où part le
   clic. Vocabulaire fermé, comme les provenances — on ne veut pas de l'adresse
   cliquée, qui porte le nom du compte et parfois un identifiant de campagne.

   Un clic sur « Suivre » n'est pas un abonné de plus : c'est un visiteur
   envoyé sur la page du compte. Ce qu'il y fait ensuite n'appartient qu'à
   Meta, et n'arrivera jamais ici. */
const PLACES = ['Suivre', 'Profil', 'Publication', 'Reel', 'Contact',
                'Pied de page', 'Crédit photo', 'Autre'];
const RESEAUX = new Set(
  ['Instagram', 'Facebook'].flatMap(r => PLACES.map(p => `${r} · ${p}`)));

/* Le code court d'une publication Instagram, tel qu'il figure dans l'adresse :
   .../reel/DU5_qJLDO6m/. Rien d'autre n'entre sous ce type. */
const PUB = /^[A-Za-z0-9_-]{5,20}$/;

/* La photo agrandie n'arrive ici que par la racine de son fichier. Aucune
   phrase, aucun accent, aucune espace : ce vocabulaire-là ne peut pas servir
   à écrire n'importe quoi en base, et le nom lisible vit dans le site. */
const PHOTO = /^[a-z0-9][a-z0-9-]{0,39}$/;

/* Les robots chargent la page comme un client, mais ne poussent jamais la porte
   du restaurant. Les compter gonfle les totaux et noie les vraies villes : sur
   les premiers jours de mesure, Bruxelles et Zaventem — deux places fortes des
   centres de données — pesaient à elles seules un cinquième des ouvertures. */
const ROBOT = new RegExp([
  'bot', 'crawl', 'spider', 'slurp', 'scrapy', 'curl/', 'wget', 'python-requests',
  'go-http-client', 'okhttp', 'libwww', 'java/', 'axios', 'headlesschrome',
  'phantomjs', 'puppeteer', 'playwright', 'lighthouse', 'pagespeed', 'gtmetrix',
  'pingdom', 'uptime', 'monitoring', 'preview', 'facebookexternalhit', 'embedly',
  'whatsapp', 'telegram', 'discord', 'semrush', 'ahrefs', 'dataforseo',
].join('|'), 'i');

/* Les noms de villes arrivent du service de géolocalisation. On les demande en
   français ; restent quelques exonymes flamands et la périphrase bruxelloise,
   que l'on ramène au nom que le gérant emploierait. */
const EXONYMES: Record<string, string> = {
  'brussels': 'Bruxelles',
  'région de bruxelles-capitale': 'Bruxelles',
  'bruxelles-capitale, région de': 'Bruxelles',
  'brussel': 'Bruxelles',
  'liege': 'Liège',
  'luik': 'Liège',
  'antwerpen': 'Anvers',
  'antwerp': 'Anvers',
  'gent': 'Gand',
  'ghent': 'Gand',
  'brugge': 'Bruges',
  'leuven': 'Louvain',
  'mechelen': 'Malines',
  'kortrijk': 'Courtrai',
  'oostende': 'Ostende',
  'sint-niklaas': 'Saint-Nicolas',
  'doornik': 'Tournai',
  'namen': 'Namur',
  'aarlen': 'Arlon',
  'hoei': 'Huy',
  'bergen': 'Mons',
};
/* D'ou vient le visiteur. Le site ne transmet qu'une de ces cinq etiquettes,
   jamais le referent brut — une adresse porterait le terme cherche ou un
   identifiant de campagne. Le vocabulaire etant ferme, on le verifie ici :
   rien d'autre n'entre en base. */
const SOURCES = new Set(['Google', 'Facebook', 'Instagram', 'Autre site', 'Accès direct']);

const MAX_PLATS = 40;
const MAX_JOURS = 365;

const URL_BASE = Deno.env.get('SUPABASE_URL')!;
const SERVICE  = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const CLE      = Deno.env.get('CLE_TABLEAU') ?? '';
const ORIGINES = (Deno.env.get('ORIGINES') ?? '').split(',').map(s => s.trim()).filter(Boolean);
const GEO      = (Deno.env.get('GEO') ?? 'oui').toLowerCase() !== 'non';

/* ── utilitaires ─────────────────────────────────────────────────────────── */

/** Date du jour en heure de Bruxelles : le restaurant ferme après minuit UTC. */
function jourBruxelles(d = new Date()): string {
  return new Intl.DateTimeFormat('fr-CA', {
    timeZone: 'Europe/Brussels', year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(d);
}

/** Un libellé propre : ni balise, ni saut de ligne, longueur bornée. */
function nettoie(v: unknown, max = 60): string {
  return String(v).replace(/[\x00-\x1f<>]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, max);
}

/** Le support, déduit des en-têtes, jamais stocké tel quel. */
function support(req: Request): string {
  const mobile = req.headers.get('sec-ch-ua-mobile');
  const ua = (req.headers.get('user-agent') ?? '').toLowerCase();
  if (/ipad|tablet|playbook|silk|(android(?!.*mobile))/.test(ua)) return 'Tablette';
  if (mobile === '?1') return 'Téléphone';
  if (mobile === '?0') return 'Ordinateur';
  if (/mobi|iphone|ipod|android|blackberry|iemobile|opera mini/.test(ua)) return 'Téléphone';
  return 'Ordinateur';
}

/** Un robot, une sonde, un aperçu de lien : tout sauf un client. */
function estRobot(req: Request): boolean {
  const ua = req.headers.get('user-agent') ?? '';
  if (!ua) return true;                    // un vrai navigateur en envoie toujours un
  return ROBOT.test(ua);
}

/** Comparaison à durée constante : ne fuit pas la clé caractère par caractère. */
function memeCle(a: string, b: string): boolean {
  if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}

/**
 * Ville approximative du visiteur.
 * L'appel part d'ici, pas du navigateur : le visiteur n'ouvre aucune
 * connexion vers un tiers, et son adresse n'est jamais écrite en base.
 */
async function ville(req: Request): Promise<string> {
  if (!GEO) return 'Non mesuré';
  const brut = (req.headers.get('x-forwarded-for') ?? '').split(',')[0].trim();
  if (!brut) return 'Non localisé';
  try {
    const ctrl = new AbortController();
    const minuteur = setTimeout(() => ctrl.abort(), 1500);
    const r = await fetch(
      `https://ipwho.is/${encodeURIComponent(brut)}?fields=success,city,region,country_code&lang=fr`,
      { signal: ctrl.signal });
    clearTimeout(minuteur);
    const g = await r.json();
    if (!g || g.success === false) return 'Non localisé';
    const nom = g.city || g.region;
    if (nom) {
      const propre = nettoie(nom, 48);
      return EXONYMES[propre.toLowerCase()] ?? propre;
    }
    return g.country_code && g.country_code !== 'BE' ? 'Hors Belgique' : 'Non localisé';
  } catch {
    return 'Non localisé';                       // jamais d'erreur visible côté visiteur
  }
}

function cors(origine: string): Record<string, string> {
  return {
    'Access-Control-Allow-Origin': origine,
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, X-Pino-Cle',
    'Access-Control-Max-Age': '86400',
    'Vary': 'Origin',
  };
}

function origineAutorisee(req: Request): string | null {
  const o = req.headers.get('Origin');
  return o && ORIGINES.includes(o) ? o : null;
}

/** Appel d'une fonction SQL avec la clé de service, qui ne quitte pas ce fichier. */
async function rpc(nom: string, corps: unknown): Promise<Response> {
  return await fetch(`${URL_BASE}/rest/v1/rpc/${nom}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'apikey': SERVICE,
      'Authorization': `Bearer ${SERVICE}`,
    },
    body: JSON.stringify(corps),
  });
}

/* ── écriture ────────────────────────────────────────────────────────────── */

async function evenement(req: Request, origine: string): Promise<Response> {
  const vide = new Response(null, { status: 204, headers: cors(origine) });

  // Écarté avant toute écriture : un robot ne laisse aucune trace en base.
  if (estRobot(req)) return vide;

  let corps: { t?: string; p?: unknown[]; r?: unknown; c?: unknown };
  try { corps = await req.json(); } catch { return vide; }
  if (!corps || !TYPES.has(String(corps.t))) return vide;

  const type = String(corps.t);
  const paires: [string, string][] = [];

  // Ces deux-là comptent par clé, et une clé hors vocabulaire n'écrit rien du
  // tout : mieux vaut perdre un clic que d'accueillir un libellé inventé.
  if (type === 'reseau') {
    const nom = nettoie(corps.c, 40);
    if (!RESEAUX.has(nom)) return vide;
    paires.push(['reseau', nom]);
  } else if (type === 'pub') {
    const code = nettoie(corps.c, 20);
    if (!PUB.test(code)) return vide;
    paires.push(['pub', code]);
  } else if (type === 'photo') {
    const racine = nettoie(corps.c, 40).toLowerCase();
    if (!PHOTO.test(racine)) return vide;
    paires.push(['photo', racine]);
  } else {
    paires.push([type, '']);
  }

  // Le profil n'est relevé qu'à l'arrivée : une seule fois par visite.
  if (type === 'vue') {
    paires.push(['ville', await ville(req)], ['support', support(req)]);
    const src = nettoie(corps.r, 20);
    if (SOURCES.has(src)) paires.push(['source', src]);
  }

  // Les plats déposés au panier, dédoublonnés et bornés.
  if (type === 'commande' && Array.isArray(corps.p)) {
    const vus = new Set<string>();
    for (const brut of corps.p) {
      const nom = nettoie(brut, 60);
      if (!nom || vus.has(nom)) continue;
      vus.add(nom);
      paires.push(['plat', nom]);
      if (vus.size >= MAX_PLATS) break;
    }
  }

  try { await rpc('incremente', { paires, le_jour: jourBruxelles() }); } catch { /* silencieux */ }
  return vide;
}

/* ── lecture ─────────────────────────────────────────────────────────────── */

async function stats(req: Request, origine: string): Promise<Response> {
  const fourni = req.headers.get('X-Pino-Cle') ?? '';
  if (!CLE || !memeCle(fourni, CLE)) {
    return new Response(JSON.stringify({ erreur: 'cle' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json', ...cors(origine) },
    });
  }

  let jours = parseInt(new URL(req.url).searchParams.get('j') ?? '', 10);
  if (!Number.isFinite(jours) || jours < 1) jours = 30;
  jours = Math.min(jours, MAX_JOURS);

  const depuis = jourBruxelles(new Date(Date.now() - (jours - 1) * 86_400_000));
  // La fenêtre juste avant, de même longueur : [depuis_prec, depuis[.
  const depuis_prec = jourBruxelles(new Date(Date.now() - (2 * jours - 1) * 86_400_000));
  const r = await rpc('stats', { depuis, depuis_prec });
  if (!r.ok) {
    return new Response(JSON.stringify({ erreur: 'base' }), {
      status: 502, headers: { 'Content-Type': 'application/json', ...cors(origine) },
    });
  }

  const agrege = await r.json();
  const totaux    = { vue: 0, appel: 0, itineraire: 0, commande: 0, ...(agrege?.totaux ?? {}) };
  const precedent = { vue: 0, appel: 0, itineraire: 0, commande: 0, ...(agrege?.precedent ?? {}) };

  return new Response(JSON.stringify({
    depuis, jusqua: jourBruxelles(), jours, depuis_prec,
    totaux,
    precedent,
    villes:   agrege?.villes   ?? [],
    supports: agrege?.supports ?? [],
    plats:    agrege?.plats    ?? [],
    courbe:   agrege?.courbe   ?? [],
    sources:  agrege?.sources  ?? [],
    reseaux:  agrege?.reseaux  ?? [],
    photos:   agrege?.photos   ?? [],
    pubs:     agrege?.pubs     ?? [],
    // Ce que pèse la queue des villes, que la page n'affiche pas en détail mais
    // doit compter dans ses pourcentages. Les plats, eux, sont renvoyés en
    // entier : la page les répartit par section de la carte.
    villes_autres:   agrege?.villes_autres   ?? 0,
    villes_autres_n: agrege?.villes_autres_n ?? 0,
  }), {
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store',
      ...cors(origine),
    },
  });
}

/* ── routage ─────────────────────────────────────────────────────────────── */

Deno.serve(async (req: Request) => {
  const origine = origineAutorisee(req);

  if (req.method === 'OPTIONS') {
    return new Response(null, {
      status: origine ? 204 : 403,
      headers: origine ? cors(origine) : {},
    });
  }
  if (!origine) return new Response('Origine non autorisée', { status: 403 });

  const chemin = new URL(req.url).pathname.replace(/^\/mesure/, '') || '/';
  if (req.method === 'POST' && chemin === '/e')     return await evenement(req, origine);
  if (req.method === 'GET'  && chemin === '/stats') return await stats(req, origine);

  return new Response('Introuvable', { status: 404, headers: cors(origine) });
});
