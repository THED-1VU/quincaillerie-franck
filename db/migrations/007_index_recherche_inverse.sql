-- ============================================================================
-- 007 INVERSE — retire les index ajoutés
-- ----------------------------------------------------------------------------
-- L'extension pg_trgm n'est PAS supprimée : elle peut servir ailleurs et sa
-- présence est sans effet de bord.
-- ============================================================================

DROP INDEX IF EXISTS idx_utilisateurs_role_site;
DROP INDEX IF EXISTS idx_historique_modif_date;
DROP INDEX IF EXISTS idx_historique_prix_utilisateur;
DROP INDEX IF EXISTS idx_historique_prix_date;
DROP INDEX IF EXISTS idx_comptages_ecarts;
DROP INDEX IF EXISTS idx_comptages_utilisateur;
DROP INDEX IF EXISTS idx_mouvements_type_date;
DROP INDEX IF EXISTS idx_mouvements_utilisateur;
DROP INDEX IF EXISTS idx_transactions_utilisateur;
DROP INDEX IF EXISTS idx_transactions_employe;
DROP INDEX IF EXISTS idx_transactions_type_date;
DROP INDEX IF EXISTS idx_ventes_lignes_article;
DROP INDEX IF EXISTS idx_ventes_mode_paiement;
DROP INDEX IF EXISTS idx_ventes_saisisseur;
DROP INDEX IF EXISTS idx_ventes_caissier;
DROP INDEX IF EXISTS idx_ventes_encaissement;
DROP INDEX IF EXISTS idx_articles_stock_faible;
DROP INDEX IF EXISTS idx_articles_site_actif;
DROP INDEX IF EXISTS idx_articles_nom_trgm;

DELETE FROM schema_migrations WHERE version = '007';
