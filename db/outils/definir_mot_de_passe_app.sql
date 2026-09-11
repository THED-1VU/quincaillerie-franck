-- ============================================================================
-- Définit le mot de passe du rôle de connexion « qf_app ».
-- ----------------------------------------------------------------------------
-- LE MOT DE PASSE N'EST JAMAIS DANS LE DÉPÔT. Il est passé en variable psql à
-- l'exécution, sur le poste serveur, par la personne qui déploie.
--
-- Usage :
--   psql -d quincaillerie -v mdp="'LeMotDePasseChoisi'" -f db/outils/definir_mot_de_passe_app.sql
--
-- Les guillemets simples à l'intérieur des guillemets doubles sont volontaires.
-- Générer un mot de passe solide, par exemple :
--   python -c "import secrets; print(secrets.token_urlsafe(24))"
--
-- Le même mot de passe est ensuite reporté dans config.ini (fichier local,
-- jamais versionné), section [database], avec user = qf_app.
-- ============================================================================

ALTER ROLE qf_app WITH PASSWORD :mdp;

\echo 'Mot de passe de qf_app défini. Reportez-le dans config.ini (user = qf_app).'
\echo 'RAPPEL : ne jamais utiliser le compte « postgres » depuis l''application.'
