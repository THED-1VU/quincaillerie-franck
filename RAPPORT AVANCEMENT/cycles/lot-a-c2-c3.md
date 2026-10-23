# Lot A — C2/C3 : sessions, comptes et autorité du serveur

2026-10-23. Mission explicite « Opération 100 % / Lot A » et compléments C2/C3
du propriétaire. Aucune décision administrative, fiscale ou D1 prise ici.

## Socle et coordination

Le main distant vérifié initialement était `37b7b7967fda4f367e523e303110f0cbda1af99a`.
Les PR 93–100 étaient toutes OPEN, `mergedAt=null`, `mergeCommit=null`.
Une seconde vérification a constaté la fusion de 93, main `f255dc6` ; 94 restait
OPEN avec deux contrôles en échec, tandis que 100 était OPEN et verte.
Conformément au contrat opérationnel du Lot B, le sommet complet `2dae406`
a ensuite été intégré **localement**, sans fusionner aucune PR dans main.
Les ascendances D2, D6/D10 et D7/D8 ont été vérifiées par `merge-base --is-ancestor`.
La PR de cette unité dépend donc de l'intégration de 100.

Worktree : `_worktrees/codex-akuma-c1-c2-c3-100`. Tests sur des instances
PostgreSQL propres, ports 5547/5548/5549. Les premiers essais sur le moteur
partagé ont été écartés après constat de l'absence de mot de passe de son
rôle qf_app. Aucun mot de passe du moteur partagé n'a été modifié par Codex.
Contrat partagé publié avant les changements ; seuls les modèles C2 de
`schemas.py` sont adaptés, aucune modification des modèles de vente.

## Écarts initiaux et corrections

| Écart reproduit | Correction et preuve négative |
|---|---|
| Un gestionnaire configuré à 481 minutes émettait et acceptait 28 860 secondes | Plafond de 28 800 secondes à l'émission et contrôle à la vérification ; réponse HTTP bornée aussi. |
| Après reset puis changement définitif, un ancien jeton redevenait accepté (HTTP 200) | 053 enregistre les sessions ; changement du secret révoque les autres sessions, reset révoque toutes les anciennes. La session de libre-service reste utilisable. |
| Désactiver puis réactiver pouvait remettre une ancienne session en service | Invalidation persistante des sessions à chaque modification de l'activité du compte. |
| Un rôle retiré en base restait exploitable par un jeton existant (HTTP 200) | Le contexte, le site et les rôles courants sont relus en base ; retrait effectif dès la requête suivante. |
| Deux échecs simultanés pouvaient perdre un incrément (lecture puis écriture sans verrou) | `verifier_connexion` verrouille le compte ; test à deux connexions, compteur final exactement 2. |
| Deux secrets différents après le 72e octet étaient équivalents avec bcrypt 4.2.1 | Validation UTF-8 à 72 octets sur les entrées C2, garde au hachage et protections SQL des créations/réinitialisations. Aucun changement du minimum métier existant. |
| Les modifications SQL de rôles et refus du limiteur n'avaient pas de trace dédiée complète | Journal de sécurité sans secret, identité SQL et auteur applicatif si présent ; trace du refus 429 dans le journal des connexions. UPDATE/DELETE refusés aux rôles métier. |

Les jetons antérieurs à 053 non enregistrés nécessitent une reconnexion.
La table des sessions ne contient ni secret ni jeton porteur : jti aléatoire,
identité et expiration uniquement. Ses lectures/écritures directes ne sont
accordées à aucun rôle métier. Les fonctions exposées sont limitées à qf_app.

## Vérifications et couverture

La passe ciblée commune C1/C2/C3 a exécuté **48 tests pytest réussis** sur
une instance isolée : sessions serveur, D6, changement forcé, cumul des rôles,
paiements mixtes et contournements SQL. Les tests couvrent notamment le refus
après reset, après réactivation, après déplacement de site et retrait de rôle,
la préservation de la session courante, les échecs concurrents et les secrets
ASCII/multioctets dépassant la capacité bcrypt.

Playwright sur serveur réel et PostgreSQL isolé : **comptes 26/26**, **rôles
35/35**, **câblage 101/101**, **vente 63/63**. La suite rôles prouve la
navigation vers la vente depuis un compte stock + comptabilité, le prix de
vente présent, le retour vers l'inventaire et le refus des écrans responsable.
Aucun écran appartenant à Qoder n'a été modifié.

Les suites existantes d'authentification, comptes, sécurité, matrice exhaustive
des endpoints, SQL des privilèges et cloisonnement intersites sont conservées
dans la régression complète et dans la CI obligatoire pytest + Playwright.
Les résultats complets sont à prendre sur le HEAD exact de la PR : un succès
sur un sommet précédent ne vaut pas validation du sommet livré.

Commande reproductible locale commune, après installation des dépendances :
`python "RAPPORT AVANCEMENT/cycles/verifier_lot_a.py" --cible`, puis la même
commande sans option pour la régression complète, et avec `--navigateur` pour
les quatre suites navigateur. Le pilote appartient à l'unité C1 dépendante.
Il n'appelle aucun script de sauvegarde en quarantaine.

## 2FA et critères de clôture

Le report V1 de D10 reste acquis. Les mesures compensatoires couvertes sont :
bcrypt coût 12 ; changement provisoire obligatoire ; limitation partagée et
verrouillage ; sessions signées et bornées, sans refresh ; révocation durable,
désactivation et reset ; rôles SQL/RLS ; audit des connexions et opérations.
Le pilote de preuves n'exécute aucune mesure du poste de production.

Les critères techniques de cette unité sont testés par les scénarios ci-dessus.
La livraison exige également les deux jobs CI verts sur son HEAD ; les liens
de contrôles de la PR constituent la preuve distante, distincte d'une fusion.

**Scores globaux conservés : C2 90 %, C3 88 %. Pas de promotion artificielle.**
Une clôture technique sur le périmètre des tests ne ferme pas les décisions :

- C2-01 : « Confirmez-vous `tentatives_max_connexion=5`, ou quelle valeur
  souhaitez-vous retenir ? » Le drapeau `a_decider` reste inchangé.
- D1 : « Confirmez-vous le périmètre actuel du caissier/agent comptabilité :
  prix de vente visibles, prix d'achat jamais visibles, ou quelles informations
  supplémentaires doivent être masquées ? » Aucun arbitrage fait ici.

Le registre et le journal globaux ne sont pas édités en parallèle : cette
note porte les changements à consolider lors de l'intégration, sans écraser
le travail du Lot B. Aucune production, importation réelle ou fusion de PR.
