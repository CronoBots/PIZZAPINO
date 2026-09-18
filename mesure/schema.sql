-- Compteurs agrégés. Aucune ligne par visiteur, aucune adresse IP, aucun cookie :
-- une seule ligne par (jour, type, clé), incrémentée. Impossible d'y reconstituer
-- un parcours individuel, ce qui est exactement ce que promet la page légale.
CREATE TABLE IF NOT EXISTS compteur (
  jour TEXT    NOT NULL,          -- 2026-09-18, en heure de Bruxelles
  type TEXT    NOT NULL,          -- vue | appel | itineraire | commande | ville | support | plat
  cle  TEXT    NOT NULL DEFAULT '',
  n    INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (jour, type, cle)
);

CREATE INDEX IF NOT EXISTS idx_compteur_jour ON compteur (jour);
