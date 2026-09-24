/* ─────────────────────────────────────────────────────────────────────────────
   Mesure de fréquentation — Pizzeria Pino
   Fonction Edge Supabase. Deux points d'entrée :

     POST  /mesure/e         le site signale un événement
     GET   /mesure/stats     la page /statistiques lit les totaux, clé exigée
     GET   /mesure/facebook  le site lit les dernières publications de la page

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
   Meta, et n'arrivera jamais ici. Un clic sur « Avis » n'est pas un avis
   publié : c'est un client envoyé sur la fiche Google. */
const PLACES = ['Suivre', 'Profil', 'Publication', 'Reel', 'Contact',
                'Pied de page', 'Crédit photo', 'Avis', 'Autre'];
const RESEAUX = new Set(
  ['Instagram', 'Facebook', 'Google', 'Tripadvisor'].flatMap(r => PLACES.map(p => `${r} · ${p}`)));

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

/* Les abonnés Instagram et Facebook. Aucun accès à Meta : le module Trustindex
   du site publie un petit fichier public qui porte déjà le nombre d'abonnés
   du compte (follower_num). On le lit au plus toutes les trois heures, au fil
   des visites et à l'ouverture du tableau de bord, et l'on garde un chiffre
   par jour et par réseau. Un nouveau module (Facebook) s'ajoute en mettant
   son identifiant dans FLUX_ABONNES, séparé par des virgules. */
const FLUX_ABONNES = (Deno.env.get('FLUX_ABONNES') ?? 'fa288d1828901758c5563445c70')
  .split(',').map(s => s.trim()).filter(s => /^[a-z0-9]{10,40}$/i.test(s));
const RESEAUX_SUIVIS = new Set(['Instagram', 'Facebook']);
const INTERVALLE_RELEVE = 3 * 3600_000;
let dernierReleve = 0;

/* La page Facebook, lue avec la clé de page rangée dans les secrets
   (FB_JETON). La clé ne quitte jamais ce fichier : le site ne reçoit que le
   contenu public de la page, et les photos recopiées chez nous. */
const FB_JETON = Deno.env.get('FB_JETON') ?? '';
const GRAPH = 'https://graph.facebook.com/v21.0';
const FRAICHEUR_FB = 3 * 3600_000;
const MAX_PUBLICATIONS = 8;
let fbEnCours: Promise<unknown> | null = null;

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

/**
 * Heure de Bruxelles, « 00 » à « 23 ».
 *
 * Déduite ici, à l'écriture, et jamais transmise par le visiteur : son fuseau,
 * son horloge, son décalage ne nous regardent pas. Ce qui entre en base est un
 * compteur de plus — « 19 h : 42 » — au même titre que la ville ou l'appareil.
 * Aucun horodatage individuel, donc aucun parcours à reconstituer.
 */
function heureBruxelles(d = new Date()): string {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/Brussels', hour: '2-digit', hour12: false, hourCycle: 'h23',
  }).formatToParts(d);
  const h = parts.find(p => p.type === 'hour')?.value ?? '';
  return h.padStart(2, '0');
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

/* ── abonnés ─────────────────────────────────────────────────────────────── */

/** Lit le nombre d'abonnés dans les fichiers Trustindex et l'écrit pour le jour.
    Jamais bloquant, jamais d'erreur visible : au pire, un jour sans relevé. */
async function releveAbonnes(): Promise<void> {
  if (!FLUX_ABONNES.length || Date.now() - dernierReleve < INTERVALLE_RELEVE) return;
  dernierReleve = Date.now();
  const releves: { reseau: string; n: number }[] = [];
  for (const id of FLUX_ABONNES) {
    try {
      const ctrl = new AbortController();
      const minuteur = setTimeout(() => ctrl.abort(), 3000);
      const r = await fetch(`https://cdn.trustindex.io/widgets/${id.slice(0, 2)}/${id}/data.json`,
                            { signal: ctrl.signal });
      clearTimeout(minuteur);
      if (!r.ok) continue;
      const d = await r.json();
      for (const src of Object.values(d?.sources ?? {}) as any[]) {
        const reseau = String(src?.type ?? '');
        const n = Number(src?.user?.follower_num);
        if (RESEAUX_SUIVIS.has(reseau) && Number.isInteger(n) && n >= 0 && n < 1e8) {
          releves.push({ reseau, n });
        }
      }
    } catch { /* service injoignable : on réessaiera plus tard */ }
  }
  if (!releves.length) { dernierReleve = 0; return; }
  try { await rpc('releve_abonnes', { releves, le_jour: jourBruxelles() }); } catch { dernierReleve = 0; }
}

/** Laisse le relevé finir après la réponse, sans faire attendre le visiteur. */
function enArrierePlan(p: Promise<unknown>): void {
  try { (globalThis as any).EdgeRuntime?.waitUntil?.(p); } catch { /* rien */ }
}

/* ── Facebook ────────────────────────────────────────────────────────────── */

const ENTETES_SERVICE = () => ({
  'apikey': SERVICE, 'Authorization': `Bearer ${SERVICE}`,
});

async function lisCacheFacebook(): Promise<{ valeur: any; maj: string } | null> {
  try {
    const r = await fetch(`${URL_BASE}/rest/v1/cache_facebook?cle=eq.page&select=valeur,maj`,
                          { headers: ENTETES_SERVICE() });
    if (!r.ok) return null;
    const l = await r.json();
    return l?.[0] ?? null;
  } catch { return null; }
}

async function ecritCacheFacebook(valeur: unknown): Promise<void> {
  await fetch(`${URL_BASE}/rest/v1/cache_facebook`, {
    method: 'POST',
    headers: { ...ENTETES_SERVICE(), 'Content-Type': 'application/json',
               'Prefer': 'resolution=merge-duplicates' },
    body: JSON.stringify({ cle: 'page', valeur, maj: new Date().toISOString() }),
  });
}

async function avecDelai(url: string, ms: number): Promise<Response> {
  const ctrl = new AbortController();
  const m = setTimeout(() => ctrl.abort(), ms);
  try { return await fetch(url, { signal: ctrl.signal }); } finally { clearTimeout(m); }
}

/** Recopie une image de Facebook dans le bucket public « facebook ». Les
    adresses de Facebook expirent au bout de quelques jours, et les charger
    depuis le site ouvrirait une connexion vers Meta à chaque visiteur. */
async function recopieImage(source: string, nom: string): Promise<string | null> {
  try {
    const r = await avecDelai(source, 6000);
    if (!r.ok) return null;
    const type = r.headers.get('content-type') ?? 'image/jpeg';
    if (!type.startsWith('image/')) return null;
    const corps = new Uint8Array(await r.arrayBuffer());
    if (corps.byteLength > 5_000_000) return null;
    const up = await fetch(`${URL_BASE}/storage/v1/object/facebook/${nom}`, {
      method: 'POST',
      headers: { ...ENTETES_SERVICE(), 'Content-Type': type, 'x-upsert': 'true',
                 'Cache-Control': 'max-age=86400' },
      body: corps,
    });
    if (!up.ok) return null;
    return `${URL_BASE}/storage/v1/object/public/facebook/${nom}`;
  } catch { return null; }
}

/** Lit la page (nom, abonnés, publications) et met le résultat en mémoire.
    En cas d'échec, on garde les publications déjà connues et l'on note
    l'erreur : le site continue d'afficher, le tableau de bord prévient. */
async function rafraichitFacebook(ancien: any): Promise<any> {
  const base = { publications: ancien?.publications ?? [], nom: ancien?.nom ?? 'Pizzeria Pino Nandrin',
                 abonnes: ancien?.abonnes ?? null, lien: ancien?.lien ?? null, avatar: ancien?.avatar ?? null };
  if (!FB_JETON) {
    const v = { ...base, etat: 'sans_cle', message: 'Aucune clé FB_JETON dans les secrets.' };
    await ecritCacheFacebook(v).catch(() => {});
    return v;
  }
  try {
    const cle = encodeURIComponent(FB_JETON);
    const [rp, rs] = await Promise.all([
      avecDelai(`${GRAPH}/me?fields=id,name,followers_count,fan_count,link,picture.width(200).height(200)&access_token=${cle}`, 8000),
      avecDelai(`${GRAPH}/me/posts?fields=id,message,created_time,permalink_url,full_picture&limit=20&access_token=${cle}`, 8000),
    ]);
    const page = await rp.json();
    const posts = await rs.json();
    const err = page?.error ?? posts?.error;
    if (err) {
      const v = { ...base, etat: err.code === 190 ? 'cle_invalide' : 'erreur',
                  message: String(err.message ?? 'Erreur Facebook').slice(0, 200) };
      await ecritCacheFacebook(v).catch(() => {});
      return v;
    }
    const abonnes = Number.isInteger(page.followers_count) ? page.followers_count
                  : (Number.isInteger(page.fan_count) ? page.fan_count : null);
    const avatarSrc = page?.picture?.data?.url;
    const avatar = avatarSrc ? (await recopieImage(avatarSrc, 'avatar.jpg')) ?? base.avatar : base.avatar;

    const retenus = (posts?.data ?? [])
      .filter((p: any) => p && (p.message || p.full_picture) && /^[0-9_]+$/.test(String(p.id)))
      .slice(0, MAX_PUBLICATIONS);
    const connus: Record<string, any> = {};
    for (const p of base.publications) connus[p.id] = p;
    const publications = [];
    for (const p of retenus) {
      let image: string | null = null;
      if (p.full_picture) {
        image = connus[p.id]?.image ?? await recopieImage(p.full_picture, `${p.id}.jpg`);
      }
      publications.push({
        id: String(p.id),
        texte: nettoieTexte(p.message ?? '', 600),
        date: String(p.created_time ?? ''),
        lien: /^https:\/\/(www\.)?facebook\.com\//.test(p.permalink_url ?? '') ? p.permalink_url : null,
        image,
      });
    }
    const v = { etat: 'ok', message: '', nom: String(page.name ?? base.nom).slice(0, 80),
                abonnes, lien: 'https://www.facebook.com/profile.php?id=100064486855231',
                avatar, publications };
    await ecritCacheFacebook(v);
    if (abonnes != null) {
      await rpc('releve_abonnes', { releves: [{ reseau: 'Facebook', n: abonnes }], le_jour: jourBruxelles() })
        .catch(() => {});
    }
    return v;
  } catch {
    return { ...base, etat: 'erreur', message: 'Facebook ne répond pas.' };
  }
}

/** Texte d'une publication : sauts de ligne gardés, balises et caractères de
    contrôle retirés. Le site l'insère en texte, jamais en HTML. */
function nettoieTexte(v: string, max: number): string {
  return String(v).replace(/[\x00-\x09\x0b-\x1f<>]/g, ' ').replace(/[ \t]+/g, ' ').trim().slice(0, max);
}

/** Le contenu à jour, en relisant Facebook si la mémoire a plus de 3 heures.
    Sans mémoire du tout, on attend la lecture ; sinon on sert l'ancienne
    version tout de suite et l'on rafraîchit en arrière-plan. */
async function contenuFacebook(attendre = false): Promise<any> {
  const c = await lisCacheFacebook();
  const perime = !c || Date.now() - Date.parse(c.maj) > FRAICHEUR_FB;
  if (perime) {
    if (!fbEnCours) fbEnCours = rafraichitFacebook(c?.valeur).finally(() => { fbEnCours = null; });
    if (!c || attendre) return await fbEnCours;
    enArrierePlan(fbEnCours);
  }
  return { ...c!.valeur, maj: c!.maj };
}

async function facebook(origine: string): Promise<Response> {
  const v = await contenuFacebook();
  // Le site ne reçoit que le contenu public ; l'état détaillé reste au tableau de bord.
  const publique = { disponible: (v?.publications ?? []).length > 0, nom: v?.nom, abonnes: v?.abonnes,
                     lien: v?.lien, avatar: v?.avatar, publications: v?.publications ?? [] };
  return new Response(JSON.stringify(publique), {
    headers: { 'Content-Type': 'application/json; charset=utf-8',
               'Cache-Control': 'public, max-age=600', ...cors(origine) },
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
    enArrierePlan(releveAbonnes());
    paires.push(['ville', await ville(req)], ['support', support(req)],
                ['heure', heureBruxelles()]);
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
  // Le tableau de bord ouvert, c'est aussi l'occasion d'un relevé frais.
  const [, fb] = await Promise.all([releveAbonnes(), contenuFacebook(true).catch(() => null)]);
  const [r, ra] = await Promise.all([
    rpc('stats', { depuis, depuis_prec }),
    rpc('stats_abonnes', { depuis }),
  ]);
  if (!r.ok) {
    return new Response(JSON.stringify({ erreur: 'base' }), {
      status: 502, headers: { 'Content-Type': 'application/json', ...cors(origine) },
    });
  }

  const agrege = await r.json();
  const abonnes = ra.ok ? await ra.json() : {};
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
    heures:   agrege?.heures   ?? [],
    // Les quatre mesures jour par jour. La page laisse choisir celle qu'elle suit.
    courbes:  agrege?.courbes  ?? {},
    // Ce que pèse la queue des villes, que la page n'affiche pas en détail mais
    // doit compter dans ses pourcentages. Les plats, eux, sont renvoyés en
    // entier : la page les répartit par section de la carte.
    villes_autres:   agrege?.villes_autres   ?? 0,
    villes_autres_n: agrege?.villes_autres_n ?? 0,
    // Les abonnés par réseau : la série de la période et le chiffre d'avant.
    abonnes: abonnes ?? {},
    // L'état de la lecture Facebook : le tableau de bord prévient si la clé
    // ne marche plus, pour qu'on ne le découvre pas des semaines plus tard.
    facebook: fb ? { etat: fb.etat, message: fb.message ?? '', maj: fb.maj ?? null } : null,
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
  if (req.method === 'GET'  && chemin === '/facebook') return await facebook(origine);

  return new Response('Introuvable', { status: 404, headers: cors(origine) });
});
