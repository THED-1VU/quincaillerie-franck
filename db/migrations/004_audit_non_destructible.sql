-- ============================================================================
-- 004 — L'historique cesse d'être effaçable
-- ----------------------------------------------------------------------------
-- Diagnostic du cycle 2, prouvé par exécution : supprimer un article a EFFACÉ
-- son historique de prix (1 ligne → 0), par ON DELETE CASCADE. Dans un outil
-- dont la raison d'être est la traçabilité anti-vol, c'est la faille la plus
-- absurde : il suffisait de supprimer l'article pour effacer la preuve.
--
-- Trois verrous :
--   1. les ON DELETE CASCADE qui détruisent de l'historique deviennent RESTRICT ;
--   2. les journaux refusent toute suppression de ligne (déclencheur) ;
--   3. un article ne se supprime plus : il se DÉSACTIVE (suppression logique).
--
-- Ce qui n'est PAS décidé ici : le sort comptable d'une vente annulée
-- (suppression de la recette ou contre-passation) reste une question ouverte —
-- ADDENDUM_CAHIER_DES_CHARGES.md, points b et g. La table « transactions »
-- n'est donc volontairement pas verrouillée en suppression.
--
-- Cycle 2 — chantier C1. Idempotent.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. CASCADE → RESTRICT sur tout ce qui porte de l'historique
-- ----------------------------------------------------------------------------
ALTER TABLE historique_prix_articles
  DROP CONSTRAINT IF EXISTS historique_prix_articles_article_id_fkey,
  DROP CONSTRAINT IF EXISTS fk_historique_prix_article;
ALTER TABLE historique_prix_articles
  ADD CONSTRAINT fk_historique_prix_article
  FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE RESTRICT;

ALTER TABLE historique_modifications_articles
  DROP CONSTRAINT IF EXISTS historique_modifications_articles_article_id_fkey,
  DROP CONSTRAINT IF EXISTS fk_historique_modifications_article;
ALTER TABLE historique_modifications_articles
  ADD CONSTRAINT fk_historique_modifications_article
  FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE RESTRICT;

ALTER TABLE comptages_stock
  DROP CONSTRAINT IF EXISTS comptages_stock_article_id_fkey,
  DROP CONSTRAINT IF EXISTS fk_comptages_stock_article;
ALTER TABLE comptages_stock
  ADD CONSTRAINT fk_comptages_stock_article
  FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE RESTRICT;

ALTER TABLE ventes_lignes
  DROP CONSTRAINT IF EXISTS ventes_lignes_vente_id_fkey,
  DROP CONSTRAINT IF EXISTS fk_ventes_lignes_vente;
ALTER TABLE ventes_lignes
  ADD CONSTRAINT fk_ventes_lignes_vente
  FOREIGN KEY (vente_id) REFERENCES ventes(id) ON DELETE RESTRICT;

ALTER TABLE absences_conges
  DROP CONSTRAINT IF EXISTS absences_conges_employe_id_fkey,
  DROP CONSTRAINT IF EXISTS fk_absences_conges_employe;
ALTER TABLE absences_conges
  ADD CONSTRAINT fk_absences_conges_employe
  FOREIGN KEY (employe_id) REFERENCES employes(id) ON DELETE RESTRICT;

ALTER TABLE avances_salaire
  DROP CONSTRAINT IF EXISTS avances_salaire_employe_id_fkey,
  DROP CONSTRAINT IF EXISTS fk_avances_salaire_employe;
ALTER TABLE avances_salaire
  ADD CONSTRAINT fk_avances_salaire_employe
  FOREIGN KEY (employe_id) REFERENCES employes(id) ON DELETE RESTRICT;

-- ----------------------------------------------------------------------------
-- 2. Les journaux refusent la suppression
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION interdire_suppression_journal()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
      'La table « % » est un journal : ses lignes ne se suppriment pas.', TG_TABLE_NAME
      USING ERRCODE = 'restrict_violation';
END;
$$;

COMMENT ON FUNCTION interdire_suppression_journal() IS
  'Refuse toute suppression sur une table de journal (historiques, mouvements, '
  'comptages, ventes). Objectif anti-vol : une trace ne s''efface pas.';

DROP TRIGGER IF EXISTS trg_journal_non_supprimable ON historique_prix_articles;
CREATE TRIGGER trg_journal_non_supprimable
  BEFORE DELETE ON historique_prix_articles
  FOR EACH ROW EXECUTE FUNCTION interdire_suppression_journal();

DROP TRIGGER IF EXISTS trg_journal_non_supprimable ON historique_modifications_articles;
CREATE TRIGGER trg_journal_non_supprimable
  BEFORE DELETE ON historique_modifications_articles
  FOR EACH ROW EXECUTE FUNCTION interdire_suppression_journal();

DROP TRIGGER IF EXISTS trg_journal_non_supprimable ON mouvements_stock;
CREATE TRIGGER trg_journal_non_supprimable
  BEFORE DELETE ON mouvements_stock
  FOR EACH ROW EXECUTE FUNCTION interdire_suppression_journal();

DROP TRIGGER IF EXISTS trg_journal_non_supprimable ON comptages_stock;
CREATE TRIGGER trg_journal_non_supprimable
  BEFORE DELETE ON comptages_stock
  FOR EACH ROW EXECUTE FUNCTION interdire_suppression_journal();

-- Une vente ne se supprime pas : elle s'annule (cahier des charges §3.3).
DROP TRIGGER IF EXISTS trg_journal_non_supprimable ON ventes;
CREATE TRIGGER trg_journal_non_supprimable
  BEFORE DELETE ON ventes
  FOR EACH ROW EXECUTE FUNCTION interdire_suppression_journal();

-- Une ligne d'une vente déjà encaissée ou annulée est figée. Tant que la vente
-- est « en_attente », la composition du panier reste modifiable.
CREATE OR REPLACE FUNCTION interdire_suppression_ligne_vente_figee()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    statut_vente VARCHAR(20);
BEGIN
    SELECT statut INTO statut_vente FROM ventes WHERE id = OLD.vente_id;
    IF statut_vente IN ('payee', 'annulee') THEN
        RAISE EXCEPTION
          'Vente % : document déjà % — ses lignes ne se suppriment plus.',
          OLD.vente_id, statut_vente
          USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN OLD;
END;
$$;

DROP TRIGGER IF EXISTS trg_ligne_vente_figee ON ventes_lignes;
CREATE TRIGGER trg_ligne_vente_figee
  BEFORE DELETE ON ventes_lignes
  FOR EACH ROW EXECUTE FUNCTION interdire_suppression_ligne_vente_figee();

-- ----------------------------------------------------------------------------
-- 3. Suppression logique des articles
-- ----------------------------------------------------------------------------
ALTER TABLE articles ADD COLUMN IF NOT EXISTS actif BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS date_desactivation TIMESTAMP;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS desactive_par_id INTEGER;

ALTER TABLE articles DROP CONSTRAINT IF EXISTS fk_articles_desactive_par;
ALTER TABLE articles ADD  CONSTRAINT fk_articles_desactive_par
  FOREIGN KEY (desactive_par_id) REFERENCES utilisateurs(id) ON DELETE RESTRICT;

ALTER TABLE articles DROP CONSTRAINT IF EXISTS chk_articles_desactivation_coherente;
ALTER TABLE articles ADD  CONSTRAINT chk_articles_desactivation_coherente
  CHECK (
    (actif = TRUE  AND date_desactivation IS NULL AND desactive_par_id IS NULL)
    OR
    (actif = FALSE AND date_desactivation IS NOT NULL AND desactive_par_id IS NOT NULL)
  );

COMMENT ON COLUMN articles.actif IS
  'Suppression LOGIQUE. Un article qui a servi (vente, mouvement, comptage, '
  'historique de prix) ne se supprime pas : on le désactive, avec l''auteur et '
  'la date. Son passé reste consultable.';

-- Les utilisateurs se désactivent déjà (colonne actif) ; on trace de la même
-- façon les employés, pour ne jamais avoir à supprimer une fiche RH.
ALTER TABLE employes ADD COLUMN IF NOT EXISTS date_desactivation TIMESTAMP;

INSERT INTO schema_migrations (version, nom)
VALUES ('004', 'audit_non_destructible')
ON CONFLICT (version) DO NOTHING;
