# Lot A — C1 : intégrité des paiements et reprise vérifiable

2026-10-23. Dépend de l'unité C2/C3 (053), elle-même basée sur le sommet complet
`2dae406` de la PR 100. Aucune de ces dépendances n'est assimilée à une fusion.
Les contrôles de chaque HEAD sont requis avant intégration, dans cet ordre.

## Écarts initiaux reproduits

La migration 052 ne vérifiait l'invariant que lorsqu'une composante était
écrite. Le rejeu sur le schéma 052 a accepté les quatre contournements :
vente payée sans composante, mode mixte à une composante, crédit portant une
composante et modification du seul total de la vente. Le même pilote sur
054 refuse les quatre cas. Les transactions des sondes sont annulées.

La modification du rattachement d'une composante ne vérifiait que sa nouvelle
vente, et la vente parente n'était pas verrouillée matériellement pour les
écritures de composantes. Les rôles métier pouvaient en outre réécrire
directement des colonnes de documents et de journaux financiers.

Le migrateur rejouait systématiquement toutes les migrations : les fichiers
historiques non idempotents empêchaient un upgrade normal d'une base existante.
Plusieurs fixtures SQL et navigateur créaient des ventes payées sans paiement,
en contournant l'écriture atomique désormais obligatoire.
Le rejeu depuis 051 a également reproduit l'échec du backfill 052 sur un
brouillon espèces à zéro (contrainte de montant strictement positif), et
l'incompatibilité du nom de contrainte laissé par l'ancien inverse.

## Corrections

- 054 contrôle les deux côtés au COMMIT : vente et composantes ; modes,
  somme, cardinalité du mixte et absence de paiement immédiat pour le crédit.
  Le brouillon non encaissé et la vente gratuite à zéro sont conservés.
- Les écritures des composantes verrouillent matériellement les ventes
  concernées, dans l'ordre de leurs identifiants. La source et la destination
  sont contrôlées lors d'un déplacement. Une transaction incohérente est
  rejetée en entier ; la concurrence ne perd pas de mise à jour.
- Les rôles métier perdent les UPDATE directs sur les documents et journaux
  concernés. Le seul UPDATE(id) sur ventes sert au verrou ; l'annulation,
  les retours et les remboursements passent par les fonctions existantes.
- Migrateurs Bash et PowerShell : reprendre après le dernier niveau initial
  enregistré, sans rejouer les versions existantes. Le niveau est figé avant
  la boucle, afin de ne pas omettre le second fichier historique 040 lors
  d'une installation vierge.
  Un trou dans les versions antérieures provoque un refus explicite, pas
  une reprise sur un socle incomplet.
- Les quatre ventes payées des fixtures SQL et les amorçages des seules
  suites cablage/stock/rapports écrivent vente + paiement dans une transaction.
  Cette adaptation transversale a été annoncée dans le contrat publié et
  dans la note de coordination du checkout principal, avant modification.

## Migrations effectivement présentes et limites

000–052 : **53 fichiers montants**, dont deux 040 historiques et aucun 043,
conformément au registre historique. 053 et 054 portent le total à 55 fichiers
montants, avec 55 inverses ; `schema_migrations` comporte 54 versions uniques.
Aucune renumérotation. Deux corrections ciblées à 052 : ne pas tenter de
créer une composante nulle pour un brouillon à zéro lors du backfill, et
recréer dans l'inverse le nom de contrainte reconnu par la migration montante.
Les marqueurs historiques par numéro ne prouvent pas individuellement les
deux fichiers 040 : l'installation vierge les rejoue tous deux. Une ancienne
base interrompue au milieu de cette collision requiert un diagnostic de schéma,
elle ne doit pas être assimilée sans preuve à une base 052 complète.

La migration 054 vérifie aussi l'existant et s'arrête atomiquement s'il est
incohérent. Elle ne fabrique aucun paiement pour masquer une anomalie.
Les fonctions SECURITY DEFINER antérieures sont conservées ; les validateurs
054 s'exécutent sous les privilèges et la RLS de l'appelant. Aucun accès aux
prix d'achat ou au site d'un tiers n'est ajouté.

## Preuves par exécution

Commande : `python "RAPPORT AVANCEMENT/cycles/verifier_lot_a.py" --cible`.
Sur instance propre : **202/202 protections SQL**, **55/55 habilitations SQL**,
**6/6 concurrence stock**, **48 tests pytest ciblés** communs C1/C2/C3.
Les nouveaux scénarios couvrent aussi RLS des composantes, refus agent stock,
refus d'UPDATE des colonnes métier et écritures de paiements concurrentes.

Le pilote utilise une instance PostgreSQL propre, sans service de production,
et détruit uniquement ses bases nommées `quincaillerie_codex_*`.
Il produit un dump custom de données **synthétiques**, le restaure directement
avec `pg_restore`, puis compare nombres et empreintes des utilisateurs, rôles,
stocks, ventes, paiements et transactions : **identiques**.
Sur la copie restaurée, inverses 054 puis 053, upgrade PowerShell depuis 052,
puis réapplication Bash : **codes 0**, versions 053 et 054 présentes.
Les quatre sondes acceptées en 052 sont ensuite refusées en 054.
La passe `--migration-seule` reconstruit aussi une base 051 avec des brouillons
espèces à zéro et à 100 : le SQL 052 initial échoue sur le zéro, le SQL corrigé
conserve les deux brouillons sans créer de composante. Retour puis remontée
052, y compris avec le nom de contrainte de l'ancien inverse : succès.
Une vente mixte est ensuite créée ; le retour 052 incompatible est refusé
dans une transaction, et ses deux composantes restent présentes.

La passe complète locale a donné 378 réussites et 10 erreurs de préparation
`PermissionError: WinError 5` dans un ancien répertoire pytest, sans échec
d'assertion métier. Les dix tests concernés ont ensuite été rejoués :
**10/10 réussis** dans un répertoire neuf. Le pilote crée désormais un
répertoire temporaire unique à chaque invocation. Ces deux passes ne sont
pas présentées comme une passe complète unique ; la CI du HEAD de livraison
reste requise pour l'attestation de régression complète.

Commande navigateur : même pilote avec `--navigateur`. Résultats :
comptes **26/26**, rôles **35/35**, câblage **101/101**, ventes **63/63**,
dont annulation mixte, recette unique, composantes séparées, crédit et retours.
La CI obligatoire ajoute l'ensemble des suites pytest et les 13 suites
Playwright sur le HEAD de la PR. Les résultats d'un sommet précédent ne sont
pas une preuve de non-régression du sommet livré.

Les fichiers de preuves suivis sont dans `RAPPORT AVANCEMENT/preuves/lot-a`.
Les dumps, secrets de test, clusters locaux et captures temporaires ne sont
pas livrés dans Git. Le pilote les conserve localement pour inspection et
arrête ses instances à la fin. Les ports de test sont distincts du Lot B.

## Sauvegarde, fiscalité et score

Compatibilité des scripts examinée en lecture : `git show` pour le fichier
en quarantaine ; le dump custom complet et `pg_restore` incluent les nouvelles
tables, fonctions, contraintes, grants et triggers. Aucun filtre de schéma
excluant les nouvelles tables n'a été introduit. **Ni sauvegarder.ps1 ni ses
appels indirects n'ont été exécutés.** La preuve de reprise concerne les
outils PostgreSQL et un jeu synthétique, pas la chaîne chiffrée sur poste réel.

**Score global C1 conservé : 96 %.** La clôture technique du périmètre testé
ne ferme ni C1-02 ni C1-03 : Q1–Q6 restent au comptable ; la reprise sur données
réelles avec rapprochement et PV n'est pas autorisée par cette mission.
TTC est acquis pour la saisie ; aucune valeur fiscale ni présentation fiscale
non validée n'a été inventée. Question bloquante : obtenir les réponses écrites
du comptable à Q1–Q6, notamment le besoin de ventilation HT ligne par ligne,
les mentions obligatoires et l'arrondi. La reprise réelle reste hors périmètre.

Le registre et le journal globaux seront consolidés à l'intégration, en
préservant les contributions de Qoder. Aucune fusion de PR exécutée par Codex.
