-- Annule la migration 051 : le seuil de remise redevient à décider
-- (mécanique 037 inactive : aucun blocage tant qu'aucune valeur n'est fixée).

UPDATE parametres
   SET valeur = 'a_definir',
       a_decider = TRUE,
       modifiable = TRUE,
       reference_decision = 'décision propriétaire 2026-09-22/23 — valeur à fixer'
 WHERE cle = 'seuil_remise_validation_pct';

DELETE FROM schema_migrations WHERE version = '051';
