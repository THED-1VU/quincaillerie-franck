-- ============================================================================
-- 040 — Chantier C7 (cycle 51) : plafond de vraisemblance DÉCIDÉ à 10 000.
-- ----------------------------------------------------------------------------
-- Décision du propriétaire (2026-09-25) : la mécanique livrée par la
-- migration 032 restait inactive tant que le paramètre valait 'a_definir'.
-- Le plafond est désormais fixé à 10 000 unités par ligne de comptage :
-- une quantité comptée au-delà est refusée comme invraisemblable.
-- ============================================================================

UPDATE parametres
   SET valeur = '10000',
       a_decider = FALSE,
       modifiable = TRUE,
       reference_decision = 'Décision 2026-09-25 (cycle 51)'
 WHERE cle = 'plafond_vraisemblance_comptage';

-- Garde-fou : si le paramètre manquait (base non migrée 032), on le crée
-- décidé — jamais bloquant.
INSERT INTO parametres (cle, valeur, type_valeur, description, modifiable, a_decider, reference_decision)
SELECT 'plafond_vraisemblance_comptage', '10000', 'entier',
       'Quantité comptée maximale acceptée sur une ligne de comptage.',
       TRUE, FALSE, 'Décision 2026-09-25 (cycle 51)'
WHERE NOT EXISTS (SELECT 1 FROM parametres WHERE cle = 'plafond_vraisemblance_comptage');

INSERT INTO schema_migrations (version, nom)
VALUES ('040', 'plafond_vraisemblance_decide')
ON CONFLICT (version) DO NOTHING;
