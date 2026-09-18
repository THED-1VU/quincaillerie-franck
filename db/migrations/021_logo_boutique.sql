-- ============================================================================
-- 021 — Logo du client (nouvelle fonctionnalité, cycle 28 : le responsable
-- téléverse le logo de SA boutique depuis l'application, sans intervention
-- technique).
-- ----------------------------------------------------------------------------
-- Le FICHIER lui-même ne vit jamais en base (voir server/app/routes/
-- configuration.py) : il est stocké hors base, dans un dossier dédié
-- (server/donnees/logo_boutique/, jamais versionné, inclus dans la
-- sauvegarde/restauration — voir db/outils/sauvegarder.ps1). Cette table ne
-- garde que le TYPE de fichier actuellement présent, pas son contenu.
--
-- '' (chaîne vide) = aucun logo téléversé — état normal, pas une erreur,
-- donc PAS la sentinelle « a_definir » (réservée aux décisions métier non
-- tranchées par le propriétaire, migration 006) : l'absence de logo n'est
-- pas une décision en attente, c'est un état de configuration ordinaire qui
-- change à chaque téléversement/suppression.
-- ============================================================================

INSERT INTO parametres (cle, valeur, type_valeur, description, modifiable, a_decider, reference_decision)
VALUES
('logo_boutique_extension', '', 'texte',
 'Extension du fichier actuellement présent dans server/donnees/logo_boutique/ '
 '("png" ou "jpg"), vide si aucun logo n''a été téléversé. Écrit UNIQUEMENT par '
 'POST /configuration/logo — jamais modifié à la main.',
 TRUE, FALSE, NULL)
ON CONFLICT (cle) DO NOTHING;

INSERT INTO schema_migrations (version, nom)
VALUES ('021', 'logo_boutique')
ON CONFLICT (version) DO NOTHING;
