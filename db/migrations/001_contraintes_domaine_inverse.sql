-- ============================================================================
-- 001 INVERSE — retire les contraintes de domaine
-- ============================================================================

ALTER TABLE utilisateurs    DROP CONSTRAINT IF EXISTS chk_utilisateurs_identifiant_non_vide;
ALTER TABLE utilisateurs    DROP CONSTRAINT IF EXISTS chk_utilisateurs_tentatives_positives;
ALTER TABLE utilisateurs    DROP CONSTRAINT IF EXISTS chk_utilisateurs_role_site;

ALTER TABLE articles        DROP CONSTRAINT IF EXISTS chk_articles_quantite_positive;
ALTER TABLE articles        DROP CONSTRAINT IF EXISTS chk_articles_prix_achat_positif;
ALTER TABLE articles        DROP CONSTRAINT IF EXISTS chk_articles_prix_vente_positif;
ALTER TABLE articles        DROP CONSTRAINT IF EXISTS chk_articles_seuil_positif;
ALTER TABLE articles        DROP CONSTRAINT IF EXISTS chk_articles_nom_non_vide;
ALTER TABLE articles        DROP CONSTRAINT IF EXISTS chk_articles_unite_non_vide;

ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_quantite_positive;

ALTER TABLE ventes          DROP CONSTRAINT IF EXISTS chk_ventes_montants_positifs;
ALTER TABLE ventes          DROP CONSTRAINT IF EXISTS chk_ventes_taux_tva_borne;
ALTER TABLE ventes          DROP CONSTRAINT IF EXISTS chk_ventes_coherence_totaux;
ALTER TABLE ventes          DROP CONSTRAINT IF EXISTS chk_ventes_tva_nulle_si_taux_nul;
ALTER TABLE ventes          DROP CONSTRAINT IF EXISTS chk_ventes_numero_facture_coherent;
ALTER TABLE ventes          DROP CONSTRAINT IF EXISTS chk_ventes_payee_complete;

ALTER TABLE ventes_lignes   DROP CONSTRAINT IF EXISTS chk_ventes_lignes_quantite_positive;
ALTER TABLE ventes_lignes   DROP CONSTRAINT IF EXISTS chk_ventes_lignes_prix_positif;

ALTER TABLE transactions    DROP CONSTRAINT IF EXISTS chk_transactions_montant_positif;

ALTER TABLE employes        DROP CONSTRAINT IF EXISTS chk_employes_salaire_positif;
ALTER TABLE absences_conges DROP CONSTRAINT IF EXISTS chk_absences_periode_coherente;
ALTER TABLE avances_salaire DROP CONSTRAINT IF EXISTS chk_avances_montant_positif;

ALTER TABLE comptages_stock DROP CONSTRAINT IF EXISTS chk_comptages_quantites_positives;

DELETE FROM schema_migrations WHERE version = '001';
