-- ============================================================================
-- 019 — Clôture de caisse quotidienne, PAR SITE (addendum, point g, décidé le
--        2026-09-13 : « une clôture par site »)
-- ----------------------------------------------------------------------------
-- Diagnostic (piste C6, 2026-09-14), prouvé par exécution : aucune clôture de
-- caisse n'existe. `routes/transactions.py` et `routes/rh.py` le disent déjà
-- explicitement depuis le cycle 16 (« hors périmètre, volontairement »). Le
-- reste de C6 (recettes/dépenses hors vente, RH) est réel et vérifié à
-- nouveau ici (144/144 pytest, 21/21 verifier-rh-reel.mjs, 87/87
-- verifier-cablage.mjs sur quincaillerie_c6) : rien n'est refait, seule la
-- clôture de caisse est construite.
--
-- Ce qui EST tranché (addendum point g, décision du 2026-09-13) :
--   * une clôture par SITE (Magasin et Comptoir clôturent séparément) ;
--   * le total ATTENDU par mode de paiement (espèces, Orange Money, MTN
--     MoMo, autre) est calculé PAR LE SERVEUR à partir des ventes `payee`
--     de la journée — jamais saisi, jamais recalculé côté client ;
--   * le responsable saisit les espèces comptées (obligatoire) et, en
--     option, les relevés Mobile Money ;
--   * l'écart (compté − attendu) est calculé par la fonction PostgreSQL,
--     jamais par l'application ;
--   * la clôture est FIGÉE après création (comme les ventes historiques,
--     migrations 004/005) : aucune modification directe, seule une
--     nouvelle clôture RECTIFICATIVE, tracée, corrige une clôture existante.
--
-- Ce qui N'EST PAS tranché (addendum point g, questions 2 à 6) et reste donc
-- SANS RÈGLE INVENTÉE :
--   * question 2 (fond de caisse initial) : ABSENT du modèle. Le montant
--     attendu en espèces ne tient compte QUE des ventes encaissées en
--     espèces ce jour-là, jamais d'un fond de caisse de départ que
--     personne n'a communiqué. Si un fond de caisse existe réellement dans
--     la boutique, le compte rendu ci-dessous le sous-estime d'autant —
--     signalé dans le rapport de cycle, PAS deviné ici.
--   * question 3 (qui clôture, à quelle heure, sort des ventes saisies en
--     retard) : la route est réservée au responsable (seul rôle qui gère déjà
--     la RH, données au moins aussi sensibles) ; aucune heure limite, aucun
--     verrou de saisie tardive n'est imposé — une vente saisie après coup
--     pour une journée déjà clôturée n'est PAS bloquée (aucune règle pour la
--     rattacher autoritairement à une autre journée), elle sera simplement
--     absente du total « attendu » déjà figé de la clôture existante :
--     visible par une éventuelle clôture rectificative, jamais corrigée en
--     silence.
--   * question 4 (rapprochement Mobile Money exact) : les montants Orange
--     Money / MTN MoMo comptés restent de simples champs OPTIONNELS
--     (nullable) — aucun relevé d'opérateur n'est importé ni comparé
--     automatiquement, seule la comparaison chiffre déclaré vs chiffre
--     attendu (déjà décidée) est faite.
--   * question 5 (seuil d'écart toléré) : paramètre `seuil_ecart_caisse_tolere`
--     amorcé à la sentinelle `a_definir`, comme `seuil_alerte_plancher` et
--     `tentatives_max_connexion` (migration 006) l'ont été avant confirmation.
--     Tant qu'il n'est pas tranché, `cloturer_caisse()` applique la valeur la
--     plus sûre — jamais inventée : une tolérance NULLE (comme `taux_tva = 0`
--     est la valeur neutre du point d tant que le régime fiscal n'est pas
--     tranché) — tout écart non nul exige alors un commentaire. Dès que le
--     propriétaire fixe un vrai seuil, il s'applique sans changement de code.
--   * question 6 (blocage vs simple marquage après clôture) : AUCUNE route de
--     ce cycle ne bloque une vente sur une journée déjà clôturée — seule
--     l'immutabilité de la clôture elle-même est garantie ci-dessous.
--
-- Cycle piste C6 (2026-09-14) — chantier C6. Idempotent.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Paramètre du seuil de commentaire obligatoire (addendum point g, question 5)
-- Même patron que seuil_alerte_plancher / tentatives_max_connexion : ajouté
-- à la table existante (migration 006), jamais une constante de code.
-- ----------------------------------------------------------------------------
INSERT INTO parametres (cle, valeur, type_valeur, description, modifiable, a_decider, reference_decision) VALUES
('seuil_ecart_caisse_tolere', 'a_definir', 'decimal',
 'Écart de caisse toléré (FCFA, par mode de paiement) au-delà duquel un '
 'commentaire devient obligatoire à la clôture. Tant que ce n''est pas '
 'tranché, cloturer_caisse() applique une tolérance NULLE (tout écart non '
 'nul exige un commentaire) — jamais un chiffre inventé.',
 TRUE, TRUE, 'addendum point g, question 5')
ON CONFLICT (cle) DO NOTHING;

-- ----------------------------------------------------------------------------
-- Table : une ligne = une clôture (originale ou rectificative), immuable.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clotures_caisse (
    id                          SERIAL PRIMARY KEY,
    site_id                     INTEGER NOT NULL REFERENCES sites(id) ON DELETE RESTRICT,
    date_cloture                DATE    NOT NULL,

    -- Attendu : calculé PAR LE SERVEUR (cloturer_caisse ci-dessous) à partir
    -- des ventes `payee` du site et du jour — jamais saisi.
    attendu_especes             NUMERIC(12,2) NOT NULL,
    attendu_orange_money        NUMERIC(12,2) NOT NULL,
    attendu_mtn_momo            NUMERIC(12,2) NOT NULL,
    attendu_autre               NUMERIC(12,2) NOT NULL,

    -- Compté : espèces obligatoires (seule caisse physique certaine),
    -- Mobile Money optionnel (addendum, question 4 non tranchée).
    compte_especes              NUMERIC(12,2) NOT NULL,
    compte_orange_money         NUMERIC(12,2),
    compte_mtn_momo             NUMERIC(12,2),
    compte_autre                NUMERIC(12,2),

    -- Écart = compté − attendu, calculé PAR LA FONCTION, jamais par
    -- l'application ni par un DEFAULT recalculable côté client. NULL pour un
    -- mode dont le compte n'a pas été saisi (rien à comparer).
    ecart_especes                NUMERIC(12,2) NOT NULL,
    ecart_orange_money           NUMERIC(12,2),
    ecart_mtn_momo                NUMERIC(12,2),
    ecart_autre                   NUMERIC(12,2),

    commentaire                  VARCHAR(500),
    utilisateur_id                INTEGER NOT NULL REFERENCES utilisateurs(id) ON DELETE RESTRICT,
    cloture_rectificative_de      INTEGER REFERENCES clotures_caisse(id) ON DELETE RESTRICT,
    date_creation                 TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE clotures_caisse IS
  'Clôture de caisse quotidienne PAR SITE (addendum point g, décidé le '
  '2026-09-13). Figée après création (voir trg_cloture_caisse_figee) : une '
  'correction se fait uniquement par une nouvelle ligne rectificative, '
  'jamais par UPDATE. Seule cloturer_caisse() (SECURITY DEFINER) y écrit.';
COMMENT ON COLUMN clotures_caisse.attendu_especes IS
  'Somme des ventes payee en espèces, site et jour de la clôture — calculée '
  'par cloturer_caisse(), jamais saisie ni recalculée côté client.';
COMMENT ON COLUMN clotures_caisse.cloture_rectificative_de IS
  'NULL pour la clôture originale du couple (site_id, date_cloture). Sinon, '
  'référence la clôture qu''elle corrige (addendum : « une correction se '
  'fait par une clôture rectificative tracée »).';

CREATE INDEX IF NOT EXISTS idx_clotures_caisse_site_date
  ON clotures_caisse (site_id, date_cloture);

-- Une seule clôture ORIGINALE par site et par jour (les rectificatives, elles,
-- peuvent s'accumuler en corrigeant la précédente — pas de limite imposée,
-- addendum non tranché sur ce point de détail).
CREATE UNIQUE INDEX IF NOT EXISTS uq_clotures_caisse_originale_par_jour
  ON clotures_caisse (site_id, date_cloture)
  WHERE cloture_rectificative_de IS NULL;

ALTER TABLE clotures_caisse DROP CONSTRAINT IF EXISTS chk_clotures_caisse_montants_positifs;
ALTER TABLE clotures_caisse ADD  CONSTRAINT chk_clotures_caisse_montants_positifs
  CHECK (
    attendu_especes >= 0 AND attendu_orange_money >= 0
    AND attendu_mtn_momo >= 0 AND attendu_autre >= 0
    AND compte_especes >= 0
    AND (compte_orange_money IS NULL OR compte_orange_money >= 0)
    AND (compte_mtn_momo    IS NULL OR compte_mtn_momo    >= 0)
    AND (compte_autre       IS NULL OR compte_autre       >= 0)
  );

-- ----------------------------------------------------------------------------
-- Immutabilité : AUCUNE modification directe, quel que soit le rôle — y
-- compris le propriétaire de la table. Seule une clôture rectificative,
-- via cloturer_caisse(), corrige. Même patron que interdire_suppression_
-- journal() (migration 004), mais pour UPDATE : ici on interdit tout, pas
-- seulement une transition de statut.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION interdire_modification_cloture_caisse()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
      'Une clôture de caisse est figée dès sa création (id %) : aucune '
      'modification directe. Corrigez par une nouvelle clôture rectificative.',
      OLD.id
      USING ERRCODE = 'restrict_violation';
END;
$$;

COMMENT ON FUNCTION interdire_modification_cloture_caisse() IS
  'Bloque tout UPDATE sur clotures_caisse, sans exception — la seule façon '
  'de corriger une clôture est une clôture rectificative tracée (addendum '
  'point g), jamais une réécriture de l''existante.';

DROP TRIGGER IF EXISTS trg_cloture_caisse_figee ON clotures_caisse;
CREATE TRIGGER trg_cloture_caisse_figee
  BEFORE UPDATE ON clotures_caisse
  FOR EACH ROW EXECUTE FUNCTION interdire_modification_cloture_caisse();

DROP TRIGGER IF EXISTS trg_journal_non_supprimable ON clotures_caisse;
CREATE TRIGGER trg_journal_non_supprimable
  BEFORE DELETE ON clotures_caisse
  FOR EACH ROW EXECUTE FUNCTION interdire_suppression_journal();

-- ----------------------------------------------------------------------------
-- Cloisonnement : réservé au responsable, comme la RH (rémunération et
-- caisse sont des données au moins aussi sensibles — CDC §3.5, addendum
-- point g « le responsable saisit »). Ni agent_stock ni agent_comptabilite
-- n'ont AUCUN droit sur cette table : ni SELECT, ni INSERT, ni EXECUTE sur
-- la fonction — pas seulement un filtre RLS.
-- ----------------------------------------------------------------------------
REVOKE ALL ON clotures_caisse FROM PUBLIC, qf_agent_stock, qf_agent_comptabilite;
GRANT SELECT ON clotures_caisse TO qf_responsable;
-- Pas de GRANT INSERT/UPDATE direct, même pour le responsable : seule
-- cloturer_caisse() (SECURITY DEFINER ci-dessous) écrit dans cette table.

ALTER TABLE clotures_caisse ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS p_clotures_caisse_site ON clotures_caisse;
CREATE POLICY p_clotures_caisse_site ON clotures_caisse
  USING      (current_user = 'qf_responsable' OR site_id = qf_site_courant())
  WITH CHECK (current_user = 'qf_responsable' OR site_id = qf_site_courant());

-- ----------------------------------------------------------------------------
-- calculer_attendu_caisse() — SOURCE UNIQUE du calcul de l'attendu par mode
-- de paiement, utilisée à la fois par cloturer_caisse() (ci-dessous) et par
-- une route de PRÉVISUALISATION (GET /caisse/attendu) : l'addendum décrit
-- « le système affiche le total attendu » AVANT que le responsable saisisse
-- son comptage — il doit donc pouvoir le consulter sans créer de clôture.
-- Pas SECURITY DEFINER : qf_responsable a déjà SELECT sur ventes (migration
-- 008), aucun besoin d'élévation de privilège pour une simple lecture.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION calculer_attendu_caisse(p_site_id INTEGER, p_date DATE)
RETURNS TABLE(especes NUMERIC, orange_money NUMERIC, mtn_momo NUMERIC, autre NUMERIC)
LANGUAGE sql
STABLE
AS $$
    SELECT
        COALESCE(SUM(total_ttc) FILTER (WHERE mode_paiement = 'especes'), 0),
        COALESCE(SUM(total_ttc) FILTER (WHERE mode_paiement = 'orange_money'), 0),
        COALESCE(SUM(total_ttc) FILTER (WHERE mode_paiement = 'mtn_momo'), 0),
        COALESCE(SUM(total_ttc) FILTER (WHERE mode_paiement = 'autre'), 0)
      FROM ventes
     WHERE site_id = p_site_id AND statut = 'payee' AND date_encaissement::date = p_date;
$$;

COMMENT ON FUNCTION calculer_attendu_caisse(INTEGER, DATE) IS
  'Total attendu par mode de paiement (ventes payee du site et du jour). '
  'credit_client est volontairement absent des 4 totaux (addendum point b : '
  'désactivé côté serveur, aucune recette de caisse ne doit lui être '
  'imputée). Utilisée par cloturer_caisse() ET par GET /caisse/attendu '
  '(prévisualisation avant saisie du comptage).';

REVOKE ALL ON FUNCTION calculer_attendu_caisse(INTEGER, DATE) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION calculer_attendu_caisse(INTEGER, DATE) TO qf_responsable;

-- ----------------------------------------------------------------------------
-- cloturer_caisse() — SEUL point d'écriture. Calcule l'attendu, calcule
-- l'écart, applique la règle du commentaire obligatoire, insère la ligne
-- figée. SECURITY DEFINER : le responsable n'a besoin d'aucun droit direct
-- d'écriture sur la table (même patron que decrementer_stock_vente,
-- migration 008/011).
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION cloturer_caisse(
    p_site_id                  INTEGER,
    p_date_cloture             DATE,
    p_espece_comptee           NUMERIC,
    p_utilisateur_id           INTEGER,
    p_orange_money_compte      NUMERIC DEFAULT NULL,
    p_mtn_momo_compte          NUMERIC DEFAULT NULL,
    p_autre_compte             NUMERIC DEFAULT NULL,
    p_commentaire              VARCHAR DEFAULT NULL,
    p_cloture_rectificative_de INTEGER DEFAULT NULL
) RETURNS clotures_caisse
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_attendu_especes      NUMERIC(12,2);
    v_attendu_orange_money NUMERIC(12,2);
    v_attendu_mtn_momo     NUMERIC(12,2);
    v_attendu_autre        NUMERIC(12,2);
    v_ecart_especes        NUMERIC(12,2);
    v_ecart_orange_money   NUMERIC(12,2);
    v_ecart_mtn_momo       NUMERIC(12,2);
    v_ecart_autre          NUMERIC(12,2);
    v_seuil_brut           TEXT;
    v_seuil                NUMERIC;
    v_depasse              BOOLEAN;
    v_resultat             clotures_caisse;
BEGIN
    IF p_site_id IS NULL THEN
        RAISE EXCEPTION 'Le site est obligatoire pour une clôture de caisse.'
          USING ERRCODE = 'check_violation';
    END IF;
    IF p_date_cloture IS NULL OR p_date_cloture > CURRENT_DATE THEN
        RAISE EXCEPTION 'Date de clôture invalide : %.', p_date_cloture
          USING ERRCODE = 'check_violation';
    END IF;
    IF p_espece_comptee IS NULL OR p_espece_comptee < 0 THEN
        RAISE EXCEPTION
          'Le montant d''espèces réellement compté est obligatoire et ne '
          'peut pas être négatif.'
          USING ERRCODE = 'check_violation';
    END IF;

    -- Une rectificative doit corriger une clôture qui existe réellement,
    -- pour le MÊME site et le MÊME jour.
    IF p_cloture_rectificative_de IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM clotures_caisse
             WHERE id = p_cloture_rectificative_de
               AND site_id = p_site_id AND date_cloture = p_date_cloture
        ) THEN
            RAISE EXCEPTION
              'Clôture rectificative : aucune clôture % à corriger pour le '
              'site % à la date %.',
              p_cloture_rectificative_de, p_site_id, p_date_cloture
              USING ERRCODE = 'foreign_key_violation';
        END IF;
    ELSE
        IF EXISTS (
            SELECT 1 FROM clotures_caisse
             WHERE site_id = p_site_id AND date_cloture = p_date_cloture
               AND cloture_rectificative_de IS NULL
        ) THEN
            RAISE EXCEPTION
              'Une clôture existe déjà pour le site % à la date % : passez '
              'par une clôture rectificative pour la corriger.',
              p_site_id, p_date_cloture
              USING ERRCODE = 'unique_violation';
        END IF;
    END IF;

    -- Attendu : ventes PAYÉES de ce site, ce jour (fuseau Africa/Douala,
    -- migration 013) — SOURCE UNIQUE : calculer_attendu_caisse() ci-dessus,
    -- la même que la prévisualisation GET /caisse/attendu.
    SELECT especes, orange_money, mtn_momo, autre
      INTO v_attendu_especes, v_attendu_orange_money, v_attendu_mtn_momo, v_attendu_autre
      FROM calculer_attendu_caisse(p_site_id, p_date_cloture);

    v_ecart_especes      := p_espece_comptee - v_attendu_especes;
    v_ecart_orange_money := CASE WHEN p_orange_money_compte IS NULL THEN NULL
                                  ELSE p_orange_money_compte - v_attendu_orange_money END;
    v_ecart_mtn_momo     := CASE WHEN p_mtn_momo_compte IS NULL THEN NULL
                                  ELSE p_mtn_momo_compte - v_attendu_mtn_momo END;
    v_ecart_autre        := CASE WHEN p_autre_compte IS NULL THEN NULL
                                  ELSE p_autre_compte - v_attendu_autre END;

    -- Seuil de commentaire obligatoire (addendum point g, question 5) : lu
    -- directement (jamais via parametre_numerique(), qui lèverait une
    -- exception sur 'a_definir' et bloquerait TOUTE clôture). Tant que le
    -- propriétaire n'a pas tranché, la tolérance appliquée est NULLE — la
    -- valeur la plus sûre, jamais un chiffre inventé à sa place.
    SELECT valeur INTO v_seuil_brut FROM parametres WHERE cle = 'seuil_ecart_caisse_tolere';
    IF v_seuil_brut IS NULL OR v_seuil_brut = 'a_definir' THEN
        v_seuil := 0;
    ELSE
        v_seuil := v_seuil_brut::NUMERIC;
    END IF;

    v_depasse :=
        ABS(v_ecart_especes) > v_seuil
        OR (v_ecart_orange_money IS NOT NULL AND ABS(v_ecart_orange_money) > v_seuil)
        OR (v_ecart_mtn_momo    IS NOT NULL AND ABS(v_ecart_mtn_momo)    > v_seuil)
        OR (v_ecart_autre       IS NOT NULL AND ABS(v_ecart_autre)       > v_seuil);

    IF v_depasse AND (p_commentaire IS NULL OR length(btrim(p_commentaire)) = 0) THEN
        RAISE EXCEPTION
          'Écart de caisse supérieur au seuil toléré (% FCFA) : un '
          'commentaire est obligatoire pour clôturer.',
          v_seuil
          USING ERRCODE = 'check_violation';
    END IF;

    INSERT INTO clotures_caisse (
        site_id, date_cloture,
        attendu_especes, attendu_orange_money, attendu_mtn_momo, attendu_autre,
        compte_especes, compte_orange_money, compte_mtn_momo, compte_autre,
        ecart_especes, ecart_orange_money, ecart_mtn_momo, ecart_autre,
        commentaire, utilisateur_id, cloture_rectificative_de
    ) VALUES (
        p_site_id, p_date_cloture,
        v_attendu_especes, v_attendu_orange_money, v_attendu_mtn_momo, v_attendu_autre,
        p_espece_comptee, p_orange_money_compte, p_mtn_momo_compte, p_autre_compte,
        v_ecart_especes, v_ecart_orange_money, v_ecart_mtn_momo, v_ecart_autre,
        NULLIF(btrim(p_commentaire), ''), p_utilisateur_id, p_cloture_rectificative_de
    )
    RETURNING * INTO v_resultat;

    RETURN v_resultat;
END;
$$;

COMMENT ON FUNCTION cloturer_caisse(INTEGER, DATE, NUMERIC, INTEGER, NUMERIC, NUMERIC, NUMERIC, VARCHAR, INTEGER) IS
  'Seul point d''écriture de clotures_caisse. Calcule l''attendu depuis les '
  'ventes payee du jour (jamais saisi), calcule l''écart (jamais côté '
  'client), exige un commentaire si l''écart dépasse seuil_ecart_caisse_tolere '
  '(tolérance nulle tant que ce paramètre reste a_definir).';

REVOKE ALL ON FUNCTION cloturer_caisse(INTEGER, DATE, NUMERIC, INTEGER, NUMERIC, NUMERIC, NUMERIC, VARCHAR, INTEGER) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION cloturer_caisse(INTEGER, DATE, NUMERIC, INTEGER, NUMERIC, NUMERIC, NUMERIC, VARCHAR, INTEGER)
  TO qf_responsable;

INSERT INTO schema_migrations (version, nom)
VALUES ('019', 'cloture_caisse')
ON CONFLICT (version) DO NOTHING;
