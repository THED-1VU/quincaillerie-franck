-- ============================================================================
-- 004 INVERSE — l'historique redevient effaçable (comportement d'origine)
-- ============================================================================

-- 3. Suppression logique
ALTER TABLE employes DROP COLUMN IF EXISTS date_desactivation;
ALTER TABLE articles DROP CONSTRAINT IF EXISTS chk_articles_desactivation_coherente;
ALTER TABLE articles DROP CONSTRAINT IF EXISTS fk_articles_desactive_par;
ALTER TABLE articles DROP COLUMN IF EXISTS desactive_par_id;
ALTER TABLE articles DROP COLUMN IF EXISTS date_desactivation;
ALTER TABLE articles DROP COLUMN IF EXISTS actif;

-- 2. Verrous de suppression
DROP TRIGGER  IF EXISTS trg_ligne_vente_figee ON ventes_lignes;
DROP FUNCTION IF EXISTS interdire_suppression_ligne_vente_figee();

DROP TRIGGER IF EXISTS trg_journal_non_supprimable ON ventes;
DROP TRIGGER IF EXISTS trg_journal_non_supprimable ON comptages_stock;
DROP TRIGGER IF EXISTS trg_journal_non_supprimable ON mouvements_stock;
DROP TRIGGER IF EXISTS trg_journal_non_supprimable ON historique_modifications_articles;
DROP TRIGGER IF EXISTS trg_journal_non_supprimable ON historique_prix_articles;
DROP FUNCTION IF EXISTS interdire_suppression_journal();

-- 1. RESTRICT → CASCADE (état d'origine)
ALTER TABLE avances_salaire DROP CONSTRAINT IF EXISTS fk_avances_salaire_employe;
ALTER TABLE avances_salaire ADD  CONSTRAINT avances_salaire_employe_id_fkey
  FOREIGN KEY (employe_id) REFERENCES employes(id) ON DELETE CASCADE;

ALTER TABLE absences_conges DROP CONSTRAINT IF EXISTS fk_absences_conges_employe;
ALTER TABLE absences_conges ADD  CONSTRAINT absences_conges_employe_id_fkey
  FOREIGN KEY (employe_id) REFERENCES employes(id) ON DELETE CASCADE;

ALTER TABLE ventes_lignes DROP CONSTRAINT IF EXISTS fk_ventes_lignes_vente;
ALTER TABLE ventes_lignes ADD  CONSTRAINT ventes_lignes_vente_id_fkey
  FOREIGN KEY (vente_id) REFERENCES ventes(id) ON DELETE CASCADE;

ALTER TABLE comptages_stock DROP CONSTRAINT IF EXISTS fk_comptages_stock_article;
ALTER TABLE comptages_stock ADD  CONSTRAINT comptages_stock_article_id_fkey
  FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE;

ALTER TABLE historique_modifications_articles DROP CONSTRAINT IF EXISTS fk_historique_modifications_article;
ALTER TABLE historique_modifications_articles ADD  CONSTRAINT historique_modifications_articles_article_id_fkey
  FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE;

ALTER TABLE historique_prix_articles DROP CONSTRAINT IF EXISTS fk_historique_prix_article;
ALTER TABLE historique_prix_articles ADD  CONSTRAINT historique_prix_articles_article_id_fkey
  FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE;

DELETE FROM schema_migrations WHERE version = '004';
