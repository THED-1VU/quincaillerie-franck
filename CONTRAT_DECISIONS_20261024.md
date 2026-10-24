# Contrat partagé — décisions du 24/10/2026

Socle : origin/main `7bebdeddc67d00d11b750238cca42b6d7154a21d` (#103 fusionnée).
Branche Codex : `codex/decisions-proprietaire-20261024`.

Le propriétaire autorise explicitement les quatre corrections, leurs tests et des PR coordonnées. Ce document est publié avant toute modification des fichiers transversaux de Qoder.

| Décision | Portée / responsable de réalisation | Interface et invariant attendus | Statut initial |
|---|---|---|---|
| D-N1 | Codex, coordination Qoder pour ventes.py / vente.html | POST /ventes : remise effective totale rapportée au total catalogue pondéré par quantités, toutes remises incluses ; ≤10 % sans approbation, >10 % uniquement sous identité responsable authentifiée ; preuve d'approbation liée à la vente, atomique | VALIDÉE propriétaire 24/10 ; conformité à reproduire/tester |
| D-N5 | Codex, coordination Qoder pour exploitation.py et tableau-bord.html | GET /exploitation/etat-sauvegarde : succès frais uniquement sur preuve complète ET vérifiée ; alerte à âge ≥3600 s ; échec/incomplet/non vérifié ne rajeunit pas la dernière preuve ; actualisation du bandeau sans rechargement | VALIDÉE propriétaire 24/10 ; conformité à reproduire/tester |
| D1 | Codex ; droits comptable réservés au propriétaire | Caissier = compte agent_comptabilite existant : vente TTC autorisée, achats/coûts/marges exclus des API/exports/SQL et accès indirects contrôlés ; aucun nouveau droit comptable | VALIDÉE propriétaire 24/10 ; audit et tests nécessaires |
| C2-01 | Codex / schéma et auth | 5 échecs consécutifs, verrou SQL atomique de 15 min à partir du cinquième ; essais pendant verrou sans prolongation ; succès remet le compteur à zéro ; limites HTTP conservées | VALIDÉE propriétaire 24/10 ; conformité à reproduire/tester |

## Réservation et coordination

- **055 réservée à Codex**, avant création, dans RAPPORT AVANCEMENT/loop-state.md : verrouillage temporaire, audit des approbations, protections associées strictement nécessaires. Aucun autre agent ne doit utiliser ce numéro.
- Tables prévues : utilisateurs (date de fin de verrou), journal d'approbation des remises lié à ventes ; fonctions d'authentification conservant leur signature. Migration réversible et historique 000–054 non réécrit.
- Approbation de remise : le responsable enregistre la vente lui-même, sous son jeton existant. Aucun champ client « approuvé » ni mot de passe de responsable envoyé dans un panier. Traçabilité SQL du responsable, du montant catalogue, du montant final et de la décision.
- Sauvegardes : le producteur en quarantaine est exclu. Le consommateur refuse tout ancien SUCCES sans preuve explicite de complétude et vérification. Une interface de preuve documentée sera testée avec des fichiers synthétiques ; aucune affirmation de fonctionnement du producteur réel.
- Possibles chevauchements : PR #105 sur ventes.py ; ne pas remplacer son correctif de concurrence ni le fusionner sans autorisation. Revalidation de compatibilité requise avant fusion.
- Tests uniquement sur **cluster privé** PostgreSQL, bases/ports et captures séparés ; aucun changement de mot de passe sur le cluster partagé.
- Pas de score relevé par cette décision, pas d'import réel, de production, de fusion, ni d'exécution/restauration de sauvegarder.ps1. `verif-integration` conservé.

## Livraison Codex des décisions du 24/10/2026 — PR #110

- Socle d'intégration : origin/main 546fa957571b7d1c105440889376efacd442752b (#104/#105/#106 inclus). Le brouillon #107 est remplacé par #110, branches conservées ; aucune fusion GitHub.
- D-N1, D-N5, D1 et C2-01 : VALIDÉES métier le 24/10 ; corrections techniques en revue dans #110, preuves détaillées dans RAPPORT_DECISIONS_20261024_CODEX.md et les commentaires de la PR. Aucune clôture globale ni score relevé par la décision seule.
- Contrôles locaux : 41 pytest ciblés ; SQL protections 202/202, habilitations 55/55, concurrence 6/6 et 055 ; migration 054→055/inverse/réapplication, inverse refusée avec audit intact ; charge 20 refus concurrents et un compte distinct accepté ; responsable secondaire HTTP 201, auteur correctement tracé.
- Dernière CI complète avant les ultimes contrôles réseau/cache : 6d0ebe4, pytest/13 suites verts. La CI du commit complet est à vérifier sur #110 ; aucun succès de ce nouveau commit n'est anticipé dans ce journal.
- 055 demeure réservée à cette livraison, utilisée une seule fois ; aucun fichier 000–054 réécrit. Pas de nouvelle réservation ni migration concurrente.
- D-N5 : producteur en quarantaine non exécuté et non qualifié ; alerte prudente sur son ancien format non vérifié. Droits comptable et Q1–Q6 toujours réservés. Scores de référence inchangés : C1 96 %, C2 90 %, C3 88 %.
- Fiches historiques publiées dans #109 (CI verte), D1/C2-01 actualisées. Rejeu des trois défauts post-#103 AVANT effectué sur 546fa95 ; APRÈS et verdict en attente de la PR qoder/correctifs-post-103. Aucune branche tierce modifiée. verif-integration conservé.
