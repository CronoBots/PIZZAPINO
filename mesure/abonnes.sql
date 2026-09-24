-- =====================================================================
--  Pizzeria Pino — relevé quotidien des abonnés (Instagram, Facebook)
--  À coller après schema.sql, dans : Supabase → SQL Editor → Run
--
--  Un nombre par jour et par réseau, le dernier relevé du jour l'emporte.
--  Rien sur les visiteurs : c'est un chiffre public du compte, lu dans le
--  fichier que publie le module Trustindex.
-- =====================================================================

create table if not exists public.abonnes (
  jour   text    not null,               -- 2026-09-24, en heure de Bruxelles
  reseau text    not null,               -- Instagram | Facebook
  n      integer not null,
  primary key (jour, reseau)
);

-- Fermée au web, comme compteur : seule la fonction Edge y touche.
alter table public.abonnes enable row level security;
revoke all on public.abonnes from anon, authenticated;

create or replace function public.releve_abonnes(releves jsonb, le_jour text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  r jsonb;
begin
  for r in select * from jsonb_array_elements(releves)
  loop
    insert into public.abonnes (jour, reseau, n)
    values (le_jour, r->>'reseau', (r->>'n')::int)
    on conflict (jour, reseau) do update set n = excluded.n;
  end loop;
end;
$$;

-- La série de la période, et le dernier chiffre connu juste avant elle :
-- c'est lui qui dit de combien on a gagné sur la période.
create or replace function public.stats_abonnes(depuis text)
returns json
language sql
security definer
set search_path = public
as $$
  select coalesce(json_object_agg(reseau, json_build_object(
    'serie', (select coalesce(json_agg(json_build_object('j', a2.jour, 'n', a2.n) order by a2.jour), '[]'::json)
              from public.abonnes a2 where a2.reseau = r.reseau and a2.jour >= depuis),
    'avant', (select a3.n from public.abonnes a3
              where a3.reseau = r.reseau and a3.jour < depuis
              order by a3.jour desc limit 1)
  )), '{}'::json)
  from (select distinct reseau from public.abonnes) r;
$$;

revoke execute on function public.releve_abonnes(jsonb, text) from public, anon, authenticated;
revoke execute on function public.stats_abonnes(text)         from public, anon, authenticated;

-- =====================================================================
--  Fil Facebook : la dernière lecture de la page, gardée en mémoire.
--  Une seule ligne (cle = 'page'). Fermée au web : seule la fonction Edge
--  la lit et l'écrit, et ne renvoie au site que le contenu public de la page.
--  Les photos sont copiées dans le bucket public « facebook ».
-- =====================================================================
create table if not exists public.cache_facebook (
  cle    text primary key,
  valeur jsonb not null,
  maj    timestamptz not null default now()
);
alter table public.cache_facebook enable row level security;
revoke all on public.cache_facebook from anon, authenticated;

insert into storage.buckets (id, name, public)
values ('facebook', 'facebook', true)
on conflict (id) do nothing;
