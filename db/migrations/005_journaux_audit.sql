-- ============================================================================
-- 005 — Journaux d'audit manquants
-- ----------------------------------------------------------------------------
-- Diagnostic du cycle 2, prouvé par exécution : la base ne contient AUCUNE
-- table de journal ou d'audit (0 résultat), et une vente passe au statut
-- « annulee » sans que l'on sache qui l'a annulée, quand, ni pourquoi — alors
-- que le cahier des charges §3.3 réserve l'annulation au responsable et §4.2
-- exige que les ventes annulées soient tracées.
--
-- Trois ajouts :
--   * journal_connexions — connexions et ÉCHECS de connexion ;
--   * journal_comptes    — création, désactivation, changement de rôle ou de site ;
--   * l'annulation d'une vente devient traçable et IRRÉVERSIBLE.
--
-- Cycle 2 — chantier C1. Idempotent.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- journal_connexions
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS journal_connexions (
    id                SERIAL PRIMARY KEY,
    identifiant_saisi VARCHAR(50)  NOT NULL,
    utilisateur_id    INTEGER      REFERENCES utilisateurs(id) ON DELETE RESTRICT,
    succes            BOOLEAN      NOT NULL,
    motif_echec       VARCHAR(60)  CHECK (motif_echec IN (
                          'identifiant_inconnu', 'mot_de_passe_incorrect',
                          'compte_desactive', 'compte_verrouille', 'autre')),
    adresse_ip        VARCHAR(45),
    poste             VARCHAR(100),
    date_tentative    TIMESTAMP    NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_journal_connexions_motif CHECK (
        (succes = TRUE  AND motif_echec IS NULL AND utilisateur_id IS NOT NULL)
        OR
        (succes = FALSE AND motif_echec IS NOT NULL)
    )
);

COMMENT ON TABLE journal_connexions IS
  'Toutes les tentatives de connexion, réussies ET échouées. Sert au '
  'verrouillage après plusieurs échecs (cahier des charges §3.1) et à repérer '
  'une tentative d''intrusion. utilisateur_id est NULL si l''identifiant saisi '
  'n''existe pas.';

CREATE INDEX IF NOT EXISTS idx_journal_connexions_date
  ON journal_connexions (date_tentative);
CREATE INDEX IF NOT EXISTS idx_journal_connexions_identifiant
  ON journal_connexions (identifiant_saisi, date_tentative);
CREATE INDEX IF NOT EXISTS idx_journal_connexions_echecs
  ON journal_connexions (utilisateur_id, date_tentative) WHERE succes = FALSE;

-- ----------------------------------------------------------------------------
-- journal_comptes
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS journal_comptes (
    id                   SERIAL PRIMARY KEY,
    utilisateur_cible_id INTEGER      NOT NULL REFERENCES utilisateurs(id) ON DELETE RESTRICT,
    action               VARCHAR(40)  NOT NULL CHECK (action IN (
                             'creation', 'desactivation', 'reactivation',
                             'changement_role', 'changement_site',
                             'reinitialisation_mot_de_passe', 'deverrouillage',
                             'changement_identifiant')),
    ancienne_valeur      VARCHAR(100),
    nouvelle_valeur      VARCHAR(100),
    utilisateur_auteur_id INTEGER     NOT NULL REFERENCES utilisateurs(id) ON DELETE RESTRICT,
    date_action          TIMESTAMP    NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE journal_comptes IS
  'Cycle de vie des comptes : qui a créé, désactivé, réactivé, déverrouillé, '
  'changé le rôle ou le site de qui, et quand. Sans ce journal, un responsable '
  'peut déplacer un compte d''un site à l''autre sans laisser de trace.';

CREATE INDEX IF NOT EXISTS idx_journal_comptes_cible
  ON journal_comptes (utilisateur_cible_id, date_action);
CREATE INDEX IF NOT EXISTS idx_journal_comptes_date
  ON journal_comptes (date_action);

-- Ces deux journaux ne se suppriment pas non plus (fonction créée en 004).
DROP TRIGGER IF EXISTS trg_journal_non_supprimable ON journal_connexions;
CREATE TRIGGER trg_journal_non_supprimable
  BEFORE DELETE ON journal_connexions
  FOR EACH ROW EXECUTE FUNCTION interdire_suppression_journal();

DROP TRIGGER IF EXISTS trg_journal_non_supprimable ON journal_comptes;
CREATE TRIGGER trg_journal_non_supprimable
  BEFORE DELETE ON journal_comptes
  FOR EACH ROW EXECUTE FUNCTION interdire_suppression_journal();

-- ----------------------------------------------------------------------------
-- Annulation d'une vente : tracée, horodatée par la base, irréversible
-- ----------------------------------------------------------------------------
ALTER TABLE ventes ADD COLUMN IF NOT EXISTS annulee_par_id   INTEGER;
ALTER TABLE ventes ADD COLUMN IF NOT EXISTS date_annulation  TIMESTAMP;
ALTER TABLE ventes ADD COLUMN IF NOT EXISTS motif_annulation VARCHAR(200);

ALTER TABLE ventes DROP CONSTRAINT IF EXISTS fk_ventes_annulee_par;
ALTER TABLE ventes ADD  CONSTRAINT fk_ventes_annulee_par
  FOREIGN KEY (annulee_par_id) REFERENCES utilisateurs(id) ON DELETE RESTRICT;

ALTER TABLE ventes DROP CONSTRAINT IF EXISTS chk_ventes_annulation_tracee;
ALTER TABLE ventes ADD  CONSTRAINT chk_ventes_annulation_tracee
  CHECK (
    (statut <> 'annulee' AND annulee_par_id IS NULL AND date_annulation IS NULL)
    OR
    (statut =  'annulee' AND annulee_par_id IS NOT NULL AND date_annulation IS NOT NULL)
  );

COMMENT ON COLUMN ventes.annulee_par_id IS
  'Qui a annulé la vente. Le cahier des charges §3.3 réserve l''annulation au '
  'responsable ; cette colonne rend la règle vérifiable a posteriori.';

CREATE OR REPLACE FUNCTION controler_changement_statut_vente()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Une vente annulée est un document clos : plus aucune modification.
    IF OLD.statut = 'annulee' THEN
        IF NEW.statut            IS DISTINCT FROM OLD.statut
        OR NEW.annulee_par_id    IS DISTINCT FROM OLD.annulee_par_id
        OR NEW.date_annulation   IS DISTINCT FROM OLD.date_annulation
        OR NEW.total_ttc         IS DISTINCT FROM OLD.total_ttc
        OR NEW.sous_total_ht     IS DISTINCT FROM OLD.sous_total_ht THEN
            RAISE EXCEPTION
              'Vente % déjà annulée le % : elle ne peut pas l''être une seconde fois, '
              'ni être modifiée.', OLD.id, OLD.date_annulation
              USING ERRCODE = 'restrict_violation';
        END IF;
        RETURN NEW;
    END IF;

    -- Transitions autorisées : en_attente → payee, en_attente → annulee,
    -- payee → annulee. Tout le reste est refusé (on ne « dé-encaisse » pas).
    IF NEW.statut IS DISTINCT FROM OLD.statut THEN
        IF NOT (
            (OLD.statut = 'en_attente' AND NEW.statut IN ('payee', 'annulee'))
            OR
            (OLD.statut = 'payee'      AND NEW.statut = 'annulee')
        ) THEN
            RAISE EXCEPTION
              'Passage de statut « % » vers « % » interdit sur la vente %.',
              OLD.statut, NEW.statut, OLD.id
              USING ERRCODE = 'restrict_violation';
        END IF;
    END IF;

    -- La date d'annulation est posée par la BASE, jamais par le client :
    -- elle ne peut donc pas être antidatée.
    -- (À l'inverse, date_encaissement reste fournie par le client : une vente
    --  est saisie APRÈS l'encaissement réel, d'après le facturier papier.)
    IF NEW.statut = 'annulee' THEN
        NEW.date_annulation := NOW();
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION controler_changement_statut_vente() IS
  'Fait respecter le cycle de vie d''une vente : transitions autorisées, '
  'annulation unique et irréversible, date d''annulation posée par la base '
  '(donc non antidatable).';

DROP TRIGGER IF EXISTS trg_statut_vente ON ventes;
CREATE TRIGGER trg_statut_vente
  BEFORE UPDATE ON ventes
  FOR EACH ROW EXECUTE FUNCTION controler_changement_statut_vente();

INSERT INTO schema_migrations (version, nom)
VALUES ('005', 'journaux_audit')
ON CONFLICT (version) DO NOTHING;
