-- ============================================================================
-- 006 — Paramètres applicatifs
-- ----------------------------------------------------------------------------
-- Diagnostic du cycle 2, prouvé par exécution : aucune table de paramètres.
-- Le taux de TVA, l'identité de la boutique, la règle du seuil d'alerte et le
-- seuil de verrouillage n'existent donc nulle part — ils sont écrits en dur
-- dans un code que plus personne ne possède.
--
-- RÈGLE APPLIQUÉE ICI : on ne devine JAMAIS une règle métier non tranchée.
-- Les paramètres dont la valeur dépend d'une décision du propriétaire sont
-- amorcés à la valeur sentinelle « a_definir » et signalés par a_decider = TRUE.
-- La fonction parametre_texte() REFUSE de renvoyer une valeur « a_definir » :
-- l'application s'arrête franchement au lieu d'appliquer en silence une règle
-- inventée (par exemple un taux de TVA).
--
-- L'application doit pouvoir tourner SANS AUCUNE TVA : taux_tva vaut 0 par
-- défaut, ce qui est une valeur utilisable, pas une valeur à deviner.
--
-- Cycle 2 — chantier C1. Idempotent.
-- ============================================================================

CREATE TABLE IF NOT EXISTS parametres (
    cle              VARCHAR(60)  PRIMARY KEY,
    valeur           TEXT         NOT NULL,
    type_valeur      VARCHAR(10)  NOT NULL DEFAULT 'texte'
                     CHECK (type_valeur IN ('texte', 'entier', 'decimal', 'booleen')),
    description      VARCHAR(300) NOT NULL,
    modifiable       BOOLEAN      NOT NULL DEFAULT TRUE,
    a_decider        BOOLEAN      NOT NULL DEFAULT FALSE,
    reference_decision VARCHAR(80),
    date_modification TIMESTAMP   NOT NULL DEFAULT NOW(),
    utilisateur_id   INTEGER      REFERENCES utilisateurs(id) ON DELETE RESTRICT
);

COMMENT ON TABLE parametres IS
  'Réglages de l''application. Rien de ce qui est ici ne doit être écrit en dur '
  'dans le code. a_decider = TRUE : le propriétaire doit trancher (voir '
  'reference_decision et ADDENDUM_CAHIER_DES_CHARGES.md).';
COMMENT ON COLUMN parametres.a_decider IS
  'TRUE tant que le propriétaire n''a pas tranché. La valeur présente est une '
  'proposition ou la sentinelle « a_definir », jamais une règle métier inventée.';

CREATE TABLE IF NOT EXISTS historique_parametres (
    id                SERIAL PRIMARY KEY,
    cle               VARCHAR(60)  NOT NULL,
    ancienne_valeur   TEXT         NOT NULL,
    nouvelle_valeur   TEXT         NOT NULL,
    utilisateur_id    INTEGER      REFERENCES utilisateurs(id) ON DELETE RESTRICT,
    date_modification TIMESTAMP    NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE historique_parametres IS
  'Tout changement de paramètre est tracé : un taux de TVA ou un seuil modifié '
  'en douce doit rester visible.';

CREATE INDEX IF NOT EXISTS idx_historique_parametres_cle
  ON historique_parametres (cle, date_modification);

DROP TRIGGER IF EXISTS trg_journal_non_supprimable ON historique_parametres;
CREATE TRIGGER trg_journal_non_supprimable
  BEFORE DELETE ON historique_parametres
  FOR EACH ROW EXECUTE FUNCTION interdire_suppression_journal();

-- ----------------------------------------------------------------------------
-- Traçage automatique + refus de modifier un paramètre verrouillé
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION tracer_modification_parametre()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.valeur IS DISTINCT FROM OLD.valeur THEN
        IF OLD.modifiable = FALSE THEN
            RAISE EXCEPTION 'Le paramètre « % » n''est pas modifiable.', OLD.cle
              USING ERRCODE = 'restrict_violation';
        END IF;
        INSERT INTO historique_parametres (cle, ancienne_valeur, nouvelle_valeur, utilisateur_id)
        VALUES (OLD.cle, OLD.valeur, NEW.valeur, NEW.utilisateur_id);
        NEW.date_modification := NOW();
        -- Une valeur réellement saisie lève la mention « à décider ».
        IF NEW.valeur <> 'a_definir' THEN
            NEW.a_decider := FALSE;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_tracer_parametre ON parametres;
CREATE TRIGGER trg_tracer_parametre
  BEFORE UPDATE ON parametres
  FOR EACH ROW EXECUTE FUNCTION tracer_modification_parametre();

-- ----------------------------------------------------------------------------
-- Lecture : refuse de livrer une décision qui n'a pas été prise
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION parametre_texte(p_cle VARCHAR)
RETURNS TEXT
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v TEXT;
    r VARCHAR(80);
BEGIN
    SELECT valeur, reference_decision INTO v, r FROM parametres WHERE cle = p_cle;
    IF v IS NULL THEN
        RAISE EXCEPTION 'Paramètre « % » inexistant.', p_cle USING ERRCODE = 'no_data_found';
    END IF;
    IF v = 'a_definir' THEN
        RAISE EXCEPTION
          'Paramètre « % » non tranché par le propriétaire (%). L''application '
          'ne doit pas inventer cette valeur.', p_cle, COALESCE(r, 'voir addendum')
          USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN v;
END;
$$;

CREATE OR REPLACE FUNCTION parametre_numerique(p_cle VARCHAR)
RETURNS NUMERIC
LANGUAGE sql
STABLE
AS $$ SELECT parametre_texte(p_cle)::NUMERIC $$;

COMMENT ON FUNCTION parametre_texte(VARCHAR) IS
  'Lit un paramètre. Lève une erreur explicite si la valeur est encore '
  '« a_definir » : mieux vaut un arrêt franc qu''une règle métier inventée.';

CREATE OR REPLACE VIEW parametres_a_decider AS
  SELECT cle, valeur, description, reference_decision
    FROM parametres WHERE a_decider = TRUE
   ORDER BY cle;

COMMENT ON VIEW parametres_a_decider IS
  'Liste des décisions encore attendues du propriétaire. Doit être vide avant '
  'la mise en production.';

-- ----------------------------------------------------------------------------
-- Amorçage
-- ----------------------------------------------------------------------------
INSERT INTO parametres (cle, valeur, type_valeur, description, modifiable, a_decider, reference_decision) VALUES

-- Identité de la boutique (connue)
('boutique_nom', 'Ets Quincaillerie Franck', 'texte',
 'Raison sociale, imprimée sur les tickets et factures.', TRUE, FALSE, NULL),
('boutique_ville', 'Batouri', 'texte',
 'Ville, imprimée sur les documents.', TRUE, FALSE, NULL),
('boutique_telephone', 'a_definir', 'texte',
 'Téléphone imprimé sur les tickets et factures.', TRUE, TRUE, 'à fournir par le propriétaire'),
('boutique_numero_contribuable', 'a_definir', 'texte',
 'Numéro de contribuable, si les mentions légales l''exigent.', TRUE, TRUE, 'addendum point d'),

-- Fiscalité : AUCUNE valeur inventée
('regime_fiscal', 'a_definir', 'texte',
 'Régime fiscal réel : impot_liberatoire, simplifie ou reel (assujetti TVA). '
 'Tant que ce point n''est pas tranché, aucune TVA n''est appliquée.', TRUE, TRUE, 'addendum point d'),
('taux_tva', '0', 'decimal',
 'Taux de TVA en pourcentage. 0 = aucune TVA appliquée, ce qui est le '
 'fonctionnement par défaut et parfaitement valide.', TRUE, TRUE, 'addendum point d'),
('prix_saisis_ttc', 'a_definir', 'texte',
 'Les prix négociés avec le client sont-ils compris TTC (oui) ou HT (non) ?', TRUE, TRUE, 'addendum point d'),
('arrondi_montants', 'a_definir', 'texte',
 'Méthode d''arrondi au franc CFA (le FCFA n''a pas de sous-unité).', TRUE, TRUE, 'addendum point d'),
('devise', 'FCFA', 'texte',
 'Devise affichée.', FALSE, FALSE, NULL),

-- Stock
('seuil_alerte_pourcentage', '20', 'entier',
 'Pourcentage de la quantité reçue servant de seuil d''alerte, recalculé '
 'UNIQUEMENT lors d''une entrée de stock (cahier des charges §3.2).', TRUE, FALSE, NULL),
('seuil_alerte_plancher', '1', 'entier',
 'Seuil d''alerte minimal, quand 20 %% de la quantité reçue donnerait 0. '
 'Valeur proposée, à confirmer.', TRUE, TRUE, 'à confirmer par le propriétaire'),

-- Sécurité
('tentatives_max_connexion', '5', 'entier',
 'Nombre d''échecs consécutifs avant verrouillage du compte. Valeur proposée, '
 'à confirmer.', TRUE, TRUE, 'à confirmer par le propriétaire'),
('duree_session_minutes', 'a_definir', 'entier',
 'Durée d''inactivité au bout de laquelle la session se ferme.', TRUE, TRUE, 'dossier de recette §6, session inactive')

ON CONFLICT (cle) DO NOTHING;

INSERT INTO schema_migrations (version, nom)
VALUES ('006', 'parametres_applicatifs')
ON CONFLICT (version) DO NOTHING;
