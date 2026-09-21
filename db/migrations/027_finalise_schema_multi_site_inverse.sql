-- Annule la migration 027. Restaure le SCHÉMA d'avant (les données fusionnées
-- par une décision humaine ne sont pas re-séparées : l'inverse de la suite
-- SQL ne compare que le schéma, pas les données).

ALTER TABLE articles ADD COLUMN quantite_stock INTEGER NOT NULL DEFAULT 0;
ALTER TABLE articles ADD COLUMN seuil_alerte   INTEGER NOT NULL DEFAULT 5;
ALTER TABLE articles ADD COLUMN site_id        INTEGER REFERENCES sites(id);

UPDATE articles a
   SET quantite_stock = COALESCE(s.quantite_stock, 0),
       seuil_alerte   = COALESCE(s.seuil_alerte, 5),
       site_id        = COALESCE(s.site_id, 1)
  FROM (
        SELECT DISTINCT ON (article_id)
               article_id, site_id, quantite_stock, seuil_alerte
          FROM stocks_sites
         ORDER BY article_id, site_id
       ) s
 WHERE s.article_id = a.id;

ALTER TABLE articles ALTER COLUMN site_id SET NOT NULL;
ALTER TABLE articles ADD CONSTRAINT chk_articles_quantite_positive CHECK (quantite_stock >= 0);
ALTER TABLE articles ADD CONSTRAINT chk_articles_seuil_positif   CHECK (seuil_alerte >= 0);
ALTER TABLE articles ADD CONSTRAINT uq_articles_id_site UNIQUE (id, site_id);
CREATE INDEX idx_articles_site ON articles(site_id);

DROP INDEX IF EXISTS uq_comptage_article_site_moment_jour;
CREATE UNIQUE INDEX uq_comptage_article_moment_jour
  ON comptages_stock (article_id, moment, (date_comptage::date));

-- La clé étrangère composite de ventes_lignes revient vers articles(id, site_id).
ALTER TABLE ventes_lignes DROP CONSTRAINT IF EXISTS fk_ventes_lignes_article_site;
ALTER TABLE ventes_lignes ADD CONSTRAINT fk_ventes_lignes_article_site
  FOREIGN KEY (article_id, site_id) REFERENCES articles (id, site_id);

ALTER TABLE mouvements_stock  DROP COLUMN IF EXISTS site_id;
ALTER TABLE comptages_stock   DROP COLUMN IF EXISTS site_id;
ALTER TABLE ecarts_stock_ventes DROP COLUMN IF EXISTS site_id;

-- ----------------------------------------------------------------------------
-- Restauration des politiques RLS et des GRANT de colonnes d'origine
-- (la migration 029 les avait remplacés ; ils référencent les colonnes
-- d'articles restaurées ci-dessus, et sont donc recréés ICI, pas dans
-- l'inverse de 029).
-- ----------------------------------------------------------------------------
DROP POLICY IF EXISTS p_articles_site ON articles;
CREATE POLICY p_articles_site ON articles
  USING      (current_user = 'qf_responsable' OR site_id = qf_site_courant())
  WITH CHECK (current_user = 'qf_responsable' OR site_id = qf_site_courant());

DROP POLICY IF EXISTS p_mouvements_site ON mouvements_stock;
CREATE POLICY p_mouvements_site ON mouvements_stock
  USING (current_user = 'qf_responsable'
         OR EXISTS (SELECT 1 FROM articles a
                     WHERE a.id = mouvements_stock.article_id
                       AND a.site_id = qf_site_courant()))
  WITH CHECK (current_user = 'qf_responsable'
         OR EXISTS (SELECT 1 FROM articles a
                     WHERE a.id = mouvements_stock.article_id
                       AND a.site_id = qf_site_courant()));

DROP POLICY IF EXISTS p_comptages_site ON comptages_stock;
CREATE POLICY p_comptages_site ON comptages_stock
  USING (current_user = 'qf_responsable'
         OR EXISTS (SELECT 1 FROM articles a
                     WHERE a.id = comptages_stock.article_id
                       AND a.site_id = qf_site_courant()))
  WITH CHECK (current_user = 'qf_responsable'
         OR EXISTS (SELECT 1 FROM articles a
                     WHERE a.id = comptages_stock.article_id
                       AND a.site_id = qf_site_courant()));

DROP POLICY IF EXISTS p_ecarts_stock_ventes_site ON ecarts_stock_ventes;
CREATE POLICY p_ecarts_stock_ventes_site ON ecarts_stock_ventes
  USING (current_user = 'qf_responsable'
         OR EXISTS (SELECT 1 FROM articles a
                     WHERE a.id = ecarts_stock_ventes.article_id
                       AND a.site_id = qf_site_courant()))
  WITH CHECK (current_user = 'qf_responsable'
         OR EXISTS (SELECT 1 FROM articles a
                     WHERE a.id = ecarts_stock_ventes.article_id
                       AND a.site_id = qf_site_courant()));

REVOKE ALL ON articles FROM qf_responsable, qf_agent_stock, qf_agent_comptabilite;

GRANT SELECT ON articles TO qf_responsable;
GRANT INSERT (nom, categorie, unite, prix_achat, prix_vente, quantite_stock,
              site_id, fournisseur_id)
  ON articles TO qf_responsable;
GRANT UPDATE (nom, categorie, unite, prix_achat, prix_vente, quantite_stock,
              fournisseur_id, actif, date_desactivation, desactive_par_id)
  ON articles TO qf_responsable;

GRANT SELECT (id, nom, categorie, unite, quantite_stock, seuil_alerte,
              site_id, fournisseur_id, date_creation, actif,
              date_desactivation, desactive_par_id)
  ON articles TO qf_agent_stock;
GRANT INSERT (nom, categorie, unite, quantite_stock, site_id, fournisseur_id)
  ON articles TO qf_agent_stock;
GRANT UPDATE (nom, categorie, unite, quantite_stock)
  ON articles TO qf_agent_stock;

GRANT SELECT (id, nom, categorie, unite, prix_vente, site_id,
              fournisseur_id, date_creation, actif)
  ON articles TO qf_agent_comptabilite;

REVOKE SELECT ON comptages_stock FROM qf_agent_stock;
GRANT SELECT (id, article_id, utilisateur_id, moment, quantite_comptee, date_comptage)
  ON comptages_stock TO qf_agent_stock;

DELETE FROM schema_migrations WHERE version = '027';
