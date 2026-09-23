-- ============================================================================
-- 037 — Chantier point f (2026-09-23), sous-chantier 3 : remises.
-- ----------------------------------------------------------------------------
-- Décision du propriétaire (ADDENDUM_CAHIER_DES_CHARGES.md, point f, réponse
-- à la question 4) :
--   * toujours visibles explicitement sur le ticket (prix catalogue, montant
--     de la remise, total réellement payé) — jamais une modification
--     silencieuse du prix affiché ;
--   * applicable au choix au niveau d'UNE LIGNE ou de la VENTE ENTIÈRE —
--     deux mécanismes séparés, pas une distribution automatique entre
--     lignes ;
--   * montant OU pourcentage, au choix du vendeur ;
--   * prix initial, montant de la remise, montant réellement payé conservés
--     SÉPARÉMENT, jamais fusionnés ;
--   * autorisation du responsable exigée au-delà d'un seuil (valeur non
--     donnée — paramètre `a_definir`, comme les autres sentinelles du
--     projet : AUCUN blocage tant qu'un chiffre n'est pas fixé) ;
--   * cumul des remises exploitable pour un futur rapport (C8, hors
--     périmètre de ce sous-chantier).
--
-- Décision complémentaire (validation du plan, 2026-09-23) :
--   * seuil distinct de celui du point c, question 5 (écart de prix par
--     vendeur, 10 %, jamais construit) — usages différents, pas de
--     paramètre partagé.
--   * une remise à 100 % est REFUSÉE ici : c'est le sous-chantier 4
--     (article offert / sortie commerciale gratuite) qui la couvre, un
--     seul chemin d'écriture par concept — même principe que le retrait
--     des routes directes en doublon au sous-chantier 2.
--
-- prix_catalogue NULLABLE (pas NOT NULL) : les lignes de vente déjà
-- enregistrées avant ce cycle, et toute écriture directe hors de la route
-- applicative (tests notamment), n'ont pas cette information — NULL toléré,
-- jamais rétro-inventé (même principe que numero_facturier/vendeur_id,
-- migration 020). remise_montant, lui, est TOUJOURS connu (0 par défaut).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Remise par ligne.
-- ----------------------------------------------------------------------------
ALTER TABLE ventes_lignes ADD COLUMN prix_catalogue NUMERIC(12,2);
ALTER TABLE ventes_lignes ADD COLUMN remise_montant NUMERIC(12,2) NOT NULL DEFAULT 0;

COMMENT ON COLUMN ventes_lignes.prix_catalogue IS
  'Prix catalogue de l''article (articles.prix_vente) au moment de la '
  'vente, capturé une fois pour toutes — jamais relu après coup. NULL pour '
  'les lignes antérieures au cycle 42 (migration 037) ou écrites hors de '
  'la route applicative, jamais rétro-inventé.';
COMMENT ON COLUMN ventes_lignes.remise_montant IS
  'Montant de la remise PAR UNITÉ (même échelle que prix_unitaire), '
  'décision 2026-09-22 (addendum, point f). prix_unitaire reste le prix '
  'réellement payé — les trois valeurs (catalogue, remise, payé) restent '
  'séparées, jamais fusionnées.';

ALTER TABLE ventes_lignes DROP CONSTRAINT chk_ventes_lignes_prix_positif;
ALTER TABLE ventes_lignes ADD CONSTRAINT chk_ventes_lignes_prix_positif
  CHECK (prix_unitaire > 0);
COMMENT ON CONSTRAINT chk_ventes_lignes_prix_positif ON ventes_lignes IS
  'Strictement positif (pas seulement >= 0) depuis la migration 037 : une '
  'remise à 100 % est refusée ici — décision 2026-09-23, elle relève du '
  'sous-chantier 4 (article offert), un mécanisme dédié et distinct.';

ALTER TABLE ventes_lignes ADD CONSTRAINT chk_ventes_lignes_remise_positive
  CHECK (remise_montant >= 0);
-- GREATEST(..., 0), pas une égalité stricte à prix_catalogue - remise :
-- un prix négocié AU-DESSUS du catalogue reste légitime (point d, jamais
-- interdit) — dans ce cas remise_montant doit être 0, pas une valeur
-- négative forcée par l'équation.
ALTER TABLE ventes_lignes ADD CONSTRAINT chk_ventes_lignes_remise_coherente
  CHECK (prix_catalogue IS NULL OR remise_montant = GREATEST(prix_catalogue - prix_unitaire, 0));

-- ----------------------------------------------------------------------------
-- 2. Remise de la vente entière — mécanisme SÉPARÉ de la remise par ligne,
--    pas une distribution automatique entre les lignes.
-- ----------------------------------------------------------------------------
ALTER TABLE ventes ADD COLUMN remise_globale_montant NUMERIC(12,2) NOT NULL DEFAULT 0;

COMMENT ON COLUMN ventes.remise_globale_montant IS
  'Remise appliquée à la vente ENTIÈRE (décision 2026-09-22, addendum '
  'point f), en plus des remises par ligne éventuelles — mécanisme séparé, '
  'jamais réparti automatiquement entre les lignes. Réduit total_ttc au-delà '
  'de la somme des lignes. Cohérence (ne peut pas dépasser le sous-total) '
  'vérifiée en Python à l''enregistrement : une CHECK sur cette seule '
  'colonne ne peut pas voir la somme des lignes soeurs.';

ALTER TABLE ventes ADD CONSTRAINT chk_ventes_remise_globale_positive
  CHECK (remise_globale_montant >= 0);

-- ----------------------------------------------------------------------------
-- 3. Seuil de validation responsable — mécanique prête, INACTIVE tant que
--    non fixé (même sentinelle que duree_session_minutes,
--    seuil_ecart_caisse_tolere, plafond_vraisemblance_comptage).
-- ----------------------------------------------------------------------------
INSERT INTO parametres (cle, valeur, type_valeur, description, modifiable, a_decider, reference_decision)
VALUES ('seuil_remise_validation_pct', 'a_definir', 'decimal',
        'Pourcentage de remise (ligne ou globale) au-delà duquel seul un '
        'responsable peut enregistrer la vente. Aucune remise bloquée tant '
        'que non fixé. Distinct du seuil d''écart de prix vendeur (point c, '
        'question 5, jamais construit) : usages différents.',
        TRUE, TRUE, 'décision propriétaire 2026-09-22/23 — valeur à fixer')
ON CONFLICT (cle) DO NOTHING;

INSERT INTO schema_migrations (version, nom)
VALUES ('037', 'remises')
ON CONFLICT (version) DO NOTHING;
