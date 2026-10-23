-- ============================================================================
-- 051 — Cycle 75 (2026-10-23) : seuil de validation des remises DÉCIDÉ à 10 %.
-- ----------------------------------------------------------------------------
-- Décision D4 du propriétaire (2026-10-23) : « Remises jusqu'à 10 % ; au-delà,
-- validation obligatoire du responsable ». La mécanique livrée par la
-- migration 037 (refus 403 côté serveur si l'auteur de la vente n'est pas
-- responsable, par ligne comme sur la remise globale) restait inactive tant
-- que le paramètre valait 'a_definir'. Il est désormais fixé à 10 :
--   * une remise de 10 % exactement passe pour tout compte autorisé ;
--   * au-delà de 10 % (strictement), seul un responsable peut enregistrer
--     la vente — vérification côté serveur, liée à l'opération (la vente
--     porte son auteur dans ventes.utilisateur_id et le détail de la remise
--     dans ventes_lignes.remise_montant / prix_catalogue).
-- Même pattern que 040 (plafond de vraisemblance décidé) : UPDATE, puis
-- garde-fou INSERT si le paramètre manquait (base non migrée 037).
-- ============================================================================

UPDATE parametres
   SET valeur = '10',
       a_decider = FALSE,
       modifiable = TRUE,
       reference_decision = 'Décision D4 2026-10-23 (cycle 75)'
 WHERE cle = 'seuil_remise_validation_pct';

INSERT INTO parametres (cle, valeur, type_valeur, description, modifiable, a_decider, reference_decision)
SELECT 'seuil_remise_validation_pct', '10', 'decimal',
       'Pourcentage de remise (ligne ou globale) au-delà duquel seul un '
       'responsable peut enregistrer la vente. Distinct du seuil d''écart de '
       'prix vendeur (point c, question 5) : usages différents.',
       TRUE, FALSE,
       'Décision D4 2026-10-23 (cycle 75)'
WHERE NOT EXISTS (SELECT 1 FROM parametres WHERE cle = 'seuil_remise_validation_pct');

INSERT INTO schema_migrations (version, nom)
VALUES ('051', 'seuil_remise_valide')
ON CONFLICT (version) DO NOTHING;
