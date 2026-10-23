# Akuma — contrat d'interface et préparation du lot A

Date : 2026-10-23. Codex : C1/C2/C3. Qoder : C5/C8/C12.
Branche Codex : `codex/akuma-c1-c2-c3-100`.
Statut : contrat proposé pour coordination ; aucun accusé de réception de Qoder.

## Socle vérifié

`git fetch origin`, `git ls-remote origin refs/heads/main` et l'API GitHub
confirment main = `37b7b7967fda4f367e523e303110f0cbda1af99a`.
Les PR 93, 94, 95, 96, 97, 98, 99 et 100 sont OPEN ; toutes ont
`mergedAt=null` et `mergeCommit=null`. La PR 94 cible la branche de 93 ;
95 cible celle de 94 ; les autres ciblent main. La PR 92 est aussi ouverte.
Une CI verte ne constitue pas une preuve de fusion.

Le registre à 20 clôtures et les scores 96/90/88 sont présents sur la branche
cycle-75-h, pas une preuve de livraison intégrée dans main.
Main ne contient ni 051 ni 052. Aucun correctif applicatif du lot A ne doit
démarrer avant intégration vérifiée du socle et nouvelle synchronisation.
La préparation seule est effectuée dans ce worktree créé depuis origin/main.
Aucune fusion n'est effectuée dans cette préparation.

## Interfaces partagées

| Interface | Responsabilité et règle de coordination |
|---|---|
| `ventes`, `ventes_paiements` (052 attendue), lignes de vente | Codex audite contraintes, transactions, concurrence et RLS ; Qoder conserve le parcours vente et la facturation. Toute évolution de structure ou de signification doit être consignée ici avant intégration. |
| `transactions`, `stocks_sites`, créances et règlements | Préserver la cohérence vente/stock/journal ; aucun double encaissement. Annulation et remboursement doivent conserver la trace et contrepasser selon les règles existantes. |
| `POST /ventes`, `GET /caisse/attendu`, fonction `calculer_attendu_caisse` | Conserver le paiement simple ; décomposition `paiements[]` attendue de 052, incompatible avec le champ simple simultané. Les rapports de Qoder doivent exploiter les composantes pour ventiler par mode. |
| `/auth/connexion`, `/auth/deconnexion`, `/auth/changer-mot-de-passe`, `/admin/comptes` | Codex possède authentification, comptes, révocation et contrôles d'accès ; les parcours de Qoder passent par ces contrôles communs. |
| Rôles `qf_responsable`, `qf_agent_comptabilite`, `qf_agent_stock` | Aucun élargissement implicite des grants, RLS, données de coût ou accès intersites. Vérifier aussi en SQL sous chaque rôle, sans dépendre des seuls menus. |
| Scripts de sauvegarde/restauration et état d'exploitation | Qoder possède C12 ; Codex vérifie la compatibilité des schémas et migrations par inspection et essais isolés autorisés. Aucun élément en quarantaine ne doit être exécuté, directement ou via un orchestrateur. |

## Invariants à prouver, pas encore certifiés par ce contrat

- Somme des composantes égale au montant encaissé, modes cohérents, unicité
  par vente/mode ; crédit sans composante d'encaissement immédiat.
- Une opération de vente atomique couvre stock, vente, journal et paiements ;
  les refus et courses concurrentes ne laissent aucun état partiel.
- Annulations, retours et remboursements préservent les montants, le stock,
  la traçabilité et l'absence de double comptage.
- Comptes désactivés, mots de passe réinitialisés et sessions révoquées
  perdent effectivement leurs accès ; cloisonnement par rôle et par site.
- TTC acquis pour la saisie ; Q1–Q6 demeurent réservées au comptable.
  Aucun critère fiscal en attente ne sera déclaré clos.

## Plan autorisé du lot et critères de sortie

1. Après intégration du socle, consigner les SHA fusionnés et les contrôles
   obligatoires ; synchroniser cette branche sans réécrire l'historique.
2. Inventorier les fichiers 000–052 réellement présents et leur suivi en base,
   y compris doublons/trous ; rejouer les preuves précédentes sur base isolée.
3. Reproduire chaque écart C1/C2/C3 et corriger les écarts techniques dans ce
   périmètre. Coordonner avant toute modification commune avec Qoder.
4. Réserver ensemble les prochains numéros avant toute nouvelle migration ;
   aucun numéro après 052 n'est réservé par ce document.
5. Exécuter migrations sur base vierge et version précédente, tests SQL directs,
   concurrence, paiements mixtes, comptes et rôles, puis régression des ventes.
   Ne lancer un orchestrateur qu'après inspection de ses appels et exclusions.
6. Livrer commandes, résultats et limites dans le rapport et le registre ;
   ne porter un score à 100 que si tous les critères sont prouvés. Garder les
   validations comptables et celles du poste cible explicitement ouvertes.

Blocage actuel : socle incomplet. La décision de fusion appartient au
propriétaire ; les dépendances et contrôles obligatoires doivent être vérifiés
avant toute fusion. Ni reset destructeur, ni force-push, ni modification du
travail de Qoder. La suppression locale de `db/outils/sauvegarder.ps1` dans le
worktree initial n'a pas été touchée.
