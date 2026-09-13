# Propriété du code source — Ets Quincaillerie Franck

Ce document formalise la décision prise sur le **point l** de
`ADDENDUM_CAHIER_DES_CHARGES.md` (« Propriété du code source et
obligation de livraison du dépôt »).

## Décision

- Le **code source complet** de l'application — API (`server/`), maquette
  (`maquette/`), schéma de base et migrations (`db/`), scripts de
  fabrication, de sauvegarde et de restauration (`db/outils/`,
  `server/fabrication/`), jeux de tests (`server/tests/`,
  `db/tests/`, `maquette/verification/`) et documentation
  (`RAPPORT AVANCEMENT/`, `PERIMETRE_LIVRE.md`, `MODELE_DONNEES.md`,
  `ADDENDUM_CAHIER_DES_CHARGES.md`, ce fichier) — est la **propriété des
  Ets Quincaillerie Franck**.
- Le dépôt est hébergé sur GitHub (`THED-1VU/quincaillerie-franck`), sous
  un compte dont le propriétaire de la boutique détient l'**accès
  administrateur permanent**. Tout autre intervenant sur ce dépôt agit en
  simple contributeur.
- Chaque cycle de travail est livré **en continu** par un commit sur la
  branche `main` (ou une branche de chantier fusionnée sur `main`),
  jamais par un exécutable livré sans le code correspondant dans le
  dépôt.
- Le dépôt **ne contient jamais** : `config.ini` réel, mots de passe, clés
  secrètes, sauvegardes de données réelles, exécutables compilés — vérifié
  par un audit de l'historique complet le 2026-09-13 (voir ci-dessous).
- **Réversibilité** : le propriétaire peut, à tout moment et sans
  dépendre d'un tiers, cloner ce dépôt, reconstruire l'exécutable
  (`server/fabrication/`, voir `server/README.md`) et redéployer
  l'application sur un poste neuf.

## Audit de l'historique — 2026-09-13

Vérifié par exécution (`git log --all -p` sur l'historique complet, pas
seulement `main`) :

- `server/config.ini` n'a **jamais** été suivi par Git (correctement
  ignoré par `.gitignore`, aucune trace dans l'historique).
- Aucune valeur de mot de passe, de clé secrète (`secret_key`) ou de
  jeton (AWS, GitHub, Slack, clé privée RSA/OpenSSH) réelle n'a été
  trouvée dans l'historique — seules des valeurs de **développement
  local** explicitement documentées comme non secrètes (`qf_dev_local`,
  `qf_app_dev_local`, mots de passe des comptes de test, la valeur
  d'exemple de `config.example.ini`) apparaissent, jamais un secret de
  production.

## Ce qui reste hors de ce document

Les questions 2 à 4 du point l (clause contractuelle liant le paiement du
solde à la livraison du dépôt, dépôt fiduciaire pour un éventuel
certificat de signature, répartition des accès administrateur entre
plusieurs personnes côté quincaillerie) relèvent d'un accord contractuel
entre le propriétaire et un prestataire — hors du périmètre technique que
ce dépôt peut trancher lui-même.
