-- ============================================================================
-- 045 — Point b : crédit client. clients, créances, règlements partiels.
-- ----------------------------------------------------------------------------
-- Décisions du propriétaire (instruction du 2026-09-25, après diagnostic) :
--   * une vente à crédit crée une créance, JAMAIS une recette encaissée ;
--   * plafond par client, 100 000 FCFA par défaut ;
--   * règlements partiels, alloués en FIFO contre les créances les plus
--     anciennes (aucune saisie de rapprochement au comptoir — le cahier
--     papier n'a jamais demandé ça non plus) ;
--   * encours et vieillissement (30/60/90 jours) au tableau de bord du
--     responsable ;
--   * aucune relance automatique, aucun intérêt ;
--   * client partagé entre les deux sites (site_id NULLABLE, même
--     convention que employes/vendeur_id, migration 040) ;
--   * fonction activable/désactivable par boutique (paramètre
--     credit_client_actif — c'est une gamme vendue à plusieurs boutiques,
--     chacune peut ne pas vouloir cette fonctionnalité) ;
--   * chargement initial des créances existantes prévu, au même titre que
--     le stock (point j, migration 041) — outil séparé,
--     db/outils/importer_creances_initiales.py.
--
-- Diagnostic préalable (trouvé par exécution, pas juste supposé) : le
-- schéma d'origine acceptait déjà mode_paiement = 'credit_client'
-- (QuincaillerieFranck_Test/creation_base_donnees.sql), la route
-- POST /ventes le refuse explicitement depuis le cycle 6 en attendant cette
-- décision, et calculer_attendu_caisse() (migration 019, clôture de
-- caisse) EXCLUT DÉJÀ credit_client de ses 4 totaux tout en laissant la
-- vente au statut 'payee' — le comportement demandé ici (vente enregistrée
-- normalement, décrément de stock normal, mais AUCUN impact sur la caisse)
-- était donc déjà câblé au niveau comptage de caisse depuis le cycle 10.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Table clients — partagée entre les deux sites (site_id purement
-- informatif : où le client a été enregistré, jamais un filtre RLS — un
-- client peut acheter à crédit sur l'un ou l'autre site).
-- ----------------------------------------------------------------------------
CREATE TABLE clients (
    id              SERIAL PRIMARY KEY,
    nom             VARCHAR(150) NOT NULL,
    telephone       VARCHAR(30),
    plafond_credit  NUMERIC(12,2) NOT NULL DEFAULT 100000,
    site_id         INTEGER REFERENCES sites(id),
    actif           BOOLEAN NOT NULL DEFAULT TRUE,
    date_creation   TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_clients_nom_non_vide CHECK (length(btrim(nom)) > 0),
    CONSTRAINT chk_clients_plafond_positif CHECK (plafond_credit >= 0)
);

COMMENT ON TABLE clients IS
  'Clients à crédit (addendum point b, décidé le 2026-09-25). Partagés entre '
  'les deux sites — site_id est informatif (où enregistré), jamais un filtre '
  'RLS. Jamais supprimés (comme articles/employes) : désactiver via actif.';

GRANT SELECT, INSERT, UPDATE ON clients TO qf_responsable;
GRANT SELECT ON clients TO qf_agent_comptabilite;
-- INSERT direct (pas de fonction SECURITY DEFINER, comme employes/rh.py) :
-- le rôle qui écrit a besoin d'USAGE sur la séquence elle-même — le GRANT
-- global de la migration 008 ne couvre que les séquences qui existaient à
-- ce moment-là, jamais celles créées par une migration ultérieure.
GRANT USAGE, SELECT ON SEQUENCE clients_id_seq TO qf_responsable;

-- ----------------------------------------------------------------------------
-- Table creances — une ligne par vente à crédit (vente_id) OU par reprise
-- de créance existante lors du chargement initial (vente_id NULL).
-- ----------------------------------------------------------------------------
CREATE TABLE creances (
    id              SERIAL PRIMARY KEY,
    client_id       INTEGER NOT NULL REFERENCES clients(id),
    vente_id        INTEGER REFERENCES ventes(id),
    site_id         INTEGER NOT NULL REFERENCES sites(id),
    montant         NUMERIC(12,2) NOT NULL,
    motif           VARCHAR(200),
    utilisateur_id  INTEGER NOT NULL REFERENCES utilisateurs(id),
    date_creance    TIMESTAMP NOT NULL DEFAULT NOW(),
    annulee         BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT chk_creances_montant_positif CHECK (montant > 0)
);

CREATE INDEX idx_creances_client ON creances(client_id, date_creance);

COMMENT ON TABLE creances IS
  'Une ligne par vente à crédit (vente_id) ou par créance reprise du cahier '
  'papier au chargement initial (vente_id NULL, voir enregistrer_creance_initiale). '
  'Journal non destructible (jamais supprimée), comme mouvements_stock/ventes — '
  'seule transition permise : annulee passe à TRUE via annuler_vente() '
  '(cas limite addendum point b « vente à crédit annulée »), jamais une '
  'autre colonne, jamais en dehors de cette fonction. Une créance déjà '
  'entamée par un règlement (allocation FIFO) refuse cette transition — '
  'cas volontairement non traité (addendum point b : « à définir »).';

-- Écrite directement par POST /ventes (comme transactions, catégorie
-- 'recette') quand mode_paiement = 'credit_client' — pas de fonction
-- SECURITY DEFINER dédiée pour ce chemin, même style que l'insertion dans
-- transactions juste à côté dans ventes.py.
GRANT SELECT, INSERT ON creances TO qf_responsable, qf_agent_comptabilite;
GRANT USAGE, SELECT ON SEQUENCE creances_id_seq TO qf_responsable, qf_agent_comptabilite;

DROP TRIGGER IF EXISTS trg_journal_non_supprimable ON creances;
CREATE TRIGGER trg_journal_non_supprimable
  BEFORE DELETE ON creances
  FOR EACH ROW EXECUTE FUNCTION interdire_suppression_journal();

-- ----------------------------------------------------------------------------
-- Table reglements_creances — un versement partiel ou total, JAMAIS lié à
-- une créance précise (allocation FIFO au moment de la lecture, pas à la
-- saisie — le cahier papier ne demande jamais au client quelle vente il
-- règle).
-- ----------------------------------------------------------------------------
CREATE TABLE reglements_creances (
    id              SERIAL PRIMARY KEY,
    client_id       INTEGER NOT NULL REFERENCES clients(id),
    montant         NUMERIC(12,2) NOT NULL,
    motif           VARCHAR(200),
    encaisse_par_id INTEGER NOT NULL REFERENCES utilisateurs(id),
    date_reglement  TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_reglements_montant_positif CHECK (montant > 0)
);

CREATE INDEX idx_reglements_client ON reglements_creances(client_id, date_reglement);

COMMENT ON TABLE reglements_creances IS
  'Versements contre l''encours total d''un client (pas contre une créance '
  'précise) — allocation FIFO calculée à la lecture par vieillissement_creances(). '
  'Écrite UNIQUEMENT par enregistrer_reglement_creance() (SECURITY DEFINER) : '
  'aucun GRANT INSERT direct.';

GRANT SELECT ON reglements_creances TO qf_responsable, qf_agent_comptabilite;

DROP TRIGGER IF EXISTS trg_journal_non_supprimable ON reglements_creances;
CREATE TRIGGER trg_journal_non_supprimable
  BEFORE DELETE ON reglements_creances
  FOR EACH ROW EXECUTE FUNCTION interdire_suppression_journal();

-- ----------------------------------------------------------------------------
-- Paramètre d'activation — par boutique (gamme, chaque déploiement décide).
-- 'oui' ici : la boutique de Franck a un besoin réel et documenté (15 à 25
-- clients débiteurs, addendum point b).
-- ----------------------------------------------------------------------------
INSERT INTO parametres (cle, valeur, type_valeur, description, modifiable, a_decider, reference_decision)
VALUES
('credit_client_actif', 'oui', 'texte',
 'Active ou désactive la vente à crédit (clients, créances, règlements) '
 'pour cette boutique — produit vendu en gamme, chaque déploiement décide '
 'indépendamment (addendum point b, décidé le 2026-09-25).',
 TRUE, FALSE, 'décision du propriétaire, 2026-09-25 (addendum point b)')
ON CONFLICT (cle) DO NOTHING;

-- ----------------------------------------------------------------------------
-- encours_client() — encours actuel d'un client (créances - règlements).
-- STABLE, pas SECURITY DEFINER : qf_responsable et qf_agent_comptabilite
-- ont déjà SELECT sur les deux tables sources (même principe que
-- calculer_attendu_caisse, migration 019).
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION encours_client(p_client_id INTEGER)
RETURNS NUMERIC(12,2)
LANGUAGE sql
STABLE
AS $$
    SELECT COALESCE((SELECT SUM(montant) FROM creances WHERE client_id = p_client_id AND NOT annulee), 0)
         - COALESCE((SELECT SUM(montant) FROM reglements_creances WHERE client_id = p_client_id), 0);
$$;

COMMENT ON FUNCTION encours_client(INTEGER) IS
  'Encours actuel = somme des créances - somme des règlements, pour un client. '
  'Utilisée pour le plafond à la vente ET pour la colonne encours de '
  'l''écran Clients.';

REVOKE ALL ON FUNCTION encours_client(INTEGER) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION encours_client(INTEGER) TO qf_responsable, qf_agent_comptabilite;

-- ----------------------------------------------------------------------------
-- vieillissement_creances() — encours restant par tranche d'ancienneté
-- (0-30 / 31-60 / 61-90 / 91+ jours), allocation FIFO des règlements contre
-- les créances les plus anciennes de CHAQUE client. Carte du tableau de
-- bord du responsable.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION vieillissement_creances()
RETURNS TABLE(tranche VARCHAR, montant NUMERIC)
LANGUAGE sql
STABLE
AS $$
    WITH cumul AS (
        SELECT c.id, c.client_id, c.montant, c.date_creance,
               COALESCE(
                 SUM(c.montant) OVER (PARTITION BY c.client_id
                                       ORDER BY c.date_creance, c.id
                                       ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),
                 0
               ) AS cumul_avant
          FROM creances c
         WHERE NOT c.annulee
    ),
    regle AS (
        SELECT client_id, SUM(montant) AS total_regle
          FROM reglements_creances
         GROUP BY client_id
    ),
    restant AS (
        SELECT cu.date_creance,
               GREATEST(0, cu.montant - GREATEST(0, COALESCE(r.total_regle, 0) - cu.cumul_avant)) AS montant_restant
          FROM cumul cu
          LEFT JOIN regle r ON r.client_id = cu.client_id
    )
    SELECT
      CASE
        WHEN CURRENT_DATE - date_creance::date <= 30 THEN '0-30'
        WHEN CURRENT_DATE - date_creance::date <= 60 THEN '31-60'
        WHEN CURRENT_DATE - date_creance::date <= 90 THEN '61-90'
        ELSE '91+'
      END AS tranche,
      SUM(montant_restant) AS montant
      FROM restant
     WHERE montant_restant > 0
     GROUP BY 1;
$$;

COMMENT ON FUNCTION vieillissement_creances() IS
  'Encours restant par tranche d''ancienneté (0-30/31-60/61-90/91+ jours), '
  'FIFO : chaque règlement d''un client éteint d''abord sa créance la plus '
  'ancienne — aucune saisie de rapprochement demandée au comptoir, comme le '
  'cahier papier. Carte du tableau de bord du responsable.';

REVOKE ALL ON FUNCTION vieillissement_creances() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION vieillissement_creances() TO qf_responsable;

-- ----------------------------------------------------------------------------
-- enregistrer_reglement_creance() — seul point d'écriture de
-- reglements_creances. Refuse un montant qui dépasse l'encours actuel du
-- client (pas de solde créditeur, aucune avance) — minimalisme demandé
-- (« aucune relance automatique, aucun intérêt »). Un client désactivé peut
-- quand même régler ce qu'il doit encore.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION enregistrer_reglement_creance(
    p_client_id      INTEGER,
    p_montant        NUMERIC,
    p_utilisateur_id INTEGER,
    p_motif          VARCHAR DEFAULT NULL
) RETURNS NUMERIC(12,2)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_encours NUMERIC(12,2);
BEGIN
    IF p_montant IS NULL OR p_montant <= 0 THEN
        RAISE EXCEPTION 'Montant de règlement invalide : %.', p_montant USING ERRCODE = 'check_violation';
    END IF;
    PERFORM 1 FROM clients WHERE id = p_client_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Client % introuvable.', p_client_id USING ERRCODE = 'foreign_key_violation';
    END IF;

    v_encours := encours_client(p_client_id);
    IF p_montant > v_encours THEN
        RAISE EXCEPTION 'Le règlement (%) dépasse l''encours du client (%).', p_montant, v_encours
          USING ERRCODE = 'check_violation';
    END IF;

    INSERT INTO reglements_creances (client_id, montant, encaisse_par_id, motif)
    VALUES (p_client_id, p_montant, p_utilisateur_id, p_motif);

    RETURN encours_client(p_client_id);
END;
$$;

COMMENT ON FUNCTION enregistrer_reglement_creance(INTEGER, NUMERIC, INTEGER, VARCHAR) IS
  'Seul point d''écriture de reglements_creances. Refuse un règlement qui '
  'dépasserait l''encours actuel du client (pas d''avance ni de solde créditeur).';

REVOKE ALL ON FUNCTION enregistrer_reglement_creance(INTEGER, NUMERIC, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION enregistrer_reglement_creance(INTEGER, NUMERIC, INTEGER, VARCHAR)
  TO qf_responsable, qf_agent_comptabilite;

-- ----------------------------------------------------------------------------
-- enregistrer_creance_initiale() — chargement du solde de départ d'un
-- client (reprise du cahier papier, point b/j), sans vente_id — même esprit
-- que enregistrer_inventaire_initial() (migration 041, point j). Réservée à
-- qf_responsable (l'import est mené avec un compte responsable, comme le
-- chargement du stock initial).
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION enregistrer_creance_initiale(
    p_client_id      INTEGER,
    p_montant        NUMERIC,
    p_site_id        INTEGER,
    p_utilisateur_id INTEGER,
    p_motif          VARCHAR
) RETURNS NUMERIC(12,2)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    IF p_montant IS NULL OR p_montant <= 0 THEN
        RAISE EXCEPTION 'Montant invalide : %.', p_montant USING ERRCODE = 'check_violation';
    END IF;
    IF p_motif IS NULL OR length(btrim(p_motif)) = 0 THEN
        RAISE EXCEPTION 'Motif obligatoire (origine de la reprise).' USING ERRCODE = 'check_violation';
    END IF;
    PERFORM 1 FROM clients WHERE id = p_client_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Client % introuvable.', p_client_id USING ERRCODE = 'foreign_key_violation';
    END IF;
    PERFORM 1 FROM sites WHERE id = p_site_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Site % introuvable.', p_site_id USING ERRCODE = 'foreign_key_violation';
    END IF;

    INSERT INTO creances (client_id, vente_id, site_id, montant, motif, utilisateur_id)
    VALUES (p_client_id, NULL, p_site_id, p_montant, p_motif, p_utilisateur_id);

    RETURN encours_client(p_client_id);
END;
$$;

COMMENT ON FUNCTION enregistrer_creance_initiale(INTEGER, NUMERIC, INTEGER, INTEGER, VARCHAR) IS
  'Chargement du solde de départ d''un client (reprise du cahier papier, '
  'addendum point b, décidé 2026-09-25) — vente_id NULL, jamais confondu '
  'avec une créance née d''une vente réelle. Réservée au responsable '
  '(import mené par le prestataire, db/outils/importer_creances_initiales.py) — '
  'même esprit que enregistrer_inventaire_initial (migration 041).';

REVOKE ALL ON FUNCTION enregistrer_creance_initiale(INTEGER, NUMERIC, INTEGER, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION enregistrer_creance_initiale(INTEGER, NUMERIC, INTEGER, INTEGER, VARCHAR)
  TO qf_responsable;

-- ----------------------------------------------------------------------------
-- annuler_vente() — trouvé par exécution en écrivant CE cycle : la version
-- en vigueur (migration 017) contre-passe INCONDITIONNELLEMENT la recette
-- par une dépense de même montant. Une vente à crédit n'a JAMAIS créé de
-- recette (voir POST /ventes) — l'annuler créerait une dépense fantôme,
-- sans recette en face, faussant le journal transactions. Corrigé ici :
-- si une créance existe pour cette vente, elle est marquée annulée (pas de
-- dépense insérée) ; sinon, comportement inchangé (dépense de contre-
-- passation, comme avant).
--
-- Cas limite explicitement non traité (addendum point b, « à définir ») :
-- une créance déjà entamée par un règlement (allocation FIFO) refuse
-- l'annulation plutôt que de produire un encours négatif ou un
-- remboursement inventé.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION annuler_vente(
    p_vente_id INTEGER,
    p_utilisateur_id INTEGER,
    p_motif VARCHAR
) RETURNS TABLE(montant_ttc NUMERIC, articles_restitues INTEGER)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_statut          VARCHAR(20);
    v_site            INTEGER;
    v_total_ttc       NUMERIC(12,2);
    r                 RECORD;
    v_compte          INTEGER := 0;
    v_creance_id      INTEGER;
    v_client_id       INTEGER;
    v_creance_montant NUMERIC(12,2);
    v_creance_date    TIMESTAMP;
    v_cumul_avant     NUMERIC(12,2);
    v_total_regle     NUMERIC(12,2);
BEGIN
    IF p_motif IS NULL OR length(btrim(p_motif)) = 0 THEN
        RAISE EXCEPTION 'Motif obligatoire pour annuler une vente.' USING ERRCODE = 'check_violation';
    END IF;

    SELECT ventes.statut, ventes.site_id, ventes.total_ttc INTO v_statut, v_site, v_total_ttc
      FROM ventes WHERE id = p_vente_id FOR UPDATE;
    IF v_statut IS NULL THEN
        RAISE EXCEPTION 'Vente % introuvable.', p_vente_id USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF v_statut = 'annulee' THEN
        RAISE EXCEPTION 'Vente % déjà annulée.', p_vente_id
          USING ERRCODE = 'restrict_violation';
    END IF;

    FOR r IN
        SELECT article_id, site_id, SUM(quantite) AS quantite
          FROM mouvements_stock
         WHERE categorie = 'vente' AND vente_id = p_vente_id
         GROUP BY article_id, site_id
    LOOP
        INSERT INTO stocks_sites (article_id, site_id, quantite_stock, seuil_alerte)
        VALUES (r.article_id, r.site_id, 0, 0)
        ON CONFLICT (article_id, site_id) DO NOTHING;

        UPDATE stocks_sites SET quantite_stock = quantite_stock + r.quantite
         WHERE article_id = r.article_id AND site_id = r.site_id;

        INSERT INTO mouvements_stock (article_id, site_id, type, categorie, quantite, motif, utilisateur_id, vente_id)
        VALUES (r.article_id, r.site_id, 'entree', 'annulation_vente', r.quantite, p_motif, p_utilisateur_id, p_vente_id);
        v_compte := v_compte + 1;
    END LOOP;

    UPDATE ventes
       SET statut = 'annulee', annulee_par_id = p_utilisateur_id, motif_annulation = p_motif
     WHERE id = p_vente_id;

    SELECT id, client_id, montant, date_creance
      INTO v_creance_id, v_client_id, v_creance_montant, v_creance_date
      FROM creances WHERE vente_id = p_vente_id AND NOT annulee;

    IF v_creance_id IS NOT NULL THEN
        SELECT COALESCE(SUM(montant), 0) INTO v_cumul_avant
          FROM creances
         WHERE client_id = v_client_id AND NOT annulee
           AND (date_creance, id) < (v_creance_date, v_creance_id);
        SELECT COALESCE(SUM(montant), 0) INTO v_total_regle
          FROM reglements_creances WHERE client_id = v_client_id;

        IF LEAST(v_creance_montant, GREATEST(0, v_total_regle - v_cumul_avant)) > 0 THEN
            RAISE EXCEPTION
              'Vente % à crédit : la créance associée a déjà reçu un règlement '
              '(allocation FIFO) — annulation refusée (cas non traité, addendum point b).',
              p_vente_id
              USING ERRCODE = 'restrict_violation';
        END IF;

        UPDATE creances SET annulee = TRUE WHERE id = v_creance_id;
    ELSE
        INSERT INTO transactions (site_id, utilisateur_id, type, montant, description, vente_id)
        VALUES (v_site, p_utilisateur_id, 'depense', v_total_ttc,
                'Annulation de la vente #' || p_vente_id, p_vente_id);
    END IF;

    UPDATE ecarts_stock_ventes
       SET regularise = TRUE, regularise_par_id = p_utilisateur_id, date_regularisation = NOW()
     WHERE vente_id = p_vente_id AND regularise = FALSE;

    RETURN QUERY SELECT v_total_ttc, v_compte;
END;
$$;

COMMENT ON FUNCTION annuler_vente(INTEGER, INTEGER, VARCHAR) IS
  'Annule une vente : restitue le stock, contre-passe la recette par une '
  'dépense — SAUF pour une vente à crédit (aucune recette n''existait), où '
  'la créance associée est marquée annulée à la place (migration 045, '
  'trouvé par exécution). Refuse si la créance a déjà reçu un règlement '
  '(cas non traité, addendum point b).';

INSERT INTO schema_migrations (version, nom)
VALUES ('045', 'credit_client')
ON CONFLICT (version) DO NOTHING;
