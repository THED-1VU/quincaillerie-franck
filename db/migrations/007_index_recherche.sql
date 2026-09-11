-- ============================================================================
-- 007 — Index manquants sur les colonnes réellement filtrées
-- ----------------------------------------------------------------------------
-- Le schéma d'origine indexe bien site / date / statut. Manquent les colonnes
-- utilisées par les écrans réels (maquette du cycle 1) et par les contrôles :
--   * recherche d'article par son nom, au clavier, pendant qu'un client attend
--     (cible : moins de 3 secondes — UX_BASELINE.md, critère k11) ;
--   * clôture de caisse : ventes encaissées d'une journée, par caissier ;
--   * qui a fait quoi : mouvements et comptages par utilisateur ;
--   * dépenses de salaire par employé.
--
-- Cycle 2 — chantier C1. Idempotent.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Recherche d'article par nom, insensible à la casse et « contient »
-- (pg_trgm est une extension standard de PostgreSQL)
-- ----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_articles_nom_trgm
  ON articles USING GIN (lower(nom) gin_trgm_ops);

COMMENT ON INDEX idx_articles_nom_trgm IS
  'Recherche « contient » sur le nom d''article (lower(nom) LIKE ''%%ciment%%'') '
  'sans balayage complet : sert la saisie rapide de l''écran de vente.';

-- Catalogue d'un site, articles actifs seulement : la liste par défaut.
CREATE INDEX IF NOT EXISTS idx_articles_site_actif
  ON articles (site_id, nom) WHERE actif = TRUE;

-- Alerte de stock faible : peu de lignes, interrogée à chaque tableau de bord.
CREATE INDEX IF NOT EXISTS idx_articles_stock_faible
  ON articles (site_id) WHERE quantite_stock <= seuil_alerte AND actif = TRUE;

-- ----------------------------------------------------------------------------
-- Ventes : clôture de caisse, suivi par caissier, recherche par facturier
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_ventes_encaissement
  ON ventes (date_encaissement, site_id) WHERE statut = 'payee';

CREATE INDEX IF NOT EXISTS idx_ventes_caissier
  ON ventes (utilisateur_caisse_id, date_encaissement);

CREATE INDEX IF NOT EXISTS idx_ventes_saisisseur
  ON ventes (utilisateur_id, date_vente);

CREATE INDEX IF NOT EXISTS idx_ventes_mode_paiement
  ON ventes (mode_paiement, date_encaissement) WHERE statut = 'payee';

CREATE INDEX IF NOT EXISTS idx_ventes_lignes_article
  ON ventes_lignes (article_id);

-- ----------------------------------------------------------------------------
-- Comptabilité
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_transactions_type_date
  ON transactions (type, date_transaction, site_id);

CREATE INDEX IF NOT EXISTS idx_transactions_employe
  ON transactions (employe_id) WHERE employe_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_transactions_utilisateur
  ON transactions (utilisateur_id, date_transaction);

-- ----------------------------------------------------------------------------
-- Qui a fait quoi (traçabilité anti-vol)
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_mouvements_utilisateur
  ON mouvements_stock (utilisateur_id, date_mouvement);

CREATE INDEX IF NOT EXISTS idx_mouvements_type_date
  ON mouvements_stock (type, date_mouvement);

CREATE INDEX IF NOT EXISTS idx_comptages_utilisateur
  ON comptages_stock (utilisateur_id, date_comptage);

-- Écarts d'inventaire non nuls : la requête du tableau de bord responsable.
CREATE INDEX IF NOT EXISTS idx_comptages_ecarts
  ON comptages_stock (date_comptage, article_id) WHERE ecart <> 0;

CREATE INDEX IF NOT EXISTS idx_historique_prix_date
  ON historique_prix_articles (date_modification);

CREATE INDEX IF NOT EXISTS idx_historique_prix_utilisateur
  ON historique_prix_articles (utilisateur_id, date_modification);

CREATE INDEX IF NOT EXISTS idx_historique_modif_date
  ON historique_modifications_articles (date_modification);

-- ----------------------------------------------------------------------------
-- Comptes
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_utilisateurs_role_site
  ON utilisateurs (role, site_id) WHERE actif = TRUE;

INSERT INTO schema_migrations (version, nom)
VALUES ('007', 'index_recherche')
ON CONFLICT (version) DO NOTHING;
