-- ============================================================================
-- 027 — Chantier 13b (cycle 35) : finalise le schéma multi-site.
-- ----------------------------------------------------------------------------
-- Ordre, délibérément :
--   1. `mouvements_stock`, `comptages_stock` et `ecarts_stock_ventes` gagnent
--      un `site_id` EXPLICITE, réamorcé depuis l'ancien site de la fiche (ou
--      de la vente pour les écarts) AVANT toute fusion d'homonymes : c'est ce
--      qui préserve le site réel de chaque historique.
--   2. Les décisions `fusionner` du cycle 13a sont CONSOMMÉES : les
--      références de la fiche supprimée sont re-pointées vers la fiche
--      gardée, sa ligne de stock est rattachée à la fiche gardée, puis la
--      fiche en double est supprimée. Jamais de fusion automatique : seules
--      les paires validées une par une par le propriétaire sont fusionnées.
--   3. `articles` perd enfin `site_id`, `quantite_stock` et `seuil_alerte`
--      (et leurs contraintes/index), et l'unicité de comptage devient
--      (article, site, moment, jour).
--
-- Les fonctions et politiques qui lisaient encore les anciennes colonnes sont
-- réécrites par les migrations 028 (fonctions) et 029 (RLS/GRANT) : entre 027
-- et 029, aucun trafic applicatif n'existe, c'est le point d'une migration.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. site_id explicite sur les historiques de stock
-- ----------------------------------------------------------------------------
ALTER TABLE mouvements_stock ADD COLUMN IF NOT EXISTS site_id INTEGER REFERENCES sites(id);
UPDATE mouvements_stock m
   SET site_id = a.site_id
  FROM articles a
 WHERE a.id = m.article_id
   AND m.site_id IS NULL;
ALTER TABLE mouvements_stock ALTER COLUMN site_id SET NOT NULL;

ALTER TABLE comptages_stock ADD COLUMN IF NOT EXISTS site_id INTEGER REFERENCES sites(id);
UPDATE comptages_stock c
   SET site_id = a.site_id
  FROM articles a
 WHERE a.id = c.article_id
   AND c.site_id IS NULL;
ALTER TABLE comptages_stock ALTER COLUMN site_id SET NOT NULL;

ALTER TABLE ecarts_stock_ventes ADD COLUMN IF NOT EXISTS site_id INTEGER REFERENCES sites(id);
UPDATE ecarts_stock_ventes e
   SET site_id = v.site_id
  FROM ventes v
 WHERE v.id = e.vente_id
   AND e.site_id IS NULL;
ALTER TABLE ecarts_stock_ventes ALTER COLUMN site_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_mouvements_site ON mouvements_stock(site_id);
CREATE INDEX IF NOT EXISTS idx_comptages_site  ON comptages_stock(site_id);
CREATE INDEX IF NOT EXISTS idx_ecarts_site      ON ecarts_stock_ventes(site_id);

-- ----------------------------------------------------------------------------
-- 2. Consommation des décisions humaines de fusion (cycle 13a)
-- ----------------------------------------------------------------------------
-- La clé étrangère composite ventes_lignes(article_id, site_id) →
-- articles(id, site_id) (migration 002) est d'abord levée : elle dépend de
-- l'index uq_articles_id_site et sera ré-accrochée, plus bas, à
-- stocks_sites(article_id, site_id) — l'invariant devient plus fort : une
-- ligne de vente ne peut désigner que (un article, un site) où l'article a
-- réellement un stock.
ALTER TABLE ventes_lignes DROP CONSTRAINT IF EXISTS fk_ventes_lignes_article_site;

DO $$
DECLARE
    d RECORD;
BEGIN
    FOR d IN
        SELECT article_id_1, article_id_2
          FROM rapprochements_articles
         WHERE decision = 'fusionner'
         ORDER BY article_id_1, article_id_2
    LOOP
        -- Références historiques : la fiche gardée reprend tout.
        UPDATE mouvements_stock SET article_id = d.article_id_1
         WHERE article_id = d.article_id_2;
        UPDATE comptages_stock SET article_id = d.article_id_1
         WHERE article_id = d.article_id_2;
        UPDATE ventes_lignes SET article_id = d.article_id_1
         WHERE article_id = d.article_id_2;
        UPDATE ecarts_stock_ventes SET article_id = d.article_id_1
         WHERE article_id = d.article_id_2;
        UPDATE historique_prix_articles SET article_id = d.article_id_1
         WHERE article_id = d.article_id_2;
        UPDATE historique_modifications_articles SET article_id = d.article_id_1
         WHERE article_id = d.article_id_2;

        -- Sa ligne de stock est rattachée à la fiche gardée.
        UPDATE stocks_sites SET article_id = d.article_id_1
         WHERE article_id = d.article_id_2;

        -- La décision a été consommée ; la fiche en double disparaît.
        DELETE FROM rapprochements_articles
         WHERE article_id_1 = d.article_id_1 AND article_id_2 = d.article_id_2;
        DELETE FROM articles WHERE id = d.article_id_2;
    END LOOP;
END;
$$;

ALTER TABLE ventes_lignes ADD CONSTRAINT fk_ventes_lignes_article_site
  FOREIGN KEY (article_id, site_id) REFERENCES stocks_sites (article_id, site_id);

-- ----------------------------------------------------------------------------
-- 3. articles : la fiche ne porte plus ni site ni quantité ni seuil
-- ----------------------------------------------------------------------------
-- Les anciennes politiques référencent articles.site_id : levées ici, elles
-- sont recréées (nouvelle forme) par la migration 029.
DROP POLICY IF EXISTS p_articles_site ON articles;
DROP POLICY IF EXISTS p_mouvements_site ON mouvements_stock;
DROP POLICY IF EXISTS p_comptages_site ON comptages_stock;
DROP POLICY IF EXISTS p_ecarts_stock_ventes_site ON ecarts_stock_ventes;

DROP INDEX IF EXISTS idx_articles_site;
ALTER TABLE articles DROP CONSTRAINT IF EXISTS uq_articles_id_site;
ALTER TABLE articles DROP CONSTRAINT IF EXISTS chk_articles_quantite_positive;
ALTER TABLE articles DROP CONSTRAINT IF EXISTS chk_articles_seuil_positif;
ALTER TABLE articles DROP COLUMN IF EXISTS quantite_stock;
ALTER TABLE articles DROP COLUMN IF EXISTS seuil_alerte;
ALTER TABLE articles DROP COLUMN IF EXISTS site_id;

-- Un comptage cible désormais un (article, site) : le même article peut être
-- compté le même jour, une fois par site.
DROP INDEX IF EXISTS uq_comptage_article_moment_jour;
CREATE UNIQUE INDEX uq_comptage_article_site_moment_jour
  ON comptages_stock (article_id, site_id, moment, (date_comptage::date));

COMMENT ON INDEX uq_comptage_article_site_moment_jour IS
  'Un seul comptage par article, par site, par moment (matin/soir) et par '
  'jour — le même article peut être compté le même jour une fois par site '
  '(décision multi-site 2026-09-19).';

INSERT INTO schema_migrations (version, nom)
VALUES ('027', 'finalise_schema_multi_site')
ON CONFLICT (version) DO NOTHING;
