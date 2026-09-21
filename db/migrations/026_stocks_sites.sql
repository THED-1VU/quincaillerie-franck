-- ============================================================================
-- 026 — Chantier 13b (cycle 35) : nouvelle table de stock par site.
-- ----------------------------------------------------------------------------
-- Décision du propriétaire (2026-09-19, VISION_PRODUIT.md « Modèle
-- article/stock multi-site ») : un article = UNE fiche ; le stock est réparti
-- par site. Cette migration crée la table `stocks_sites` et y recopie, à
-- l'identique, la quantité et le seuil de chaque fiche actuelle (une ligne par
-- fiche, à son site). Les colonnes d'origine d'`articles` ne sont PAS encore
-- supprimées : c'est la migration 027 qui finalise, après avoir ajouté
-- `site_id` aux mouvements/comptages et consommé les décisions de
-- rapprochement (cycle 13a).
-- ============================================================================

CREATE TABLE stocks_sites (
    article_id     INTEGER NOT NULL REFERENCES articles(id),
    site_id        INTEGER NOT NULL REFERENCES sites(id),
    quantite_stock INTEGER NOT NULL DEFAULT 0,
    seuil_alerte   INTEGER NOT NULL DEFAULT 5,
    CONSTRAINT pk_stocks_sites PRIMARY KEY (article_id, site_id),
    CONSTRAINT chk_stocks_sites_quantite_positive CHECK (quantite_stock >= 0),
    CONSTRAINT chk_stocks_sites_seuil_positif   CHECK (seuil_alerte >= 0)
);

COMMENT ON TABLE stocks_sites IS
  'Stock d''un article par site (décision 2026-09-19 : une fiche article, un '
  'stock par site). La quantité et le seuil ne vivent plus sur articles. '
  'Toute écriture passe par les fonctions SECURITY DEFINER du stock — aucun '
  'rôle métier n''a d''INSERT/UPDATE/DELETE direct.';

CREATE INDEX idx_stocks_sites_site ON stocks_sites(site_id);

-- Recopie 1:1 depuis l'état actuel (une fiche = un site aujourd'hui).
INSERT INTO stocks_sites (article_id, site_id, quantite_stock, seuil_alerte)
SELECT id, site_id, quantite_stock, seuil_alerte
  FROM articles;

INSERT INTO schema_migrations (version, nom)
VALUES ('026', 'stocks_sites')
ON CONFLICT (version) DO NOTHING;
