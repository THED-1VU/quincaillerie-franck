-- Annule la migration 040 : le plafond redevient à décider.

UPDATE parametres
   SET valeur = 'a_definir',
       a_decider = TRUE,
       modifiable = TRUE,
       reference_decision = NULL
 WHERE cle = 'plafond_vraisemblance_comptage';

DELETE FROM schema_migrations WHERE version = '040';
