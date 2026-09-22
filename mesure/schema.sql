-- =====================================================================
--  Pizzeria Pino — mesure de fréquentation (Supabase / PostgreSQL)
--  À coller dans : Supabase → projet PIZZERIAPINO → SQL Editor → Run
--
--  Principe : on n'enregistre QUE des compteurs agrégés. Une seule ligne
--  par (jour, type, clé), incrémentée. Pas de ligne par visiteur, pas
--  d'adresse IP, pas d'horodatage individuel, pas de cookie. Aucun
--  parcours ne peut en être reconstitué — c'est exactement ce que
--  promettent les mentions légales et l'article 14 du contrat.
-- =====================================================================

create table if not exists public.compteur (
  jour text    not null,                 -- 2026-09-18, en heure de Bruxelles
  type text    not null,                 -- vue | appel | itineraire | commande | ville | support | plat
  cle  text    not null default '',
  n    integer not null default 0,
  primary key (jour, type, cle)
);

create index if not exists compteur_jour_idx on public.compteur (jour);

-- ---------------------------------------------------------------------
--  Sécurité : la table est fermée. Personne n'y accède depuis le web.
--  Ni lecture ni écriture pour « anon » : aucune policy n'est créée, et
--  RLS bloque donc tout. Seule la fonction Edge, qui détient la clé de
--  service, écrit et lit — après avoir vérifié le mot de passe.
--
--  C'est la différence avec un montage où la fonction d'agrégation est
--  accordée à « anon » : là, quiconque lit le JavaScript du site peut
--  appeler la fonction et consulter les chiffres.
-- ---------------------------------------------------------------------
alter table public.compteur enable row level security;

revoke all on public.compteur from anon, authenticated;

-- ---------------------------------------------------------------------
--  Incrément atomique. Appelée par la fonction Edge uniquement.
-- ---------------------------------------------------------------------
create or replace function public.incremente(paires jsonb, le_jour text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  p jsonb;
begin
  for p in select * from jsonb_array_elements(paires)
  loop
    insert into public.compteur (jour, type, cle, n)
    values (le_jour, p->>0, coalesce(p->>1, ''), 1)
    on conflict (jour, type, cle) do update set n = public.compteur.n + 1;
  end loop;
end;
$$;

-- ---------------------------------------------------------------------
--  Agrégats pour le tableau de bord, sur les N derniers jours.
-- ---------------------------------------------------------------------
create or replace function public.stats(depuis text, depuis_prec text default null)
returns json
language sql
security definer
set search_path = public
as $$
  with fenetre as (
    select type, cle, sum(n)::int as n
    from public.compteur
    where jour >= depuis
    group by type, cle
  ),
  -- La fenêtre d'avant, de même longueur, pour dire si ça monte ou si ça baisse.
  precedente as (
    select type, sum(n)::int as n
    from public.compteur
    where depuis_prec is not null and jour >= depuis_prec and jour < depuis
      and type in ('vue','appel','itineraire','commande')
    group by type
  ),
  -- Villes et plats sont classés ICI, avec leur rang : la page n'affiche que
  -- les premiers, mais on renvoie aussi ce que pèse la queue. Sans cela, elle
  -- calculerait ses pourcentages sur le seul haut du classement et annoncerait
  -- des parts trop grandes.
  v as (
    select cle as nom, n, row_number() over (order by n desc, cle) as rang
    from fenetre where type = 'ville'
  ),
  )
  select json_build_object(
    'totaux', (
      select coalesce(json_object_agg(type, n), '{}'::json)
      from (select type, sum(n)::int as n from fenetre
            where type in ('vue','appel','itineraire','commande')
            group by type) t
    ),
    'precedent', (
      select coalesce(json_object_agg(type, n), '{}'::json) from precedente
    ),
    'villes', (
      select coalesce(json_agg(json_build_object('nom', nom, 'n', n) order by rang), '[]'::json)
      from v where rang <= 12
    ),
    'villes_autres',   (select coalesce(sum(n), 0)::int from v where rang > 12),
    'villes_autres_n', (select count(*)::int          from v where rang > 12),
    'supports', (
      select coalesce(json_agg(json_build_object('nom', nom, 'n', n) order by n desc, nom), '[]'::json)
      from (select cle as nom, n from fenetre where type = 'support') s
    ),
    -- Tous les plats : le tableau de bord les repartit par section de la carte,
    -- et une proportion calculee sur les quinze premiers seulement serait fausse.
    -- D'ou viennent les ouvertures. Cinq etiquettes fermees, jamais un referent
    -- brut : une adresse porterait le terme cherche ou un identifiant de campagne.
    'sources', (
      select coalesce(json_agg(json_build_object('nom', nom, 'n', n) order by n desc, nom), '[]'::json)
      from (select cle as nom, n from fenetre where type = 'source') so
    ),
    'plats', (
      select coalesce(json_agg(json_build_object('nom', nom, 'n', n) order by n desc, nom), '[]'::json)
      from (select cle as nom, n from fenetre where type = 'plat') p
    ),
    'courbe', (
      select coalesce(json_agg(json_build_object('j', j, 'n', n) order by j), '[]'::json)
      from (select jour as j, sum(n)::int as n from public.compteur
            where type = 'vue' and jour >= depuis group by jour) c
    )
  );
$$;

-- Ces deux fonctions ne sont accordées à personne d'autre qu'au rôle de
-- service : la fonction Edge s'en sert, le web n'y touche pas.
revoke execute on function public.incremente(jsonb, text) from public, anon, authenticated;
revoke execute on function public.stats(text, text)       from public, anon, authenticated;

-- =====================================================================
--  Ensuite : déployer la fonction Edge (voir mesure/README.md), puis
--  Project Settings → API → copier l'URL du projet.
-- =====================================================================
