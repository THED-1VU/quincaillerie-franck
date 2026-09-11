-- ============================================================================
-- 002 — Cohérence entre tables
-- ----------------------------------------------------------------------------
-- Deux incohérences prouvées par exécution au diagnostic du cycle 2 :
--   * une vente rattachée au Comptoir peut contenir un article du Magasin
--     (le cloisonnement par site est alors une fiction) ;
--   * une même vente peut engendrer PLUSIEURS recettes comptables
--     (double comptage du chiffre d'affaires).
--
-- On les rend impossibles de façon DÉCLARATIVE (clés étrangères composites et
-- index unique partiel), sans déclencheur : la base refuse, quel que soit le
-- programme client.
--
-- Cycle 2 — chantier C1. Idempotent.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Clés candidates nécessaires aux clés étrangères composites
-- ----------------------------------------------------------------------------
ALTER TABLE articles DROP CONSTRAINT IF EXISTS uq_articles_id_site;
ALTER TABLE articles ADD  CONSTRAINT uq_articles_id_site UNIQUE (id, site_id);

ALTER TABLE ventes DROP CONSTRAINT IF EXISTS uq_ventes_id_site;
ALTER TABLE ventes ADD  CONSTRAINT uq_ventes_id_site UNIQUE (id, site_id);

-- ----------------------------------------------------------------------------
-- ventes_lignes : porte désormais le site, et ce site doit être À LA FOIS
-- celui de la vente et celui de l'article. Une ligne « hors site » devient
-- structurellement impossible.
-- ----------------------------------------------------------------------------
ALTER TABLE ventes_lignes ADD COLUMN IF NOT EXISTS site_id INTEGER;

UPDATE ventes_lignes vl
   SET site_id = v.site_id
  FROM ventes v
 WHERE v.id = vl.vente_id
   AND vl.site_id IS DISTINCT FROM v.site_id;

ALTER TABLE ventes_lignes ALTER COLUMN site_id SET NOT NULL;

ALTER TABLE ventes_lignes DROP CONSTRAINT IF EXISTS fk_ventes_lignes_vente_site;
ALTER TABLE ventes_lignes ADD  CONSTRAINT fk_ventes_lignes_vente_site
  FOREIGN KEY (vente_id, site_id) REFERENCES ventes (id, site_id);

ALTER TABLE ventes_lignes DROP CONSTRAINT IF EXISTS fk_ventes_lignes_article_site;
ALTER TABLE ventes_lignes ADD  CONSTRAINT fk_ventes_lignes_article_site
  FOREIGN KEY (article_id, site_id) REFERENCES articles (id, site_id);

COMMENT ON COLUMN ventes_lignes.site_id IS
  'Site de la ligne. Contraint à être celui de la vente ET celui de l''article '
  '(clés étrangères composites) : empêche de vendre au Comptoir un article du Magasin.';

-- ----------------------------------------------------------------------------
-- transactions : une recette par vente, au plus. Et la transaction issue d'une
-- vente porte forcément le site de cette vente.
-- ----------------------------------------------------------------------------
DROP INDEX IF EXISTS uq_transactions_recette_par_vente;
CREATE UNIQUE INDEX uq_transactions_recette_par_vente
  ON transactions (vente_id)
  WHERE vente_id IS NOT NULL AND type = 'recette';

COMMENT ON INDEX uq_transactions_recette_par_vente IS
  'Au plus UNE recette par vente : empêche le double comptage du chiffre d''affaires. '
  'Une dépense rattachée à la même vente (remboursement, avoir) reste possible.';

ALTER TABLE transactions DROP CONSTRAINT IF EXISTS fk_transactions_vente_site;
ALTER TABLE transactions ADD  CONSTRAINT fk_transactions_vente_site
  FOREIGN KEY (vente_id, site_id) REFERENCES ventes (id, site_id);

INSERT INTO schema_migrations (version, nom)
VALUES ('002', 'coherence_inter_tables')
ON CONFLICT (version) DO NOTHING;
